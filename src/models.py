from typing import Optional
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    """Request model for sending messages"""
    text: Optional[str] = None
    
    class Config:
        str_strip_whitespace = True


class ApiKeyResponse(BaseModel):
    """Response model for API key operations"""
    user_id: str
    apikey: str
    created_at: str
