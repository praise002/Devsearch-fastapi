from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.service import UserService
from src.db.models import Otp, Profile, ProfileSkill, Skill, User


class TestUserRegistration:
    register_url = "/api/v1/auth/register"

    """Test suite for user registration endpoint."""

    async def test_register_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        valid_user_data: dict,
        mock_email: list,
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
        assert email_data["template_name"] == "verify_email_request.html"

    async def test_register_very_long_password(
        self,
        async_client: AsyncClient,
        valid_user_data: dict,
    ):
        valid_data = valid_user_data.copy()
        valid_data["password"] = "A" * 1000

        response = await async_client.post(self.register_url, json=valid_data)
        print(response.json())

        assert response.status_code == 422

    async def test_register_user_already_exists(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        valid_user_data: dict,
        mock_email: list,
    ):
        # Arrange
        await async_client.post(self.register_url, json=valid_user_data)
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
        mock_email: list,
    ):
        """
        Test registration fails when username already exists.
        """
        # Arrange
        await async_client.post(self.register_url, json=valid_user_data)
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

        email_data = mock_email[0]
        assert email_data["template_name"] == "welcome_message.html"

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
        print(response_data)

        assert response_data["status"] == "success"
        assert response_data["message"] == "Email address already verified."

        # Assert: No welcome emails should be sent for already verified users
        assert len(mock_email) == 0

    async def test_verify_email_missing_fields(
        self,
        async_client: AsyncClient,
        registered_user: User,
        otp_for_user: str,
    ):
        """
        Test verification fails when required fields are missing.
        """
        # Test missing email
        response = await async_client.post(
            self.verify_user_email, json={"otp": otp_for_user}
        )
        assert response.status_code == 422

        # Test missing OTP
        response = await async_client.post(
            self.verify_user_email, json={"email": registered_user.email}
        )
        assert response.status_code == 422

        # Test empty data
        response = await async_client.post(self.verify_user_email, json={})
        assert response.status_code == 422

    async def test_verify_email_invalid_otp_format(
        self,
        async_client: AsyncClient,
        registered_user: User,
    ):
        """
        Test verification fails with invalid OTP formats.
        """
        invalid_otp_cases = [
            "12345",  # Too short
            "1234567",  # Too long
            "abcdef",  # Non-numeric
            "12 3456",  # Contains space
            "",  # Empty
        ]

        for invalid_otp in invalid_otp_cases:
            verification_data = {"email": registered_user.email, "otp": invalid_otp}

            response = await async_client.post(
                self.verify_user_email, json=verification_data
            )
            print(response.json())

            # Should either be validation error or invalid OTP error
            assert response.status_code == 422


class TestResendVerificationEmail:
    """Test suite for OTP resend endpoint."""

    resend_verification = "/api/v1/auth/verification"

    @pytest.mark.asyncio
    async def test_resend_otp_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
        mock_email: list,
    ):
        # Arrange
        resend_data = {"email": registered_user.email}

        # Create some existing OTPs to test invalidation
        existing_otp = Otp(user_id=registered_user.id, otp=123456)
        db_session.add(existing_otp)
        await db_session.commit()

        # Act: Resend verification email
        response = await async_client.post(self.resend_verification, json=resend_data)

        # Assert: Check response
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert response_data["message"] == "OTP sent successfully"

        # Assert: Check email was sent
        assert len(mock_email) == 1
        email_data = mock_email[0]
        assert email_data["template_name"] == "verify_email_request.html"

        user_service = UserService()
        # Assert: There should be exactly ONE new OTP for the user
        all_otps = await user_service.get_user_otps(registered_user.id, db_session)
        print(all_otps)
        assert len(all_otps) == 1

    async def test_resend_otp_user_not_found(
        self,
        async_client: AsyncClient,
    ):

        # Arrange
        resend_data = {"email": "nonexistent@example.com"}

        # Act
        response = await async_client.post(self.resend_verification, json=resend_data)

        # Assert
        assert response.status_code == 422
        response_data = response.json()
        assert response_data["err_code"] == "user_not_found"

    async def test_resend_otp_already_verified(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        mock_email: list,
    ):
        # Arrange
        resend_data = {"email": verified_user.email}

        # Act
        response = await async_client.post(self.resend_verification, json=resend_data)

        # Assert: Check response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["status"] == "success"
        assert "Email address already verified" in response_data["message"]

        # Assert: No email should be sent for already verified users
        assert len(mock_email) == 0

    async def test_resend_otp_missing_email(
        self,
        async_client: AsyncClient,
    ):
        # Arrange: Missing email
        resend_data = {}

        # Act
        response = await async_client.post(self.resend_verification, json=resend_data)
        print(response.json())
        # Assert
        assert response.status_code == 422


class TestUserLogin:
    """Test suite for user login endpoint."""

    login_url = "/api/v1/auth/token"

    async def test_login_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        valid_user_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": valid_user_data["password"],
        }

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 200
        response_data = response.json()

        assert response_data["status"] == "success"
        assert response_data["message"] == "Login successful"
        assert "access" in response_data
        assert "refresh" in response_data

        # Assert: Tokens should not be empty
        assert response_data["access"] is not None
        assert response_data["refresh"] is not None

    async def test_login_user_not_found(
        self,
        async_client: AsyncClient,
    ):

        login_data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        }

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "failure"
        assert response_data["err_code"] == "unauthorized"

    async def test_login_invalid_password(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
    ):

        login_data = {"email": verified_user.email, "password": "WrongPassword123!"}

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "failure"
        assert response_data["err_code"] == "unauthorized"

    async def test_login_account_not_verified(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
        valid_user_data: dict,
    ):

        login_data = {
            "email": registered_user.email,
            "password": valid_user_data["password"],
        }

        response = await async_client.post(self.login_url, json=login_data)
        assert response.status_code == 403
        response_data = response.json()
        assert response_data["err_code"] == "account_not_verified"

    async def test_login_user_inactive(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        inactive_user: User,
        another_user_data: dict,
    ):
        login_data = {
            "email": another_user_data["email"],
            "password": another_user_data["password"],
        }

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 403
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "forbidden"

    async def test_login_missing_email(
        self,
        async_client: AsyncClient,
    ):

        login_data = {"password": "SomePassword123!"}

        response = await async_client.post(self.login_url, json=login_data)
        print(response.json())

        assert response.status_code == 422

    async def test_login_missing_password(
        self,
        async_client: AsyncClient,
        verified_user: User,
    ):

        login_data = {"email": verified_user.email}

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 422

    async def test_login_empty_credentials(
        self,
        async_client: AsyncClient,
    ):

        login_data = {"email": "", "password": ""}

        response = await async_client.post(self.login_url, json=login_data)

        assert response.status_code == 422

    async def test_login_case_insensitive_email(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        valid_user_data: dict,
    ):

        login_data = {
            "email": verified_user.email.upper(),
            "password": valid_user_data["password"],
        }

        response = await async_client.post(self.login_url, json=login_data)
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)
        assert response_data["status"] == "success"
        assert "access" in response_data
        assert "refresh" in response_data


class TestTokenRefresh:
    """Test suite for token refresh endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
    ):
        pass


class TestGetCurrentUserProfile:
    """Test suite for get current user profile endpoint"""

    url = "/api/v1/auth/me"
    login_url = "/api/v1/auth/token"

    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
    ):
        await db_session.refresh(verified_user, ["profile"])
        profile = verified_user.profile
        assert profile is not None, "User should have a default profile."

        profile.short_intro = "Software Developer"
        profile.bio = "Passionate about coding and open source"
        profile.location = "New York, USA"
        profile.github = "https://github.com/testuser"
        profile.stack_overflow = "https://stackoverflow.com/users/testuser"
        profile.tw = "https://twitter.com/testuser"
        profile.ln = "https://linkedin.com/in/testuser"
        profile.website = "https://testuser.com"

        skill = Skill(
            name="Python",
        )

        profile_skill = ProfileSkill(
            profile_id=profile.id,
            skill_id=skill.id,
            description="Expert in Python development with 5 years experience",
        )

        db_session.add_all([profile, skill, profile_skill])
        await db_session.commit()

        login_data = {
            "email": user3_data["email"],
            "password": user3_data["password"],
        }

        login_response = await async_client.post(self.login_url, json=login_data)

        response_json = login_response.json()
        print(response_json)
        access = response_json["access"]
        print(access)
        response = await async_client.get(
            self.url, headers={"Authorization": f"Bearer {access}"}
        )

        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["id"] == str(verified_user.id)

    async def test_get_user_profile_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        # Act: Try to access without authentication
        response = await async_client.get(self.url)

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"


# FastAPI Filters
# FastAPI-Users
# FastAPI-Admin
# pytest src/tests/test_auth.py::TestGetCurrentUserProfile -v -s
# pytest src/tests/test_auth.py::TestResendVerificationEmail::test_resend_otp_success -v -s
# TODO: FIX EMAIL SENDING
