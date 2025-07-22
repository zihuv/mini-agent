import logging
from typing import Any, Dict, List, Union
from mn_agent.llm.llm import OpenAILLM
from mn_agent.tools.tool_manager import ToolManager
from mn_agent.llm.utils import Message
import json
from mn_agent.config.agent_config import AgentConfig
import sys
from mn_agent.rag.text_chunker import TextFileChunker
from mn_agent.rag.embed import VectorDB
from mn_agent.rag.rag_engine import rag_answer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    """LLM+工具+记忆+规划"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.max_rounds = config.max_rounds
        self.max_errors = config.max_errors
        self.should_stop = False
        self.round = 0
        self.error_count = 0
        self.document_path = config.document_path
        # 初始化LLM
        self.llm = self._init_llm()
        # 初始化工具管理器
        self.tool_manager = ToolManager()
        logger.info(f"Agent初始化完成，模型: {self.config.model}")

    def _init_llm(self) -> OpenAILLM:
        """初始化LLM"""
        api_key = self.config.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key未配置")
        model = self.config.model
        base_url = self.config.base_url
        return OpenAILLM(api_key, model, base_url)

    def _prepare_messages(self, inputs: Union[str, List[Message]]) -> List[Message]:
        """准备消息列表"""
        if isinstance(inputs, str):
            system_prompt = self.config.system_prompt
            return [
                Message(role="system", content=system_prompt),
                Message(role="user", content=inputs),
            ]
        return inputs

    async def _step(self, messages: List[Message]) -> List[Message]:
        """执行单步对话"""
        try:
            # 获取可用工具
            tools = await self.tool_manager.list_tools()
            # 生成LLM响应
            response = self.llm.generate(messages, tools)
            messages.append(response)
            # 处理工具调用
            if getattr(response, 'tool_calls', None):
                logger.info(f"检测到工具调用: {len(response.tool_calls)}个")
                import asyncio
                async def call_tool(tool_call):
                    arguments = tool_call.arguments
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    return await self.tool_manager.call_tool(tool_call.tool_name, arguments)

                tool_results = await asyncio.gather(*[
                    call_tool(tool_call) for tool_call in response.tool_calls
                ])

                for tool_call, result in zip(response.tool_calls, tool_results):
                    tool_message = Message(
                        role="tool",
                        content=result,
                        tool_call_id=getattr(tool_call, 'id', None),
                        name=getattr(tool_call, 'tool_name', None),
                    )
                    messages.append(tool_message)
            else:
                # 没有工具调用，停止对话
                self.should_stop = True
            return messages
        except Exception as e:
            logger.error(f"步骤执行失败: {e}")
            self.error_count += 1
            # 添加错误消息
            error_message = Message(
                role="assistant", content=f"执行过程中遇到错误: {str(e)}"
            )
            messages.append(error_message)
            # 检查是否超过最大错误次数
            if self.error_count >= self.max_errors:
                self.should_stop = True
            return messages

    async def run(self, inputs: Union[str, List[Message]]) -> List[Message]:
        """运行Agent"""
        try:
            # 重置运行时状态
            self.should_stop = False
            self.round = 0
            self.error_count = 0
            # 如果指定了文档路径，走RAG流程
            if self.document_path:
                question = inputs if isinstance(inputs, str) else (inputs[-1].content if inputs else "")
                response = rag_answer(self.document_path, question, self.config)
                return [Message(role="assistant", content=response)]
            # 否则走原有LLM流程
            # 准备消息
            messages = self._prepare_messages(inputs)
            # 显示初始消息
            for msg in messages:
                if msg.role != "system":
                    logger.info(f"[{msg.role}]: {msg.content}")
            # 主循环
            while not self.should_stop and self.round < self.max_rounds:
                messages = await self._step(messages)
                self.round += 1
                # 显示最新响应
                if messages[-1].content:
                    logger.info(f"[assistant]: {messages[-1].content}")
            # 检查是否超时
            if self.round >= self.max_rounds and not self.should_stop:
                timeout_message = Message(
                    role="assistant",
                    content=f"任务超时，已达到最大轮次 {self.max_rounds}",
                )
                messages.append(timeout_message)
                logger.warning(f"任务超时，轮次: {self.round}")
            logger.info(f"Agent运行完成，总轮次: {self.round}")
            return messages
        except Exception as e:
            logger.error(f"Agent运行出错: {e}")
            raise
