import sys
import os
import random
import hashlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chat.service import ChatService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from auth.models import User
from chat.models import Conversation, Message

# 创建测试数据库引擎
engine = create_engine('sqlite:///:memory:')
SessionLocal = sessionmaker(bind=engine)

# 初始化数据库
Base.metadata.create_all(engine)

def generate_unique_username():
    """生成唯一的用户名"""
    return f"testuser_{random.randint(1000, 9999)}"

def generate_unique_email():
    """生成唯一的邮箱地址"""
    return f"test_{random.randint(1000, 9999)}@example.com"

@pytest.fixture
def db_session():
    """创建一个带有唯一用户的测试数据库会话"""
    db = SessionLocal()
    try:
        # 生成唯一用户名和邮箱
        username = generate_unique_username()
        email = generate_unique_email()
        
        # 创建测试用户
        user = User(id=2, username=username, email=email)
        db.add(user)
        db.commit()
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_openai_client(mocker):
    # 创建一个mock的OpenAI客户端
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = []
    return mock_client

@pytest.fixture
def chat_service(mock_openai_client):
    # 创建ChatService实例并替换为mock的OpenAI客户端
    return ChatService(client=mock_openai_client)

def test_get_or_create_conversation(chat_service, db_session, unique_user_id):
    # 测试获取或创建对话功能
    conversation = chat_service.get_or_create_conversation(db_session, unique_user_id)
    assert conversation.user_id == unique_user_id
    assert len(conversation.id) > 0

    # 使用提供的对话ID进行测试
    conversation_id = "test-conversation-id"
    conversation = chat_service.get_or_create_conversation(db_session, unique_user_id, conversation_id)
    assert conversation.id == conversation_id
    assert conversation.user_id == unique_user_id

def test_get_user_conversation_history(chat_service, db_session, unique_user_id):
    # 测试获取用户对话历史功能
    conversation = chat_service.get_or_create_conversation(db_session, unique_user_id)
    
    # 添加消息到对话
    message1 = Message(conversation_id=conversation.id, role="user", content="Hello")
    message2 = Message(conversation_id=conversation.id, role="assistant", content="Hi there")
    db_session.add(message1)
    db_session.add(message2)
    db_session.commit()
    
    history = chat_service.get_user_conversation_history(unique_user_id, db_session)
    assert len(history) == 1
    assert history[0]["conversation_id"] == conversation.id
    assert len(history[0]["messages"]) == 2
    assert history[0]["messages"][0]["role"] == "user"
    assert history[0]["messages"][0]["content"] == "Hello"
    assert history[0]["messages"][1]["role"] == "assistant"
    assert history[0]["messages"][1]["content"] == "Hi there"