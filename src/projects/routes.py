from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.utils import SUCCESS_EXAMPLE
from src.cloudinary_service import CloudinaryService
from src.db.main import get_session
from src.db.models import User
from src.errors import InsufficientPermission, NotFound, UnprocessableEntity
from src.profiles.service import ProfileService
from src.projects.schema_examples import (
    ADD_TAGS_PROJECT_RESPONSES,
    CREATE_PROJECT_RESPONSES,
    CREATE_REVIEW_RESPONSES,
    DELETE_PROJECT_RESPONSES,
    GET_ALL_TAGS_RESPONSES,
    GET_RELATED_PROJECTS_RESPONSES,
    REMOVE_TAGS_PROJECT_RESPONSES,
    UPDATE_PROJECT_RESPONSES,
)
from src.projects.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectOwnerInfo,
    ProjectResponse,
    ProjectResponseData,
    ProjectUpdate,
    ReviewCreate,
    ReviewResponse,
    TagCreate,
    TagListResponse,
    TagResponse,
)
from src.projects.service import ProjectService

router = APIRouter()
project_service = ProjectService()
profile_service = ProfileService()
cloudinary_service = CloudinaryService()


def build_project_response(project) -> ProjectResponse:
    """
    Convert Project model to ProjectResponse
    """
    return ProjectResponse(
        status="",
        message="",
        data=ProjectResponseData(
            id=str(project.id),
            title=project.title,
            slug=project.slug,
            description=project.description,
            featured_image=project.featured_image,
            source_link=project.source_link,
            demo_link=project.demo_link,
            vote_total=project.vote_total,
            vote_ratio=project.vote_ratio,
            created_at=project.created_at,
            updated_at=project.updated_at,
            owner=ProjectOwnerInfo(
                user_id=str(project.owner.user_id),
                username=project.owner.user.username,
                full_name=project.owner.user.full_name,
                avatar_url=project.owner.avatar_url,
            ),
            tags=[
                TagResponse(id=str(tag.id), name=tag.name, created_at=tag.created_at)
                for tag in (project.tags or [])
            ],
            reviews=[
                ReviewResponse(
                    id=str(review.id),
                    value=review.value,
                    content=review.content,
                    created_at=review.created_at,
                    reviewer=ProjectOwnerInfo(
                        user_id=str(project.owner.user_id),
                        username=project.owner.user.username,
                        full_name=project.owner.user.full_name,
                        avatar_url=project.owner.avatar_url,
                    ),
                )
                for review in (project.reviews or [])
            ],
        ),
    )


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    search: str = Query(None, description="Search by title or description"),
    limit: int = Query(20, ge=1, le=100, description="Number of projects"),
    offset: int = Query(0, ge=0, description="Skip projects"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all projects with search and pagination

    EXAMPLE:
    - GET /projects/ → First 20 projects
    - GET /projects/?search=react → Projects mentioning "react"
    - GET /projects/?limit=10&offset=20 → Projects 21-30
    """
    projects = await project_service.get_all_projects(
        session=session, search=search, limit=limit, offset=offset
    )
    # return [
    #     ProjectListResponse(
    #         status=SUCCESS_EXAMPLE,
    #         message="Projects retrieved successfully",
    #         data=ProjectListResponseData(
    #             id=str(p.id),
    #             title=p.title,
    #             slug=p.slug,
    #             description=p.description,
    #             featured_image=p.featured_image,
    #             vote_total=p.vote_total,
    #             vote_ratio=p.vote_ratio,
    #             owner=ProjectOwnerInfo(
    #                 user_id=str(p.owner.user_id),
    #                 username=p.owner.user.username,
    #                 full_name=p.owner.user.full_name,
    #                 avatar_url=p.owner.avatar_url,
    #             ),
    #             tags=[
    #                 TagResponse(id=str(t.id), name=t.name, created_at=t.created_at)
    #                 for t in (p.tags or [])
    #             ],
    #             reviews=[
    #                 ReviewResponse(
    #                     id=str(r.id),
    #                     value=r.value,
    #                     content=r.content,
    #                     created_at=r.created_at,
    #                     reviewer=ProjectOwnerInfo(
    #                         user_id=str(p.owner.user_id),
    #                         username=p.owner.user.username,
    #                         full_name=p.owner.user.full_name,
    #                         avatar_url=p.owner.avatar_url,
    #                     ),
    #                 )
    #                 for r in (p.reviews or [])
    #             ],
    #         ),
    #     )
    #     for p in projects
    # ]
    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Projects retrieved successfully",
        "data": [p for p in projects],
    }


@router.post(
    "/",
    responses=CREATE_PROJECT_RESPONSES,
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_data: ProjectCreate,
    featured_image: UploadFile = File(None, description="Project featured image"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new project
    """
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    featured_image_url = None
    if featured_image:
        public_id = f"project_{current_user.id}_{featured_image.filename}"
        upload_result = await cloudinary_service.upload_image(
            file=featured_image,
            folder="project_images",
            public_id=public_id,
        )
        featured_image_url = upload_result["url"]

    project_dict = project_data.model_dump()
    if featured_image_url:
        project_dict["featured_image"] = featured_image_url

    new_project = await project_service.create_project(
        project_data=project_dict,
        owner_id=str(profile.id),
        session=session,
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Project created successfully",
        "data": new_project,
    }


@router.get("/{slug}", response_model=ProjectResponse)
async def get_project(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific project by its slug
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Project retrieved successfully",
        "data": project,
    }


@router.patch(
    "/{slug}", responses=UPDATE_PROJECT_RESPONSES, response_model=ProjectResponse
)
async def update_project(
    slug: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update a project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    if str(project.owner_id) != str(current_user.id):
        raise InsufficientPermission("You can only update your own projects")

    update_data = project_data.model_dump(exclude_unset=True)
    updated_project = await project_service.update_project(
        project, update_data, session
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Project updated successfully",
        "data": updated_project,
    }


@router.delete(
    "/{slug}",
    responses=DELETE_PROJECT_RESPONSES,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    slug: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    # Security check
    if str(project.owner.user_id) != str(current_user.id):
        raise InsufficientPermission("You can only delete your own projects")

    await project_service.delete_project(project, session)

    return None  # 204 No Content


@router.patch(
    "/{slug}/image", responses=UPDATE_PROJECT_RESPONSES, response_model=ProjectResponse
)
async def update_project_image(
    slug: str,
    featured_image: UploadFile = File(description="New project image"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update project's featured image
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    if str(project.owner_id) != str(current_user.id):
        raise InsufficientPermission("You can only update your own projects")

    public_id = f"project_{current_user.id}_{slug}"
    upload_result = await cloudinary_service.upload_image(
        file=featured_image,
        folder="project_images",
        public_id=public_id,
        overwrite=True,  # Replace existing image
    )

    updated_project = await project_service.update_project(
        project, {"featured_image": upload_result["url"]}, session
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Project image updated successfully",
        "data": updated_project,
    }


@router.post(
    "/{slug}/reviews",
    responses=CREATE_REVIEW_RESPONSES,
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    slug: str,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Add a review to a project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    # Get reviewer's profile
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    # Can't review your own project
    if str(project.owner_id) == str(profile.id):
        raise UnprocessableEntity("You cannot review your own project")

    try:
        review = await project_service.create_review(
            project_id=str(project.id),
            reviewer_profile_id=str(profile.id),
            review_data=review_data.model_dump(),
            session=session,
        )
    except ValueError as e:
        raise UnprocessableEntity(str(e))

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Review created successfully",
        "data": review,
    }


@router.get(
    "/{slug}/reviews", responses=CREATE_REVIEW_RESPONSES, response_model=ReviewResponse
)
async def get_project_reviews(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get all reviews for a project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    reviews = await project_service.get_project_reviews(str(project.id), session)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Reviews retrieved successfully",
        "data": [r for r in reviews],
    }


@router.patch(
    "/{slug}/tags", responses=ADD_TAGS_PROJECT_RESPONSES, response_model=TagListResponse
)
async def add_tags_to_project(
    slug: str,
    tags: str = Query(
        description="Comma-separated tag names (e.g., 'React, TypeScript, Node.js')"
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Add a tag to project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    if str(project.owner_id) != str(current_user.id):
        raise InsufficientPermission("You can only add tags to your own projects")

    try:
        added_tags = await project_service.add_tags_to_project(project, tags, session)
    except ValueError as e:
        raise UnprocessableEntity(str(e))

    return {
        "status": SUCCESS_EXAMPLE,
        "message": f"{len(added_tags)} tag(s) added to project",
        "data": added_tags,
    }


@router.delete(
    "/{slug}/tags",
    responses=REMOVE_TAGS_PROJECT_RESPONSES,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_tag_from_project(
    slug: str,
    tags: str = Query(
        description="Comma-separated tag names to remove (e.g., 'React, TypeScript')"
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove tag from project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    if str(project.owner_id) != str(current_user.id):
        InsufficientPermission("You can only remove tags from your own projects")

    try:
        removed_tags = await project_service.remove_tags_from_project(
            project, tags, session
        )
    except ValueError as e:
        raise UnprocessableEntity(str(e))

    if not removed_tags:
        raise NotFound("None of the specified tags were found on this project")

    return None


@router.get("/tags", responses=GET_ALL_TAGS_RESPONSES, response_model=List[TagResponse])
async def get_all_tags(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all available tags
    """
    tags = await project_service.get_all_tags(session)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Tags retrieved successfully",
        "data": [t for t in tags],
    }


@router.get(
    "/{slug}/related-projects",
    responses=GET_RELATED_PROJECTS_RESPONSES,
    response_model=ProjectListResponse,
)
async def get_related_projects(
    slug: str,
    limit: int = Query(6, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    """
    Get projects related to current project
    """
    project = await project_service.get_project_by_slug(slug, session)

    if not project:
        raise NotFound(f"Project with slug '{slug}' not found")

    related = await project_service.get_related_projects(project, session, limit=limit)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Related projects retrieved successfully",
        "data": [p for p in related],
    }
