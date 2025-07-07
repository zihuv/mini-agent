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
    conversation_id: str = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接收上传的文件并将其内容索引到向量数据库中"""
    try:
        # 如果未提供 conversation_id，自动创建新会话
        if not conversation_id:
            conversation = chat_service.get_or_create_conversation(db, user.id)
            conversation_id = conversation.id
        else:
            # 验证会话归属
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        # 验证文件类型
        allowed_types = ['.txt', '.doc', '.docx', '.pdf']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
            )

        # 读取文件内容
        try:
            content = await file.read()
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be a valid text file"
            )

        # 索引文档内容
        success = chat_service.index_document(
            content=text_content,
            conversation_id=conversation_id
        )
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to index document"
            )
        
        return {
            "status": "success",
            "message": f"Document {file.filename} indexed successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@router.post("/message")
async def send_message(
    request: dict, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """处理用户发送的消息"""
    if 'message' not in request:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        response = chat_service.generate_response(
            prompt=request['message'],
            user_id=user.id,
            db=db,
            conversation_id=request.get('conversation_id')
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

@router.get("/conversation/{conversation_id}/documents")
async def get_conversation_documents(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定会话的所有文档"""
    # 验证会话归属
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 获取文档列表
    docs = chat_service.retrieve_documents("", conversation_id)
    return {"documents": [{"id": i, "content": doc} for i, doc in enumerate(docs)]}
