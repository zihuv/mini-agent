from typing import List, Optional

from pydantic.type_adapter import P
from mn_agent.llm.utils import Message, Tool
from openai import OpenAI
import logging
from mn_agent.llm.utils import ToolCall

logger = logging.getLogger(__name__)

class OpenAILLM:
    """OpenAI LLM实现"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", base_url: Optional[str] = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def generate(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> Message:
        """调用OpenAI API"""
        try:
            # 准备消息
            api_messages = [msg.to_dict() for msg in messages]
            
            # 准备工具
            api_tools = tools if tools else None
            
            # 构建参数
            params = {
                "model": self.model,
                "messages": api_messages,
            }
            if api_tools:
                params["tools"] = api_tools
                params["tool_choice"] = "auto"
            
            # 调用API
            response = self.client.chat.completions.create(**params)
            
            # 解析响应
            message = response.choices[0].message
            
            # 构建返回消息
            result = Message(
                role=message.role,
                content=message.content or ''
            )
            
            # 处理工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                result.tool_calls = []
                for tool_call in message.tool_calls:
                    # 转换成 ToolCall 对象
                    tool_data = ToolCall(
                        id=getattr(tool_call, 'id', None),
                        type=getattr(tool_call, 'type', None),
                        tool_name=getattr(tool_call.function, 'name', None) if hasattr(tool_call, 'function') else None,
                        arguments=getattr(tool_call.function, 'arguments', None) if hasattr(tool_call, 'function') else None,
                    )
                    print("tool_data", tool_data)
                    result.tool_calls.append(tool_data)
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return Message(
                role='assistant',
                content=f"抱歉，我遇到了一个错误: {str(e)}"
            )