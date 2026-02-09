from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import User

# pytest src/tests/test_profiles.py::TestGetMyProfile::test_get_user_profile_success -v -s


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


# pytest src/tests/test_profiles.py::TestGetProfiles::test_get_profiles_success -v -s
# pytest src/tests/test_profiles.py::TestGetMyProfile -v -s
