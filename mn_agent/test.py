"""
增强版LLM Agent实现
包含真实LLM集成、更好的错误处理和扩展功能
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import openai
from openai import OpenAI


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """增强的消息数据结构"""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str = ''
    tool_calls: List[Dict] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'role': self.role,
            'content': self.content
        }
        if self.tool_calls:
            result['tool_calls'] = self.tool_calls
        if self.tool_call_id:
            result['tool_call_id'] = self.tool_call_id
        if self.name:
            result['name'] = self.name
        return result


@dataclass
class Tool:
    """增强的工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为OpenAI工具格式"""
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.parameters
            }
        }
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具调用"""
        pass


@dataclass
class Runtime:
    """增强的运行时状态"""
    should_stop: bool = False
    round: int = 0
    tag: str = 'default'
    error_count: int = 0
    max_errors: int = 3
    
    def reset(self):
        """重置运行时状态"""
        self.should_stop = False
        self.round = 0
        self.error_count = 0


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


class ToolManager:
    """增强的工具管理器"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name}")
    
    def get_tools(self) -> List[Tool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict] = None) -> str:
        """调用单个工具"""
        if tool_name not in self.tools:
            return f"工具 {tool_name} 未找到"
        
        try:
            args = arguments or {}
            result = await self.tools[tool_name].execute(**args)
            logger.info(f"工具 {tool_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return f"工具执行错误: {str(e)}"
    
    async def parallel_call_tools(self, tool_calls: List[Dict]) -> List[str]:
        """并行调用多个工具"""
        tasks = []
        for tool_call in tool_calls:
            # 解析参数
            if isinstance(tool_call.get('function', {}).get('arguments'), str):
                args = json.loads(tool_call['function']['arguments'])
            else:
                args = tool_call.get('function', {}).get('arguments', {})
            
            # 创建异步任务
            task = self.call_tool(
                tool_call['function']['name'], 
                args
            )
            tasks.append(task)
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(f"工具执行异常: {str(result)}")
            else:
                processed_results.append(result)
        
        return processed_results


class EnhancedAgent:
    """增强版Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.runtime = Runtime()
        self.max_rounds = config.get('max_rounds', 10)
        
        # 初始化LLM
        self.llm = self._init_llm()
        
        # 初始化工具管理器
        self.tool_manager = ToolManager()
        
        # 注册工具
        self._register_tools()
        
        logger.info(f"Agent初始化完成，模型: {self.config.get('model', 'unknown')}")
    
    def _init_llm(self) -> OpenAILLM:
        """初始化LLM"""
        api_key = self.config.get('openai_api_key')
        if not api_key:
            raise ValueError("OpenAI API key未配置")
        
        model = self.config.get('model', 'gpt-3.5-turbo')
        base_url = self.config.get('base_url', None)
        
        return OpenAILLM(api_key, model, base_url)
    
    def _register_tools(self):
        """注册工具"""
        # 这里可以注册默认工具或从配置加载
        pass
    
    def _prepare_messages(self, inputs: Union[str, List[Message]]) -> List[Message]:
        """准备消息列表"""
        if isinstance(inputs, str):
            system_prompt = self.config.get('system_prompt', '你是一个有用的助手。')
            return [
                Message(role='system', content=system_prompt),
                Message(role='user', content=inputs)
            ]
        return inputs
    
    async def _step(self, messages: List[Message]) -> List[Message]:
        """执行单步对话"""
        try:
            # 获取可用工具
            tools = self.tool_manager.get_tools()
            
            # 生成LLM响应
            response = self.llm.generate(messages, tools)
            messages.append(response)
            
            # 处理工具调用
            if response.tool_calls:
                logger.info(f"检测到工具调用: {len(response.tool_calls)}个")
                tool_results = await self.tool_manager.parallel_call_tools(response.tool_calls)
                
                # 添加工具响应
                for i, (tool_call, result) in enumerate(zip(response.tool_calls, tool_results)):
                    tool_message = Message(
                        role='tool',
                        content=result,
                        tool_call_id=tool_call['id'],
                        name=tool_call['function']['name']
                    )
                    messages.append(tool_message)
            else:
                # 没有工具调用，停止对话
                self.runtime.should_stop = True
            
            return messages
            
        except Exception as e:
            logger.error(f"步骤执行失败: {e}")
            self.runtime.error_count += 1
            
            # 添加错误消息
            error_message = Message(
                role='assistant',
                content=f"执行过程中遇到错误: {str(e)}"
            )
            messages.append(error_message)
            
            # 检查是否超过最大错误次数
            if self.runtime.error_count >= self.runtime.max_errors:
                self.runtime.should_stop = True
            
            return messages
    
    async def run(self, inputs: Union[str, List[Message]]) -> List[Message]:
        """运行Agent"""
        try:
            # 重置运行时状态
            self.runtime.reset()
            
            # 准备消息
            messages = self._prepare_messages(inputs)
            
            # 显示初始消息
            for msg in messages:
                if msg.role != 'system':
                    logger.info(f"[{msg.role}]: {msg.content}")
            
            # 主循环
            while not self.runtime.should_stop and self.runtime.round < self.max_rounds:
                messages = await self._step(messages)
                self.runtime.round += 1
                
                # 显示最新响应
                if messages[-1].content:
                    logger.info(f"[assistant]: {messages[-1].content}")
            
            # 检查是否超时
            if self.runtime.round >= self.max_rounds and not self.runtime.should_stop:
                timeout_message = Message(
                    role='assistant',
                    content=f'任务超时，已达到最大轮次 {self.max_rounds}'
                )
                messages.append(timeout_message)
                logger.warning(f"任务超时，轮次: {self.runtime.round}")
            
            logger.info(f"Agent运行完成，总轮次: {self.runtime.round}")
            return messages
            
        except Exception as e:
            logger.error(f"Agent运行出错: {e}")
            raise


# 示例工具实现
class SearchTool(Tool):
    """搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="搜索网络信息",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"}
                },
                "required": ["query"]
            }
        )
    
    async def execute(self, **kwargs) -> str:
        query = kwargs.get('query', '')
        # 这里应该实现实际的搜索逻辑
        return f"搜索结果: {query}"


class CalculatorTool(Tool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        )
    
    async def execute(self, **kwargs) -> str:
        expression = kwargs.get('expression', '')
        try:
            # 注意：实际使用时应该使用安全的eval替代方案
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"


class WeatherTool(Tool):
    """天气工具"""
    
    def __init__(self):
        super().__init__(
            name="get_weather",
            description="获取指定城市的天气信息",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        )
    
    async def execute(self, **kwargs) -> str:
        city = kwargs.get('city', '')
        # 模拟天气API调用
        return f"{city}的天气: 晴天，温度25°C"


# 使用示例
async def main():
    """使用示例"""
    # 配置
    config = {
        'model': 'deepseek-chat',
        'system_prompt': '你是一个智能助手，可以使用工具来帮助用户。请根据用户需求选择合适的工具。',
        'max_rounds': 5,
        'openai_api_key': 'sk-7e5750392b114a90a700398a7d1ff416',  # 替换为你的API密钥
        'base_url': 'https://api.deepseek.com/v1'  # 可选，自定义API地址
    }
    
    # 创建Agent
    agent = EnhancedAgent(config)
    
    # 注册工具
    agent.tool_manager.register_tool(SearchTool())
    agent.tool_manager.register_tool(CalculatorTool())
    agent.tool_manager.register_tool(WeatherTool())
    
    # 运行Agent
    queries = [
        "请帮我计算 2 + 3 * 4",
        "北京今天天气怎么样？",
        "搜索一下Python编程"
    ]
    
    for query in queries:
        print(f"\n=== 处理查询: {query} ===")
        messages = await agent.run(query)
        
        print("\n=== 完整对话历史 ===")
        for msg in messages:
            if msg.role != 'system':
                print(f"[{msg.role}]: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main()) 