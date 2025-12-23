from typing import List, Optional

from slugify import slugify
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.cloudinary_service import CloudinaryService
from src.constants import VoteType
from src.db.models import Profile, Project, Review, Tag, User


class ProjectService:
    """Handles all project-related database operations"""

    async def get_all_projects(
        self,
        session: AsyncSession,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Project]:
        """
        Get list of projects with optional search
        """
        statement = select(Project).join(Profile).join(User)

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(Project.title.ilike(pattern), Project.description.ilike(pattern))
            )

        # Order by popularity
        statement = statement.order_by(col(Project.vote_total).desc())

        statement = statement.offset(offset).limit(limit)

        result = await session.exec(statement)
        return result.all()

    async def get_project_by_slug(
        self, slug: str, session: AsyncSession
    ) -> Optional[Project]:
        """
        Get project by its slug
        """
        statement = select(Project).where(Project.slug == slug)
        result = await session.exec(statement)
        return result.first()

    async def create_project(
        self, project_data: dict, owner_id: str, session: AsyncSession
    ) -> Project:
        """
        Create a new project
        """

        # Generate slug from title
        base_slug = slugify(project_data["title"])
        slug = base_slug

        # Ensure uniqueness
        counter = 1
        while True:
            try:
                new_project = Project(
                    **project_data,
                    slug=slug,
                    owner_id=owner_id,
                )
                session.add(new_project)
                await session.flush()
                break
            except IntegrityError:
                await session.rollback()
                slug = f"{base_slug}-{counter}"
                counter += 1

        await session.commit()
        await session.refresh(new_project)
        return new_project

    async def update_project(
        self, project: Project, update_data: dict, session: AsyncSession
    ) -> Project:
        """
        Update project fields
        """
        for key, value in update_data.items():
            setattr(project, key, value)

        # If title changed, update slug
        if "title" in update_data:
            new_slug = slugify(update_data["title"])

            if new_slug != project.slug:
                # Generate unique slug with database constraint
                base_slug = new_slug
                counter = 1

                while True:
                    try:
                        project.slug = new_slug
                        session.add(project)
                        await session.flush()  # Check constraint without committing
                        break  # Success!
                    except IntegrityError:
                        # Slug conflict, try next number
                        await session.rollback()
                        new_slug = f"{base_slug}-{counter}"
                        counter += 1

        await session.commit()
        await session.refresh(project)
        return project

    async def delete_project(self, project: Project, session: AsyncSession) -> None:
        """
        Delete project and all related data
        """
        public_id = CloudinaryService.extract_public_id_from_url(project.featured_image)
        if public_id:
            await CloudinaryService.delete_image(public_id)

        await session.delete(project)
        await session.commit()

    async def get_or_create_tag(self, tag_name: str, session: AsyncSession) -> Tag:
        """
        Get existing tag or create new one

        WHY? Tags are reusable across projects
        Example: "React" tag should be shared by all React projects
        """
        statement = select(Tag).where(Tag.name.ilike(tag_name))
        result = await session.exec(statement)
        tag = result.first()

        if tag:
            return tag

        new_tag = Tag(name=tag_name.title())
        session.add(new_tag)
        await session.commit()
        await session.refresh(new_tag)
        return new_tag

    async def add_tag_to_project(
        self, project: Project, tag_name: str, session: AsyncSession
    ) -> Tag:
        """
        Add tag to project
        """
        tag = await self.get_or_create_tag(tag_name, session)

        if tag in project.tags:
            raise ValueError("Tag already exists on this project")

        project.tags.append(tag)
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return tag

    async def add_tags_to_project(
        self, project: Project, tags_string: str, session: AsyncSession
    ) -> List[Tag]:
        """
        Add multiple tags to project from comma-separated string

        Args:
            project: The project to add tags to
            tags_string: Comma-separated tag names (e.g., "React, TypeScript, Node.js")
            session: Database session

        Returns:
            List of Tag objects that were added

        Example:
            tags = await service.add_tags_to_project(
                project,
                "Python, FastAPI, PostgreSQL",
                session
            )
        """
        # Split by comma and clean up each tag name
        tag_names = [tag.strip() for tag in tags_string.split(",") if tag.strip()]

        if not tag_names:
            raise ValueError("No valid tags provided")

        added_tags = []
        existing_tag_names = [tag.name.lower() for tag in project.tags]

        for tag_name in tag_names:
            # Skip if tag already exists on project
            if tag_name.lower() in existing_tag_names:
                continue

            # Get or create tag
            tag = await self.get_or_create_tag(tag_name, session)

            # Add to project
            project.tags.append(tag)
            added_tags.append(tag)

        if added_tags:
            session.add(project)
            await session.commit()
            await session.refresh(project)

        return added_tags

    async def remove_tag_from_project(
        self, project: Project, tag_id: str, session: AsyncSession
    ) -> None:
        """
        Remove tag from project
        """
        tag = await session.get(Tag, tag_id)
        if not tag or tag not in project.tags:
            raise ValueError("Tag not found on this project")

        # Remove the link between project and tag
        project.tags.remove(tag)
        session.add(project)
        await session.commit()

    async def remove_tags_from_project(
        self, project: Project, tags_string: str, session: AsyncSession
    ) -> List[Tag]:
        """
        Remove multiple tags from project from comma-separated string

        Args:
            project: The project to remove tags from
            tags_string: Comma-separated tag names (e.g., "React, TypeScript, Node.js")
            session: Database session

        Returns:
            List of Tag objects that were removed

        Example:
            removed_tags = await service.remove_tags_from_project(
                project,
                "Python, FastAPI, PostgreSQL",
                session
            )
        """
        # Split by comma and clean up each tag name
        tag_names = [tag.strip() for tag in tags_string.split(",") if tag.strip()]

        if not tag_names:
            raise ValueError("No valid tags provided")

        removed_tags = []
        project_tag_map = {tag.name.lower(): tag for tag in project.tags}

        for tag_name in tag_names:
            # Find tag in project's current tags (case-insensitive)
            tag = project_tag_map.get(tag_name.lower())

            if not tag:
                # Tag not found on project, skip it
                continue

            # Remove tag from project
            project.tags.remove(tag)
            removed_tags.append(tag)

        if removed_tags:
            session.add(project)
            await session.commit()
            await session.refresh(project)

        return removed_tags

    async def get_all_tags(self, session: AsyncSession) -> List[Tag]:
        """Get all available tags"""
        statement = select(Tag).order_by(Tag.name)
        result = await session.exec(statement)
        return result.all()

    async def create_review(
        self,
        project_id: str,
        reviewer_profile_id: str,
        review_data: dict,
        session: AsyncSession,
    ) -> Review:
        """
        Create a review for a project
        """
        existing = await session.exec(
            select(Review).where(
                Review.project_id == project_id,
                Review.profile_id == reviewer_profile_id,
            )
        )
        if existing.first():
            raise ValueError("You have already reviewed this project")

        new_review = Review(
            project_id=project_id, profile_id=reviewer_profile_id, **review_data
        )

        session.add(new_review)
        await session.commit()
        await session.refresh(new_review)

        await self.update_project_votes(project_id, session)

        return new_review

    async def get_project_reviews(
        self, project_id: str, session: AsyncSession
    ) -> List[Review]:
        """Get all reviews for a project"""
        statement = (
            select(Review)
            .where(Review.project_id == project_id)
            .order_by(col(Review.created_at).desc())
        )
        result = await session.exec(statement)
        return result.all()

    async def update_project_votes(
        self, project_id: str, session: AsyncSession
    ) -> None:
        """
        Recalculate project vote statistics
        """
        project = await session.get(Project, project_id)
        if not project:
            return

        # Count total reviews
        total_reviews = await session.exec(
            select(func.count(Review.id)).where(Review.project_id == project_id)
        )
        vote_total = total_reviews.first() or 0

        upvotes = await session.exec(
            select(func.count(Review.id)).where(
                Review.project_id == project_id, Review.value == VoteType.up
            )
        )
        upvote_count = upvotes.first() or 0

        # Calculate ratio
        if vote_total > 0:
            vote_ratio = int((upvote_count / vote_total) * 100)
        else:
            vote_ratio = 0

        project.vote_total = vote_total
        project.vote_ratio = vote_ratio
        session.add(project)
        await session.commit()

    async def get_related_projects(
        self, project: Project, session: AsyncSession, limit: int = 6
    ) -> List[Project]:
        """
        Get projects related to current project
        """
        if not project.tags:
            return []

        tag_ids = [tag.id for tag in project.tags]

        statement = (
            select(Project)
            .join(Tag)
            .where(
                Tag.id.in_(tag_ids), Project.id != project.id  # Exclude current project
            )
            .order_by(col(Project.vote_total).desc())
            .limit(limit)
        )

        result = await session.exec(statement)
        return result.all()
