from typing import List, Optional
from mn_agent.llm.utils import Message, Tool


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
            api_tools = None
            if tools:
                api_tools = [tool.to_dict() for tool in tools]
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                tools=api_tools,
                tool_choice="auto" if tools else None
            )
            
            # 解析响应
            choice = response.choices[0]
            message = choice.message
            
            # 构建返回消息
            result = Message(
                role=message.role,
                content=message.content or ''
            )
            
            # 处理工具调用
            if message.tool_calls:
                result.tool_calls = []
                for tool_call in message.tool_calls:
                    result.tool_calls.append({
                        'id': tool_call.id,
                        'type': tool_call.type,
                        'function': {
                            'name': tool_call.function.name,
                            'arguments': tool_call.function.arguments
                        }
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return Message(
                role='assistant',
                content=f"抱歉，我遇到了一个错误: {str(e)}"
            )