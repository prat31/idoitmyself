from typing import List, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.ai_service import ai_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="The message content")


class ChatStreamRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None


@router.post("/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """Stream an AI chat completion from OpenRouter."""
    serialized_messages = [msg.model_dump() for msg in request.messages]
    return StreamingResponse(
        ai_service.stream_chat_completion(serialized_messages, model=request.model),
        media_type="text/event-stream"
    )
