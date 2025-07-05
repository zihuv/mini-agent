from openai import OpenAI
import os
import json
from typing import Generator
from uuid import uuid4
from sqlalchemy.orm import Session
from .models import Message, Conversation

class ChatService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.model = os.getenv("OPENAI_MODEL", "deepseek-chat")

    def get_or_create_conversation(
        self, 
        db: Session, 
        user_id: int, 
        conversation_id: str = None
    ) -> Conversation:
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()
            if conversation:
                return conversation
        
        # 如果找不到现有对话或没有提供 ID，创建新对话
        conversation = Conversation(
            id=str(uuid4()),
            user_id=user_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def generate_response(
        self, 
        prompt: str, 
        user_id: int,
        db: Session,
        conversation_id: str = None
    ) -> Generator[str, None, None]:
        try:
            # 获取或创建对话
            conversation = self.get_or_create_conversation(db, user_id, conversation_id)
            
            # 创建并保存用户消息
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=prompt
            )
            db.add(user_message)
            db.commit()
            
            # 准备发送给 LLM 的消息列表
            messages = [{"role": "system", "content": "You are a helpful assistant"}]
            db_messages = db.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at).all()
            
            messages.extend([{"role": m.role, "content": m.content} for m in db_messages])
            
            # 调用 LLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            # 创建助手消息
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=""
            )
            db.add(assistant_message)
            db.commit()
            
            # 处理流式响应
            for chunk in response:
                if chunk and chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_message.content += content
                    db.commit()
                    yield f"data: {json.dumps({'text': content, 'conversation_id': conversation.id})}\n\n"
            
        except Exception as e:
            error_message = str(e)
            print(f"Error in generate_response: {error_message}")
            yield f"data: {json.dumps({'error': error_message})}\n\n"