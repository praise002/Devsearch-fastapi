from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import SUCCESS_EXAMPLE
from src.db.main import get_session
from src.db.models import User
from src.errors import InsufficientPermission, NotFound
from src.messaging.schema_examples import (
    DELETE_RESPONSES,
    GET_MESSAGE_RESPONSES,
    GET_UNREAD_COUNT_RESPONSES,
    GET_USER_MESSAGES_RESPONSES,
    MARK_MESSAGE_RESPONSES,
)
from src.messaging.schemas import (
    MessageCreate,
    MessageListResponse,
    MessageMarkResponse,
    MessageResponse,
    MessageSendResponse,
    MessageUnreadCountResponse,
)
from src.messaging.service import MessageService
from src.profiles.service import ProfileService

router = APIRouter()
message_service = MessageService()
profile_service = ProfileService()


@router.get(
    "/", responses=GET_USER_MESSAGES_RESPONSES, response_model=MessageListResponse
)
async def get_my_messages(
    unread_only: bool = Query(False, description="Show only unread messages"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages"),
    offset: int = Query(0, ge=0, description="Skip messages"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get all messages in your inbox

    EXAMPLE:
    - GET /messages/ → All messages
    - GET /messages/?unread_only=true → Only unread
    - GET /messages/?limit=20&offset=0 → First 20 messages
    """

    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if not profile:
        raise NotFound("Profile not found")

    messages = await message_service.get_user_messages(
        profile_id=str(profile.id),
        session=session,
        only_unread=unread_only,
        limit=limit,
        offset=offset,
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Messages retrieved successfully",
        "data": [m for m in messages],
    }


@router.post(
    "/", response_model=MessageSendResponse, status_code=status.HTTP_201_CREATED
)
async def send_message(
    message_data: MessageCreate,
    recipient_username: str = Query(description="Username of message recipient"),
    session: AsyncSession = Depends(get_session),
):
    """
    Send a message to a user

    Anyone can send (no auth required - public contact form)

    EXAMPLE:
    POST /messages/?recipient_username=johndoe
    {
      "name": "Jane Smith",
      "email": "jane@example.com",
      "subject": "Question about your project",
      "body": "Hi, I saw your React project and have a question..."
    }
    """
    recipient_profile = await profile_service.get_profile_by_username(
        recipient_username, session
    )

    if not recipient_profile:
        raise NotFound(f"User '{recipient_username}' not found")

    await message_service.create_message(
        recipient_profile_id=str(recipient_profile.id),
        message_data=message_data.model_dump(),
        session=session,
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Messages sent successfully",
    }


@router.get(
    "/{message_id}", responses=GET_MESSAGE_RESPONSES, response_model=MessageResponse
)
async def get_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific message by ID
    """
    message = await message_service.get_message_by_id(message_id, session)

    if not message:
        raise NotFound("Message not found")

    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if str(message.recipient_id) != str(profile.id):
        raise InsufficientPermission("You can only read your own messages")

    if not message.is_read:
        message = await message_service.mark_as_read(message, session)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Message retrieved successfully",
        "data": message,
    }


@router.patch(
    "/{message_id}",
    responses=MARK_MESSAGE_RESPONSES,
    response_model=MessageMarkResponse,
)
async def mark_message_as_unread(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Mark a message as unread
    """

    message = await message_service.get_message_by_id(message_id, session)

    if not message:
        raise NotFound("Message not found")

    # Get user's profile - exists if user exists
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if str(message.recipient_id) != str(profile.id):
        raise InsufficientPermission("You can only mark your own messages as unread")

    if not message.is_read:
        message = await message_service.mark_as_unread(message, session)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Message marked as unread",
        "is_read": message.is_read,
    }


@router.get(
    "/unread/count",
    responses=GET_UNREAD_COUNT_RESPONSES,
    response_model=MessageUnreadCountResponse,
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get count of unread messages
    """
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    count = await message_service.get_unread_count(str(profile.id), session)

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Count of unread messages retrieved successfully",
        "unread_count": count,
    }


@router.delete(
    "/{message_id}", responses=DELETE_RESPONSES, status_code=status.HTTP_204_NO_CONTENT
)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a message
    """
    message = await message_service.get_message_by_id(message_id, session)

    if not message:
        raise NotFound("Message not found")

    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if str(message.recipient_id) != str(profile.id):
        raise InsufficientPermission("You can only delete your own messages")

    await message_service.delete_message(message, session)

    return None
