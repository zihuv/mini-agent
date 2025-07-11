import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import os
import json
from typing import Generator, List, Dict, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
import faiss
from sentence_transformers import SentenceTransformer
import torch

from .models import Message, Conversation


class VectorDB:
    """
    使用 FAISS 实现的向量数据库，支持会话隔离
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.indices: Dict[str, faiss.Index] = {}  # 每个会话一个向量索引
        self.documents: Dict[str, Dict[int, str]] = {}  # 每个会话的文档存储
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def _get_or_create_index(self, conversation_id: str):
        """获取或创建会话的向量索引"""
        if conversation_id not in self.indices:
            self.indices[conversation_id] = faiss.IndexFlatL2(self.dimension)
            self.documents[conversation_id] = {}
        return self.indices[conversation_id]
    
    def store_vector(self, document: str, conversation_id: str) -> int:
        """存储向量及其对应的文档内容到指定会话"""
        vector = self.model.encode([document])[0]
        vector = vector.reshape(1, -1).astype('float32')
        
        index = self._get_or_create_index(conversation_id)
        index.add(vector)
        doc_id = index.ntotal - 1
        self.documents[conversation_id][doc_id] = document
        return doc_id
    
    def search(self, query: str, conversation_id: str, k: int = 5) -> List[str]:
        """在指定会话中搜索最相似的文档"""
        if conversation_id not in self.indices:
            return []
            
        query_vector = self.model.encode([query])[0]
        query_vector = query_vector.reshape(1, -1).astype('float32')
        
        index = self.indices[conversation_id]
        distances, indices = index.search(query_vector, k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and idx in self.documents[conversation_id]:
                results.append(self.documents[conversation_id][idx])
        return results

    def clear_conversation(self, conversation_id: str):
        """清除指定会话的所有文档"""
        if conversation_id in self.indices:
            del self.indices[conversation_id]
            del self.documents[conversation_id]


class ChatService:
    _vector_db = None  # 单例模式存储VectorDB实例

    def __init__(self, client=None):
        # 如果未提供客户端，则使用环境变量初始化OpenAI客户端
        if client is None:
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
        else:
            self.client = client
        self.model = os.getenv("OPENAI_MODEL", "deepseek-chat")
        if ChatService._vector_db is None:
            ChatService._vector_db = VectorDB()
        self.tools = {}  # 工具名称 -> 函数实现
        self.tool_specs = []  # OpenAI 格式的工具描述

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

    def get_user_conversation_history(self, user_id: int, db: Session):
        # 获取用户的所有对话记录
        conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
        
        # 将对话记录转换为更易读的格式
        history = []
        for conversation in conversations:
            messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at).all()
            history.append({
                "conversation_id": conversation.id,
                "created_at": conversation.created_at,
                "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]
            })
        
        return history

    def register_tool(self, tool_name, description, parameters, tool_function):
        """
        注册工具到 ChatService
        :param tool_name: 工具名称 (e.g. "get_weather")
        :param description: 工具描述
        :param parameters: 参数规范 (OpenAI 格式)
        :param tool_function: 实际执行的函数
        """
        self.tools[tool_name] = tool_function
        self.tool_specs.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": parameters
            }
        })
    
    def execute_tool(self, tool_name, arguments):
        """执行工具并处理错误"""
        try:
            # 尝试解析 JSON 参数
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
                
            # 检查工具是否存在
            if tool_name not in self.tools:
                return f"错误: 未知工具 '{tool_name}'"
                
            # 执行工具
            return self.tools[tool_name](**arguments)
            
        except json.JSONDecodeError:
            # 处理非 JSON 格式参数
            try:
                # 尝试从字符串中提取参数
                params = {}
                for param in self.get_required_params(tool_name):
                    # 简单模式匹配提取参数值
                    match = re.search(fr'{param}[:=]\s*([^,}}]+)', arguments)
                    if match:
                        params[param] = match.group(1).strip('"\' ')
                
                return self.tools[tool_name](**params)
            except Exception as e:
                return f"参数解析错误: {str(e)}"
                
        except Exception as e:
            return f"工具执行错误: {str(e)}"
    
    def get_required_params(self, tool_name):
        """获取工具的必需参数列表"""
        for spec in self.tool_specs:
            if spec["function"]["name"] == tool_name:
                return spec["function"]["parameters"].get("required", [])
        return []

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
            
            # 检索相关文档
            retrieved_docs = []
            if conversation_id:  # 如果是现有会话，从会话相关的文档中检索
                retrieved_docs = self._vector_db.search(prompt, conversation.id)
            
            # 创建并保存用户消息
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=prompt
            )
            db.add(user_message)
            db.commit()
            
            # 准备发送给 LLM 的消息列表
            system_message = "You are a helpful assistant. "
            if retrieved_docs:
                system_message += "Here are some relevant documents that might help answer the question:\n\n"
                for i, doc in enumerate(retrieved_docs, 1):
                    system_message += f"Document {i}:\n{doc}\n\n"
                system_message += "Please use this information to provide a detailed and accurate response."
            
            messages = [{"role": "system", "content": system_message}]
            db_messages = db.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at).all()
            
            messages.extend([{"role": m.role, "content": m.content} for m in db_messages])
            
            # 调用 LLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_specs if self.tool_specs else None,
                tool_choice="auto" if self.tool_specs else None,
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
                if chunk and chunk.choices:
                    # 检查是否调用了工具
                    if chunk.choices[0].delta.tool_calls:
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            tool_name = tool_call.function.name
                            arguments = tool_call.function.arguments
                            
                            # 执行工具
                            tool_result = self.execute_tool(tool_name, arguments)
                            
                            # 添加工具结果到消息历史
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": str(tool_result)
                            })
                            
                            # 重新调用 LLM 处理工具结果
                            response = self.client.chat.completions.create(
                                model=self.model,
                                messages=messages,
                                tools=self.tool_specs if self.tool_specs else None,
                                tool_choice="auto" if self.tool_specs else None,
                                stream=True
                            )
                            
                            # 更新助手消息
                            for chunk in response:
                                if chunk and chunk.choices and chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    assistant_message.content += content
                                    db.commit()
                                    yield f"data: {json.dumps({'text': content, 'conversation_id': conversation.id})}\n\n"
                    elif chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        assistant_message.content += content
                        db.commit()
                        yield f"data: {json.dumps({'text': content, 'conversation_id': conversation.id})}\n\n"
            
        except Exception as e:
            error_message = str(e)
            print(f"Error in generate_response: {error_message}")
            yield f"data: {json.dumps({'error': error_message})}\n\n"

    def index_document(self, content: str, conversation_id: str) -> bool:
        """将文档内容转换为向量并存储在指定会话的向量数据库中"""
        try:
            # 限制文档长度以避免内存问题
            max_length = 10000
            if len(content) > max_length:
                content = content[:max_length]
                print(f"Warning: Document content truncated to {max_length} characters")
            
            self._vector_db.store_vector(content, conversation_id)
            return True
        except Exception as e:
            print(f"Error indexing document: {str(e)}")
            return False

    def retrieve_documents(self, query: str, conversation_id: str, top_k: int = 5) -> List[str]:
        """从指定会话中搜索与查询最相关的文档"""
        try:
            # 限制查询长度以避免性能问题
            max_query_length = 1000
            if len(query) > max_query_length:
                query = query[:max_query_length]
                print(f"Warning: Query truncated to {max_query_length} characters")
            
            return self._vector_db.search(query, conversation_id, top_k)
        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
            return []

    def clear_conversation_documents(self, conversation_id: str):
        """清除指定会话的所有文档"""
        try:
            self._vector_db.clear_conversation(conversation_id)
            return True
        except Exception as e:
            print(f"Error clearing conversation documents: {str(e)}")
            return False
