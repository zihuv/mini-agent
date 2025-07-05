from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from .models import ChatRequest
from .service import ChatService
from auth.dependencies import get_current_user
from auth.models import User
from database import get_db

router = APIRouter()
chat_service = ChatService()

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    return StreamingResponse(
        chat_service.generate_response(
            prompt=request.prompt,
            conversation_id=request.conversation_id,
            user_id=current_user.id,
            db=db
        ),
        media_type="text/event-stream"
    )