from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MessageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)

# For READING messages (receiver's view)
class MessageResponseData(BaseModel):
    """What you see in your inbox"""
    id: str
    name: str              # Sender's name
    email: str             # Sender's email (to reply)
    subject: str
    body: str
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    status: str
    message: str
    data: MessageResponseData
    
# For SENDING messages (sender confirmation)
class MessageSendResponseData(BaseModel):
    """Confirmation after sending"""
    id: str       
    recipient_username: str  # "Sent to johndoe"
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class MessageSendResponse(BaseModel):
    status: str            
    message: str 
    # data: MessageSendResponseData          

class MessageListResponseData(BaseModel):
    id: str
    name: str
    email: str
    subject: str
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class MessageListResponse(BaseModel):
    status: str
    message: str
    data: list[MessageListResponseData]
    
class MessageMarkResponse(BaseModel):
    """Response after marking message as read or unread"""
    status: str
    message: str
    is_read: bool
    
class MessageUnreadCountResponse(BaseModel):
    status: str
    message: str
    unread_count: int