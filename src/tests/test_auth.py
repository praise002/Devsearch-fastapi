import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.service import UserService
from src.db.models import Otp, User


class TestUserRegistration:
    register_url = "/api/v1/auth/register"

    """Test suite for user registration endpoint."""

    async def test_register_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_email: list,
        valid_user_data: dict,
    ):

        # Act: Make registration request
        response = await async_client.post(self.register_url, json=valid_user_data)

        # Assert: Check response
        assert response.status_code == 201
        response_data = response.json()

        assert response_data["status"] == "success"
        assert "verify" in response_data["message"]
        assert response_data["email"] == valid_user_data["email"]

        # Assert: Check database
        user_service = UserService()
        user = await user_service.get_user_by_email(
            valid_user_data["email"], db_session
        )

        assert user is not None
        assert user.email == valid_user_data["email"]
        assert user.username == valid_user_data["username"]
        assert user.first_name == valid_user_data["first_name"]
        assert user.last_name == valid_user_data["last_name"]
        assert not user.is_email_verified
        assert user.is_active

        # Assert: Check email was sent
        assert len(mock_email) == 1
        email_data = mock_email[0]
        assert email_data["email_to"] == valid_user_data["email"]
        assert email_data["subject"] == "Verify your email"
        assert "otp" in email_data["template_context"]

    async def test_register_user_already_exists(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        valid_user_data: dict,
    ):
        # Arrange
        duplicate_request = valid_user_data.copy()
        duplicate_request["username"] = "different_username_123"

        # Act: Try to register same user again
        response = await async_client.post(self.register_url, json=duplicate_request)

        # Assert
        assert response.status_code == 422
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "user_exists"

    async def test_register_username_already_exists(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        valid_user_data: dict,
    ):
        """
        Test registration fails when username already exists.
        """
        # Arrange
        duplicate_request = valid_user_data.copy()
        duplicate_request["email"] = "email@email.com"

        # Act: Try to register with duplicate username
        response = await async_client.post(self.register_url, json=duplicate_request)

        # Assert
        assert response.status_code == 422
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "username_exists"

    async def test_register_invalid_email(
        self,
        async_client: AsyncClient,
        invalid_user_data: dict,
    ):
        """
        Test registration fails with invalid email format.
        """

        response = await async_client.post(self.register_url, json=invalid_user_data)

        assert response.status_code == 422

    async def test_register_weak_password(
        self,
        async_client: AsyncClient,
        weak_password_data: dict,
    ):
        """
        Test registration fails with weak password.
        """

        response = await async_client.post(self.register_url, json=weak_password_data)

        assert response.status_code == 422

    async def test_register_missing_required_fields(
        self,
        async_client: AsyncClient,
    ):
        """
        Test registration fails when required fields are missing.
        """
        incomplete_data = {
            "email": "test@example.com",
        }

        response = await async_client.post(self.register_url, json=incomplete_data)

        assert response.status_code == 422

    async def test_password_is_hashed(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_email: list,
        another_user_data: dict,
    ):
        """
        Test that password is properly hashed in database.
        """
        # Act
        response = await async_client.post(self.register_url, json=another_user_data)

        # Assert
        assert response.status_code == 201

        # Check password is hashed (not stored in plain text)
        user_service = UserService()
        user = await user_service.get_user_by_email(
            another_user_data["email"], db_session
        )

        assert user.hashed_password is not None
        assert user.hashed_password != another_user_data["password"]
        assert len(user.hashed_password) > 20


class TestEmailVerification:
    """Test suite for email verification endpoint."""

    verify_user_email = "/api/v1/auth/verification/verify"

    async def test_verify_email_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
        otp_for_user: int,
        mock_email: list,
    ):

        # Arrange
        verification_data = {"email": registered_user.email, "otp": otp_for_user}

        # Act: Verify email
        response = await async_client.post(
            self.verify_user_email, json=verification_data
        )

        # Assert: Check response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["status"] == "success"
        assert "verified" in response_data["message"]

        # Assert: Check user is verified in database
        user_service = UserService()
        updated_user = await user_service.get_user_by_email(
            registered_user.email, db_session
        )

        assert updated_user.is_email_verified is True

        # Assert: Check OTP is invalidated
        otp_record = await user_service.get_otp_by_user(
            registered_user.id, otp_for_user, db_session
        )
        assert otp_record is None

        # Assert: Check welcome email was sent
        assert len(mock_email) == 1

    async def test_verify_email_invalid_otp(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
    ):
        """
        Test verification fails with invalid OTP.
        """
        # Arrange
        verification_data = {
            "email": registered_user.email,
            "otp": "999999",
        }

        # Act
        response = await async_client.post(
            self.verify_user_email, json=verification_data
        )

        # Assert
        assert response.status_code == 422
        response_data = response.json()
        assert response_data["err_code"] == "invalid_otp"

        # Assert: User should still be unverified
        user_service = UserService()
        user = await user_service.get_user_by_email(registered_user.email, db_session)
        assert user.is_email_verified is False

    async def test_verify_email_user_not_found(
        self,
        async_client: AsyncClient,
        otp_for_user: str,
    ):
        """
        Test verification fails for non-existent user.
        """
        # Arrange
        verification_data = {"email": "nonexistent@example.com", "otp": otp_for_user}

        # Act
        response = await async_client.post(
            self.verify_user_email, json=verification_data
        )

        # Assert
        assert response.status_code == 422

    async def test_verify_email_already_verified(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        mock_email: list,
    ):
        """
        Test verification when user is already verified.
        """
        # Arrange
        otp_record = Otp(user_id=verified_user.id, otp=123456, is_valid=True)
        db_session.add(otp_record)
        await db_session.commit()

        verification_data = {"email": verified_user.email, "otp": 123456}

        # Act
        response = await async_client.post(
            self.verify_user_email, json=verification_data
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["status"] == "success"
        assert response_data["message"] == "Email address already verified."

        # Assert: No welcome emails should be sent for already verified users
        assert len(mock_email) == 0


# FastAPI Filters
# FastAPI-Users
# FastAPI-Admin
