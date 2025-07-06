from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from chat.service import ChatService
from auth.dependencies import get_current_user
from chat.models import ChatRequest, Conversation
from auth.models import User
from database import get_db
import os

router = APIRouter()
chat_service = ChatService()

@router.post("/index")
async def index_document(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    接收上传的文件并将其内容索引到向量数据库中。
    文件内容会与特定的会话关联。
    """
    try:
        # 验证会话归属
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        content = await file.read()
        success = chat_service.index_document(
            content=content.decode('utf-8'),
            conversation_id=conversation_id
        )
        if not success:
            raise HTTPException(status_code=500, detail="Document indexing failed")
        
        return {
            "status": "success",
            "message": f"Document {file.filename} indexed successfully for conversation {conversation_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message")
async def send_message(
    request: dict, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    处理用户发送的消息，使用会话相关的文档进行回答。
    """
    if 'message' not in request or 'conversation_id' not in request:
        raise HTTPException(status_code=400, detail="Message and conversation_id are required.")

    conversation_id = request['conversation_id']
    # 验证会话归属
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        response = chat_service.generate_response(
            prompt=request['message'],
            user_id=user.id,
            db=db,
            conversation_id=conversation_id
        )
        return StreamingResponse(response, media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.delete("/conversation/{conversation_id}/documents")
async def clear_conversation_documents(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    清除指定会话的所有文档
    """
    # 验证会话归属
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    success = chat_service.clear_conversation_documents(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear conversation documents")
    
    return {"status": "success", "message": "Conversation documents cleared successfully"}

@router.get("/history")
async def get_user_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = chat_service.get_user_conversation_history(user_id=current_user.id, db=db)
    return {"history": history}
