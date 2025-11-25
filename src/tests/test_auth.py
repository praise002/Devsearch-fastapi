import asyncio
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


class TestLogout:

    logout_url = "/api/v1/auth/logout"
    login_url = "/api/v1/auth/token"

    async def test_logout_success(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        refresh_token = tokens["refresh"]

        response = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {refresh_token}"}
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "Logged Out Successfully" in response_data["message"]

        # Try to use the same refresh token again
        retry_response = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {refresh_token}"}
        )
        print(retry_response.json())
        assert retry_response.status_code == 401

    async def test_logout_without_token(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.post(self.logout_url)
        print(response.json())

        assert response.status_code == 401
        response_data = response.json()
        assert response_data["err_code"] == "unauthorized"

    async def test_logout_with_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        invalid_token = "invalid.token.here"

        response = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {invalid_token}"}
        )
        print(response.json())

        assert response.status_code == 401

    async def test_logout_with_access_token(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        response = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {access_token}"}
        )
        print(response.json())

        assert response.status_code == 401

    async def test_logout_with_expired_token(
        self,
        async_client: AsyncClient,
        expired_refresh_token: str,
    ):

        response = await async_client.post(
            self.logout_url,
            headers={"Authorization": f"Bearer {expired_refresh_token}"},
        )
        response_data = response.json()
        print(response_data)

        assert response.status_code == 401
        assert response_data["err_code"] == "invalid_token"

    async def test_logout_twice_with_same_token(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):

        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        refresh_token = tokens["refresh"]

        # First logout
        first_logout = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {refresh_token}"}
        )
        print(first_logout.json())
        assert first_logout.status_code == 200

        # Try to logout again with same token
        second_logout = await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {refresh_token}"}
        )
        print(second_logout.json())

        # Second logout should fail
        assert second_logout.status_code == 401


class TestLogoutAll:
    """Test suite for logout all devices endpoint"""

    logout_all_url = "/api/v1/auth/logout/all"
    login_url = "/api/v1/auth/token"

    async def test_logout_all_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
    ):
        # Arrange: Create multiple sessions (login multiple times)
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }

        # Session 1
        login1 = await async_client.post(self.login_url, json=login_data)
        tokens1 = login1.json()

        # Session 2
        login2 = await async_client.post(self.login_url, json=login_data)
        tokens2 = login2.json()

        # Session 3
        login3 = await async_client.post(self.login_url, json=login_data)
        tokens3 = login3.json()

        # Act: Logout from all devices using Session 1's access token
        response = await async_client.post(
            self.logout_all_url,
            headers={"Authorization": f"Bearer {tokens1['access']}"},
        )

        # Assert: Check response
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)
        assert response_data["status"] == "success"
        assert "all devices" in response_data["message"].lower()

        # Assert: All refresh tokens should now be blacklisted
        # Try to use refresh token from session 2
        from src.auth.service import UserService

        user_service = UserService()

        # Decode tokens to get JTIs
        from src.auth.utils import decode_token

        refresh1_jti = decode_token(tokens1["refresh"])["jti"]
        refresh2_jti = decode_token(tokens2["refresh"])["jti"]
        refresh3_jti = decode_token(tokens3["refresh"])["jti"]

        # Check all tokens are blacklisted
        assert await user_service.is_token_blacklisted(refresh1_jti, db_session)
        assert await user_service.is_token_blacklisted(refresh2_jti, db_session)
        assert await user_service.is_token_blacklisted(refresh3_jti, db_session)

    async def test_logout_all_without_token(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.post(self.logout_all_url)

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_logout_all_with_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        invalid_token = "invalid.token.here"

        response = await async_client.post(
            self.logout_all_url, headers={"Authorization": f"Bearer {invalid_token}"}
        )
        print(response.json())

        assert response.status_code == 401

    async def test_logout_all_with_refresh_token(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }

        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        refresh_token = tokens["refresh"]

        # Try to logout all with refresh token (should fail)
        response = await async_client.post(
            self.logout_all_url, headers={"Authorization": f"Bearer {refresh_token}"}
        )

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "access_token_required"


class TestTokenRefresh:
    """Test suite for token refresh endpoint"""

    refresh_url = "/api/v1/auth/token/refresh"
    login_url = "/api/v1/auth/token"
    logout_url = "/api/v1/auth/logout"
    logout_all_url = "/api/v1/auth/logout/all"

    async def test_refresh_token_success(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):

        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        old_tokens = login_response.json()
        old_refresh = old_tokens["refresh"]
        old_access = old_tokens["access"]

        response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {old_refresh}"}
        )

        # Assert: Check response
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Token refreshed successfully" in response_data["message"]
        assert "access" in response_data
        assert "refresh" in response_data

        # New tokens should be different from old ones
        assert response_data["access"] != old_access
        assert response_data["refresh"] != old_refresh

    async def test_refresh_token_blacklists_old_token(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        old_tokens = login_response.json()
        old_refresh = old_tokens["refresh"]

        # Refresh once
        await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {old_refresh}"}
        )

        # Try to refresh again with same old token
        retry_response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {old_refresh}"}
        )

        # Assert: Should fail because old token is blacklisted
        assert retry_response.status_code == 401
        response_data = retry_response.json()
        print(response_data)
        assert response_data["err_code"] == "invalid_token"

    async def test_refresh_token_without_token(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.post(self.refresh_url)

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_refresh_with_access_token(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):

        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # try to refresh with access token
        response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {access_token}"}
        )

        # Should fail
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "refresh_token_required"

    async def test_refresh_with_invalid_token(
        self,
        async_client: AsyncClient,
    ):

        invalid_token = "invalid.token.here"

        response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "invalid_token"

    async def test_refresh_with_expired_token(
        self,
        async_client: AsyncClient,
        expired_refresh_token: str,
    ):

        response = await async_client.post(
            self.refresh_url,
            headers={"Authorization": f"Bearer {expired_refresh_token}"},
        )
        response_data = response.json()
        print(response_data)

        assert response.status_code == 401
        assert response_data["err_code"] == "invalid_token"

    async def test_refresh_after_logout(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()

        # Logout
        await async_client.post(
            self.logout_url, headers={"Authorization": f"Bearer {tokens['refresh']}"}
        )

        # Try to refresh after logout
        response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {tokens['refresh']}"}
        )

        # Should fail
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "invalid_token"

    async def test_refresh_after_logout_all(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }

        login1 = await async_client.post(self.login_url, json=login_data)
        tokens1 = login1.json()

        login2 = await async_client.post(self.login_url, json=login_data)
        tokens2 = login2.json()

        # Logout from all devices using session 1

        await async_client.post(
            self.logout_all_url,
            headers={"Authorization": f"Bearer {tokens1['access']}"},
        )

        # Try to refresh tokens from session 2
        response = await async_client.post(
            self.refresh_url, headers={"Authorization": f"Bearer {tokens2['refresh']}"}
        )

        # Should fail because all tokens are blacklisted
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)


class TestPasswordResetRequest:
    """Test suite for password reset request endpoint"""

    reset_url = "/api/v1/auth/passwords/reset"

    async def test_password_reset_request_success(
        self,
        async_client: AsyncClient,
        verified_user: User,
        mock_email: list,
    ):
        reset_data = {"email": verified_user.email}
        response = await async_client.post(self.reset_url, json=reset_data)

        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "If that email address is in our database" in response_data["message"]

        assert len(mock_email) == 1
        email_data = mock_email[0]
        assert email_data["email_to"] == verified_user.email
        assert "otp" in email_data["template_context"]
        print(email_data["template_context"])
        assert email_data["template_name"] == "password_reset_email.html"

    async def test_password_reset_request_nonexistent_user(
        self,
        async_client: AsyncClient,
        mock_email: list,
    ):

        reset_data = {"email": "nonexistent@example.com"}

        response = await async_client.post(self.reset_url, json=reset_data)

        # Response looks identical to success case (security measure)
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "If that email address is in our database" in response_data["message"]

        # Assert: No email was sent (but response doesn't reveal this)
        assert len(mock_email) == 0

    async def test_password_reset_request_unverified_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
        mock_email: list,
    ):

        reset_data = {"email": registered_user.email}
        print(reset_data)

        response = await async_client.post(self.reset_url, json=reset_data)
        print(response.json())

        # Should succeed (unverified users can reset password)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"

        # Email should be sent
        assert len(mock_email) == 1

    async def test_password_reset_request_inactive_user(
        self,
        async_client: AsyncClient,
        inactive_user: User,
        mock_email: list,
    ):
        """Test password reset request for inactive user"""
        reset_data = {"email": inactive_user.email}

        response = await async_client.post(self.reset_url, json=reset_data)
        print(response.json())

        # Assert: Response is same (doesn't reveal account status)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"

        # email not sent
        assert len(mock_email) == 0

    async def test_password_reset_request_missing_email(
        self,
        async_client: AsyncClient,
    ):

        reset_data = {}

        response = await async_client.post(self.reset_url, json=reset_data)

        # Validation error
        assert response.status_code == 422
        response_data = response.json()
        print(response_data)

    async def test_password_reset_request_case_insensitive_email(
        self,
        async_client: AsyncClient,
        verified_user: User,
        mock_email: list,
    ):

        reset_data = {"email": verified_user.email.upper()}

        response = await async_client.post(self.reset_url, json=reset_data)

        assert response.status_code == 200

        assert len(mock_email) == 1
        assert mock_email[0]["email_to"] == verified_user.email.lower()


class TestPasswordResetVerifyOtp:
    """Test suite for password reset OTP verification endpoint"""

    verify_otp_url = "/api/v1/auth/passwords/reset/verify"
    reset_request_url = "/api/v1/auth/passwords/reset"

    async def test_verify_otp_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: User,
    ):

        # Create a valid OTP for the user
        otp = 123456
        otp_record = Otp(user_id=registered_user.id, otp=otp, is_valid=True)
        db_session.add(otp_record)
        await db_session.commit()

        # Verify the OTP
        response = await async_client.post(
            self.verify_otp_url,
            json={
                "email": registered_user.email,
                "otp": otp,
            },
        )

        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["status"] == "success"
        assert "proceed to set a new password" in data["message"].lower()
        
    async def test_verify_otp_inactive_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        inactive_user: User,
    ):

        # Create a valid OTP for the user
        otp = 123456
        otp_record = Otp(user_id=inactive_user.id, otp=otp, is_valid=True)
        db_session.add(otp_record)
        await db_session.commit()

        # Verify the OTP
        response = await async_client.post(
            self.verify_otp_url,
            json={
                "email": inactive_user.email,
                "otp": otp,
            },
        )

        # assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["status"] == "failure"
        assert "disabled" in data["message"].lower()


    async def test_verify_otp_user_not_found(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.post(
            self.verify_otp_url,
            json={
                "email": "nonexistent@example.com",
                "otp": 123456,
            },
        )

        assert response.status_code == 422
        data = response.json()
        print(data)
        assert data["err_code"] == "user_not_found"
# FastAPI Filters
# FastAPI-Users
# FastAPI-Admin
# pytest src/tests/test_auth.py::TestPasswordResetVerifyOtp -v -s
# pytest src/tests/test_auth.py::TestResendVerificationEmail::test_resend_otp_success -v -s
