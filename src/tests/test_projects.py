from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Project, User

# pytest src/tests/test_projects.py::TestUpdateProject::test_update_project_success -v -s


class TestGetProjects:
    """Test suite for GET /projects/ endpoint"""

    get_projects_url = "/api/v1/projects/"

    async def test_get_projects_success(
        self,
        async_client: AsyncClient,
        multiple_projects,
    ):
        """
        Test successfully retrieving all projects.
        """
        # Act
        response = await async_client.get(self.get_projects_url)

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Projects retrieved successfully" in response_data["message"]
        assert "data" in response_data

        # Should have at least the projects from fixture
        assert len(response_data["data"]) >= 3

    async def test_get_projects_with_search(
        self,
        async_client: AsyncClient,
        multiple_projects,
    ):
        """
        Test searching projects by title or description.
        """
        # Act: Search by title keyword
        response = await async_client.get(
            self.get_projects_url, params={"search": "Python"}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        # Should find "Python Web Scraper" project
        assert len(response_data["data"]) >= 1
        found_titles = [p["title"] for p in response_data["data"]]
        assert any("Python" in title for title in found_titles)

        # Act: Search by description keyword
        response = await async_client.get(
            self.get_projects_url, params={"search": "React"}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["data"]) >= 1

    async def test_get_projects_with_pagination(
        self,
        async_client: AsyncClient,
        multiple_projects,
    ):
        """
        Test pagination with limit and offset.
        """
        # Act: Get first 2 projects
        response = await async_client.get(
            self.get_projects_url, params={"limit": 2, "offset": 0}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["data"]) <= 2
        print(len(response_data["data"]))

        # Act: Get next projects
        response = await async_client.get(
            self.get_projects_url, params={"limit": 2, "offset": 2}
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

    async def test_get_projects_empty_database(
        self,
        async_client: AsyncClient,
    ):
        """
        Test retrieving projects when database is empty.
        """
        # Act
        response = await async_client.get(self.get_projects_url)

        # Assert
        assert response.status_code == 200
        response_data = response.json()

        # Should return empty list or structure
        print(response_data["data"])
        assert isinstance(response_data["data"], list)

    async def test_get_projects_invalid_pagination(
        self,
        async_client: AsyncClient,
    ):
        """
        Test with invalid pagination parameters.
        """
        # Act: Negative limit
        response = await async_client.get(self.get_projects_url, params={"limit": -1})

        # Assert
        assert response.status_code == 422
        print(response.json())

        # Act: Limit too high
        response = await async_client.get(self.get_projects_url, params={"limit": 101})

        # Assert
        assert response.status_code == 422
        print(response.json())


class TestCreateProject:
    """Test suite for POST /projects/ endpoint"""

    create_project_url = "/api/v1/projects/"
    login_url = "/api/v1/auth/token"

    async def test_create_project_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test creating a project with featured image.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Create project with image
        from io import BytesIO

        fake_image = BytesIO(b"fake project image")
        files = {"featured_image": ("project.jpg", fake_image, "image/jpeg")}

        project_data = {
            "title": "Test Project",
            "description": "Test Description",
            "source_link": "https://github.com/test",
            "demo_link": "https://demo.test.com",
        }

        response = await async_client.post(
            self.create_project_url,
            data=project_data,
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 201
        response_data = response.json()
        print(response_data)

        data = response_data["data"]
        assert "featured_image" in data
        # Should have Cloudinary URL from mock
        assert data["featured_image"] == mock_cloudinary["url"]

        assert response_data["status"] == "success"
        assert "Project created successfully" in response_data["message"]
        assert "data" in response_data

        assert data["title"] == project_data["title"]
        # Check that the mock cloudinary URL was used
        assert "https://res.cloudinary.com" in data["featured_image"]

        # Verify in database
        statement = select(Project).where(Project.title == project_data["title"])
        result = await db_session.exec(statement)
        project = result.first()
        assert project is not None

    async def test_create_project_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """
        Test creating project without authentication.
        """
        # Act
        project_data = {
            "title": "Should Fail",
            "description": "This should fail",
        }

        response = await async_client.post(
            self.create_project_url,
            data=project_data,
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_create_project_invalid_data(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test creating project with missing required fields.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Missing title
        project_data = {"description": "Missing title"}

        response = await async_client.post(
            self.create_project_url,
            data=project_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 422
        print(response.json())

        # Act: Missing description
        project_data = {"title": "Missing Description"}

        response = await async_client.post(
            self.create_project_url,
            json=project_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 422
        print(response.json())

    async def test_create_project_duplicate_title(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        verified_user: User,
        sample_project,
        user3_data: dict,
        mock_cloudinary,
    ):
        """
        Test creating project with duplicate title (should handle slug conflict).
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]
        print(sample_project.title)

        # Act: Create project with same title as sample_project
        from io import BytesIO

        fake_image = BytesIO(b"fake project image")
        files = {"featured_image": ("project.jpg", fake_image, "image/jpeg")}

        project_data = {
            "title": sample_project.title,
            "description": "Duplicate title test",
        }
        print(project_data)

        response = await async_client.post(
            self.create_project_url,
            data=project_data,
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        response_data = response.json()

        data = response_data["data"]

        # Assert: Should handle slug conflict
        assert "1" in data["slug"]

        print(response.json())


class TestGetProject:
    """Test suite for GET /projects/{slug} endpoint"""

    def get_project_url(self, slug: str):
        return f"/api/v1/projects/{slug}"

    async def test_get_project_success(
        self,
        async_client: AsyncClient,
        sample_project,
    ):
        """
        Test successfully retrieving a project by slug.
        """
        # Act
        response = await async_client.get(self.get_project_url(sample_project.slug))

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Project retrieved successfully" in response_data["message"]
        assert "data" in response_data

        data = response_data["data"]
        assert data["slug"] == sample_project.slug
        assert data["title"] == sample_project.title

    async def test_get_project_not_found(
        self,
        async_client: AsyncClient,
    ):
        """
        Test retrieving non-existent project.
        """
        # Act
        response = await async_client.get(self.get_project_url("nonexistent-slug"))

        # Assert
        assert response.status_code == 404
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "not_found"

    async def test_get_project_with_tags(
        self,
        async_client: AsyncClient,
        project_with_tags,
    ):
        """
        Test retrieving project that has tags.
        """
        # Act
        response = await async_client.get(self.get_project_url(project_with_tags.slug))

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        data = response_data["data"]
        assert "tags" in data
        assert len(data["tags"]) > 0

    async def test_get_project_with_reviews(
        self,
        async_client: AsyncClient,
        project_with_reviews,
    ):
        """
        Test retrieving project that has reviews.
        """
        # Act
        response = await async_client.get(
            self.get_project_url(project_with_reviews.slug)
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        data = response_data["data"]
        assert "reviews" in data
        assert len(data["reviews"]) > 0


class TestUpdateProject:
    """Test suite for PATCH /projects/{slug} endpoint"""

    def get_update_url(self, slug: str):
        return f"/api/v1/projects/{slug}"

    login_url = "/api/v1/auth/token"

    async def test_update_project_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_project,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test successfully updating a project.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Update project
        update_data = {
            "title": "Updated Project Title",
            "description": "Updated description",
            "demo_link": "https://new-demo-link.com",
        }

        response = await async_client.patch(
            self.get_update_url(sample_project.slug),
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        # assert response.status_code == 200
        response_data = response.json()
        print(response_data)

        assert response_data["status"] == "success"
        assert "Project updated successfully" in response_data["message"]

        # Verify in database
        assert sample_project.title == update_data["title"]
        assert sample_project.description == update_data["description"]

    async def test_update_project_not_found(
        self,
        async_client: AsyncClient,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test updating non-existent project.
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act
        update_data = {"title": "Should Fail"}

        response = await async_client.patch(
            self.get_update_url("nonexistent-slug"),
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 404
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "not_found"

    async def test_update_project_not_owner(
        self,
        async_client: AsyncClient,
        another_user_project,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test updating project owned by another user.
        """
        # Arrange: Login as verified_user (not the owner)
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        # Act: Try to update another user's project
        update_data = {"title": "Stealing this project"}

        response = await async_client.patch(
            self.get_update_url(another_user_project.slug),
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 403
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "insufficient_permission"

    async def test_update_project_unauthenticated(
        self,
        async_client: AsyncClient,
        sample_project,
    ):
        """
        Test updating project without authentication.
        """
        # Act
        update_data = {"title": "Should Fail"}

        response = await async_client.patch(
            self.get_update_url(sample_project.slug),
            json=update_data,
        )

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        print(response_data)
        assert response_data["err_code"] == "unauthorized"

    async def test_update_project_partial_update(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_project,
        verified_user: User,
        user3_data: dict,
    ):
        """
        Test partial update (only some fields).
        """
        # Arrange: Login
        login_data = {
            "email": verified_user.email,
            "password": user3_data["password"],
        }
        login_response = await async_client.post(self.login_url, json=login_data)
        tokens = login_response.json()
        access_token = tokens["access"]

        original_title = sample_project.title

        # Act: Update only description
        update_data = {"description": "Only updating description"}

        response = await async_client.patch(
            self.get_update_url(sample_project.slug),
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200

        # Verify title unchanged
        assert sample_project.title == original_title
        assert sample_project.description == update_data["description"]
        assert sample_project.title == original_title
        assert sample_project.description == update_data["description"]
