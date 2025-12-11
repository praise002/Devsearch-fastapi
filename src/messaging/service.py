from typing import List, Optional

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Message, Profile, User


class MessageService:
    """Handles all message-related database operations"""

    async def get_user_messages(
        self,
        profile_id: str,
        session: AsyncSession,
        only_unread: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """
        Get messages for a user's inbox
        USE CASE:
        User's inbox showing all messages they've received
        """
        statement = select(Message).where(Message.recipient_id == profile_id)

        # Filter unread only
        if only_unread:
            statement = statement.where(Message.is_read == False)

        # Order by newest first
        statement = statement.order_by(col(Message.created_at).desc())

        # Pagination
        statement = statement.offset(offset).limit(limit)

        result = await session.exec(statement)
        return result.all()

    async def get_message_by_id(
        self, message_id: str, session: AsyncSession
    ) -> Optional[Message]:
        """
        Get a specific message by ID
        """
        statement = select(Message).where(Message.id == message_id)
        result = await session.exec(statement)
        return result.first()

    async def create_message(
        self, recipient_profile_id: str, message_data: dict, session: AsyncSession
    ) -> Message:
        """
        Create a new message

        FLOW:
        1. Someone fills "Contact me" form on user's profile
        2. Message saved to recipient's inbox
        3. Recipient gets notification of new message
        """
        new_message = Message(recipient_id=recipient_profile_id, **message_data)

        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)
        return new_message

    async def mark_as_read(self, message: Message, session: AsyncSession) -> Message:
        """
        Mark a message as read

        WHY?
        - Track which messages user has seen
        - Show unread count in UI
        - Different styling for read/unread
        """
        message.is_read = True
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message
    
    async def mark_as_unread(self, message: Message, session: AsyncSession) -> Message:
        """
        Mark a message as unread
        """
        message.is_read = False
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    async def get_unread_count(self, profile_id: str, session: AsyncSession) -> int:
        """
        Count unread messages for a user
        - Used for badge showing "You have 3 unread messages"
        """
        from sqlmodel import func

        statement = select(func.count(Message.id)).where(
            Message.recipient_id == profile_id, Message.is_read == False
        )
        result = await session.exec(statement)
        count = result.first()
        return count or 0

    async def delete_message(self, message: Message, session: AsyncSession) -> None:
        """
        Delete a message
        """
        await session.delete(message)
        await session.commit()
