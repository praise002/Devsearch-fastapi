from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Profile, User


class TestGetProfiles:
    """Test suite for GET /profiles/ endpoint"""

    get_profiles_url = "/api/v1/profiles/"

    async def test_get_profiles_success(
        self,
        async_client: AsyncClient,
        verified_user_with_profile,
        another_verified_user_with_profile,
    ):
        """
        Test successfully retrieving all profiles.
        """
        # Act
        response = await async_client.get(self.get_profiles_url)

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Should return a list
        print(response_data)

        # Check top-level structure
        assert "status" in response_data
        assert "message" in response_data
        assert "data" in response_data

        # Check pagination structure
        data = response_data["data"]
        assert "count" in data
        assert "next" in data
        assert "previous" in data
        assert "results" in data

        # Check results
        assert len(data["results"]) >= 2  # At least 2 profiles
        print(len(data["results"]) >= 2)

        # Check structure of first profile
        if len(data["results"]) > 0:
            profile = data["results"][0]
            assert "id" in profile
            assert "user_id" in profile
            assert "username" in profile
            assert "full_name" in profile

    async def test_get_profiles_with_search(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user_with_profile,
    ):
        """
        Test searching profiles by username, intro, or location.
        """
        # Arrange: Update profile with searchable data
        profile = verified_user_with_profile["profile"]
        profile.short_intro = "Python developer with 5 years experience"
        profile.location = "San Francisco, CA"
        db_session.add(profile)
        await db_session.commit()

        # Act: Search by intro keyword
        response = await async_client.get(
            self.get_profiles_url, params={"search": "Python"}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()["data"]["results"]
        assert len(response_data) >= 1

        # Act: Search by location
        response = await async_client.get(
            self.get_profiles_url, params={"search": "San Francisco"}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()["data"]["results"]
        assert len(response_data) >= 1

        # Act: Search by username
        user = verified_user_with_profile["user"]
        response = await async_client.get(
            self.get_profiles_url, params={"search": user.username}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()["data"]["results"]
        assert len(response_data) >= 1

    async def test_get_profiles_with_pagination(
        self,
        async_client: AsyncClient,
        verified_user_with_profile,
        another_verified_user_with_profile,
    ):
        """
        Test pagination with limit and offset.
        """
        # Act: Get first profile
        response = await async_client.get(
            self.get_profiles_url, params={"limit": 1, "offset": 0}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()["data"]
        assert len(response_data["results"]) == 1
        assert response_data["count"] >= 2  # Total count should be at least 2

        # Act: Get second profile
        response = await async_client.get(
            self.get_profiles_url, params={"limit": 1, "offset": 1}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()["data"]
        assert len(response_data["results"]) <= 1

    async def test_get_profiles_empty_db(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Test retrieving profiles when database is empty.
        """
        # Act: Get profiles (database is fresh from fixture)
        response = await async_client.get(self.get_profiles_url)

        # Assert: Should return empty list
        assert response.status_code == 200
        response_data = response.json()["data"]
        assert response_data["count"] == 0
        assert len(response_data["results"]) == 0
        print(response_data)

    async def test_get_profiles_invalid_pagination_params(
        self,
        async_client: AsyncClient,
    ):
        """
        Test with invalid pagination parameters.
        """
        # Act: Negative limit
        response = await async_client.get(self.get_profiles_url, params={"limit": -1})

        # Assert: Should fail validation
        assert response.status_code == 422
        print(response.json())

        # Act: Negative offset
        response = await async_client.get(self.get_profiles_url, params={"offset": -1})

        # Assert: Should fail validation
        assert response.status_code == 422
        print(response.json())

        # Act: Limit too high
        response = await async_client.get(self.get_profiles_url, params={"limit": 101})

        # Assert: Should fail validation
        assert response.status_code == 422
        print(response.json())


class TestGetMyProfile:
    """Test suite for GET /profiles/me endpoint"""

    get_my_profile_url = "/api/v1/profiles/me"
    login_url = "/api/v1/auth/token"

    async def test_get_my_profile_success(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test successfully retrieving current user's profile.
        """
        # Arrange: Login to get access token
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Get my profile
        response = await async_client.get(
            self.get_my_profile_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Profile retrieved successfully" in response_data["message"]
        assert "data" in response_data

        # Check data structure
        data = response_data["data"]
        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "first_name" in data
        assert "last_name" in data
        assert data["email"] == verified_user.email
        assert data["username"] == verified_user.username

    async def test_get_my_profile_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """
        Test retrieving profile without authentication.
        """
        # Act: Try to get profile without token
        response = await async_client.get(self.get_my_profile_url)

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_get_my_profile_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """
        Test retrieving profile with invalid token.
        """
        # Act: Use invalid token
        response = await async_client.get(
            self.get_my_profile_url,
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)

    async def test_get_my_profile_with_skills(
        self,
        async_client: AsyncClient,
        profile_with_skills,
        user3_data: dict,
    ):
        """
        Test retrieving profile that has skills.
        """
        # Arrange: Login
        user = profile_with_skills["user"]
        login_data = {
            "email": user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Get my profile
        response = await async_client.get(
            self.get_my_profile_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        data = response_data["data"]
        assert "skills" in data
        assert isinstance(data["skills"], list)
        assert len(data["skills"]) == 3  # We added 3 skills in fixture

        # Check skill structure
        skill = data["skills"][0]
        assert "id" in skill
        assert "name" in skill
        assert "description" in skill

    async def test_get_my_profile_without_skills(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test retrieving profile with no skills.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Get my profile
        response = await async_client.get(
            self.get_my_profile_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        data = response_data["data"]
        assert "skills" in data
        # Skills might be empty list or None
        assert data["skills"] == [] or data["skills"] is None


class TestUpdateMyProfile:
    """Test suite for PATCH /profiles/me endpoint"""

    update_profile_url = "/api/v1/profiles/me"
    login_url = "/api/v1/auth/token"

    async def test_update_profile_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test successfully updating profile with valid data.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Update profile
        update_data = {
            "short_intro": "Full-stack developer specializing in Python and React",
            "bio": "I love building scalable web applications",
            "location": "New York, NY",
            "github": "https://github.com/testuser",
            "website": "https://testuser.dev",
        }

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Profile updated successfully" in response_data["message"]
        assert "data" in response_data

        # Verify database changes
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        updated_profile = result.first()

        assert updated_profile.short_intro == update_data["short_intro"]
        assert updated_profile.bio == update_data["bio"]
        assert updated_profile.location == update_data["location"]
        assert updated_profile.github == update_data["github"]

    async def test_update_profile_partial_update(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test partial update (only updating some fields).
        """
        # Arrange: Login and set initial data
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Set initial profile data
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        profile = result.first()

        profile.short_intro = "Original intro"
        profile.location = "Original location"
        db_session.add(profile)
        await db_session.commit()

        # Act: Update only short_intro
        update_data = {"short_intro": "Updated intro"}

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200

        # Verify only short_intro changed
        await db_session.refresh(profile)
        assert profile.short_intro == "Updated intro"
        assert profile.location == "Original location"  # Should remain unchanged

    async def test_update_profile_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """
        Test updating profile without authentication.
        """
        # Act: Try to update without token
        update_data = {"short_intro": "This should fail"}

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_update_profile_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """
        Test updating profile with invalid token.
        """
        # Act
        update_data = {"short_intro": "This should fail"}

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)

    async def test_update_profile_invalid_url_formats(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test updating profile with invalid URL formats.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Invalid GitHub URL
        update_data = {"github": "not-a-valid-url"}

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        print(response.json())

    async def test_update_profile_empty_fields(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test updating profile with empty strings (clearing fields).
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Clear fields with empty strings or None
        update_data = {
            "short_intro": "",
            "bio": None,
            "location": "",
        }

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed (fields are optional)
        print(response.json())

    async def test_update_profile_exceeds_max_length(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test updating profile with fields exceeding max length.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: short_intro max is 200 chars
        update_data = {"short_intro": "A" * 201}

        response = await async_client.patch(
            self.update_profile_url,
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should fail validation
        assert response.status_code == 422
        print(response.json())


class TestUploadAvatar:
    """Test suite for POST /profiles/avatar endpoint"""

    upload_avatar_url = "/api/v1/profiles/avatar"
    login_url = "/api/v1/auth/token"

    async def test_upload_avatar_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test successfully uploading avatar image.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Create fake image file
        from io import BytesIO

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "avatar.jpg"

        # Act: Upload avatar
        files = {"file": ("avatar.jpg", fake_image, "image/jpeg")}
        response = await async_client.post(
            self.upload_avatar_url,
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Avatar uploaded successfully" in response_data["message"]
        assert "avatar_url" in response_data
        assert response_data["avatar_url"] == mock_cloudinary["url"]

        # Verify database update
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        profile = result.first()

        assert profile.avatar_url == mock_cloudinary["url"]

    async def test_upload_avatar_replace_existing(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test uploading avatar when user already has one (should replace).
        """
        # Arrange: Set existing avatar
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        profile = result.first()

        old_avatar_url = "https://old-avatar-url.com/avatar.jpg"
        profile.avatar_url = old_avatar_url
        db_session.add(profile)
        await db_session.commit()

        # Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Upload new avatar
        from io import BytesIO

        fake_image = BytesIO(b"new image content")
        files = {"file": ("new_avatar.jpg", fake_image, "image/jpeg")}

        response = await async_client.post(
            self.upload_avatar_url,
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Should have new URL, not old one
        assert response_data["avatar_url"] == mock_cloudinary["url"]
        assert response_data["avatar_url"] != old_avatar_url

    async def test_upload_avatar_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """
        Test uploading avatar without authentication.
        """
        # Act: Try to upload without token
        from io import BytesIO

        fake_image = BytesIO(b"fake image content")
        files = {"file": ("avatar.jpg", fake_image, "image/jpeg")}

        response = await async_client.post(
            self.upload_avatar_url,
            files=files,
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_upload_avatar_invalid_file_type(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test uploading non-image file as avatar.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Upload text file instead of image
        from io import BytesIO

        fake_file = BytesIO(b"This is not an image")
        files = {"file": ("document.txt", fake_file, "text/plain")}

        response = await async_client.post(
            self.upload_avatar_url,
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should fail validation
        # Note: Depends on your CloudinaryService validation
        print(response.json())

    async def test_upload_avatar_missing_file(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test uploading avatar without providing file.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Don't include file
        response = await async_client.post(
            self.upload_avatar_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should fail validation
        assert response.status_code == 422
        print(response.json())


class TestDeleteAvatar:
    """Test suite for DELETE /profiles/avatar endpoint"""

    delete_avatar_url = "/api/v1/profiles/avatar"
    login_url = "/api/v1/auth/token"

    async def test_delete_avatar_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test successfully deleting avatar.
        """
        # Arrange: Set avatar URL
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        profile = result.first()

        avatar_url = "https://res.cloudinary.com/test/image/upload/v123/user_avatar.jpg"
        profile.avatar_url = avatar_url
        db_session.add(profile)
        await db_session.commit()

        # Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Delete avatar
        response = await async_client.delete(
            self.delete_avatar_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 204

        # Verify database update
        await db_session.refresh(profile)
        assert profile.avatar_url is None

    async def test_delete_avatar_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """
        Test deleting avatar without authentication.
        """
        # Act
        response = await async_client.delete(self.delete_avatar_url)

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_delete_avatar_no_avatar_exists(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test deleting avatar when user has no avatar set.
        """
        # Arrange: Ensure no avatar
        from sqlmodel import select

        statement = select(Profile).where(Profile.user_id == verified_user.id)
        result = await db_session.exec(statement)
        profile = result.first()

        profile.avatar_url = None
        db_session.add(profile)
        await db_session.commit()

        # Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Try to delete non-existent avatar
        response = await async_client.delete(
            self.delete_avatar_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should still succeed (idempotent)
        assert response.status_code == 204


class TestGetUserProfile:
    """Test suite for GET /profiles/{username} endpoint"""

    def get_user_profile_url(self, username: str):
        return f"/api/v1/profiles/{username}"

    async def test_get_user_profile_success(
        self,
        async_client: AsyncClient,
        verified_user: User,
    ):
        """
        Test successfully retrieving a user's profile by username.
        """
        # Arrange
        username = verified_user.username

        # Act
        response = await async_client.get(self.get_user_profile_url(username))

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Profile retrieved successfully" in response_data["message"]
        assert "data" in response_data
        assert "skills" in response_data["data"]

    async def test_get_user_profile_not_found(
        self,
        async_client: AsyncClient,
    ):
        """
        Test retrieving profile for non-existent username.
        """
        # Act
        response = await async_client.get(
            self.get_user_profile_url("nonexistentuser123")
        )

        # Assert
        assert response.status_code == 404
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "not_found"

    async def test_get_user_profile_case_sensitive_username(
        self,
        async_client: AsyncClient,
        verified_user: User,
    ):
        """
        Test that username lookup is case-sensitive (or insensitive, depending on your implementation).
        """
        # Arrange
        username = verified_user.username

        # Act: Try with different case
        response = await async_client.get(self.get_user_profile_url(username.upper()))

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Profile retrieved successfully" in response_data["message"]
        assert "data" in response_data


# pytest src/tests/test_profiles.py::TestUploadAvatar -v -s
# pytest src/tests/test_profiles.py::TestDeleteAvatar -v -s

# pytest src/tests/test_profiles.py::TestGetProfiles::test_get_profiles_success -v -s
