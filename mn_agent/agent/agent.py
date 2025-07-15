import logging

from typing import Any, Dict, List,  Union

from openai import OpenAI
from mn_agent.agent.runtime import Runtime
from mn_agent.llm.openai import OpenAILLM
from mn_agent.tools.tool_manager import ToolManager
from mn_agent.utils.base import ToolBase
from mn_agent.llm.utils import Message

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent:
    """LLM+工具+记忆+规划"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.runtime = Runtime()
        self.max_rounds = config.get("max_rounds", 10)

        # 初始化LLM
        self.llm = self._init_llm()

        # 初始化工具管理器
        self.tool_manager = ToolManager()

        # 注册工具
        self._register_tools()

        logger.info(f"Agent初始化完成，模型: {self.config.get('model', 'unknown')}")

    def _init_llm(self) -> OpenAILLM:
        """初始化LLM"""
        api_key = self.config.get("openai_api_key")
        if not api_key:
            raise ValueError("OpenAI API key未配置")

        model = self.config.get("model", "gpt-3.5-turbo")
        base_url = self.config.get("base_url", None)

        return OpenAILLM(api_key, model, base_url)

    def _register_tools(self):
        """注册工具"""
        # 这里可以注册默认工具或从配置加载
        pass

    def _prepare_messages(self, inputs: Union[str, List[Message]]) -> List[Message]:
        """准备消息列表"""
        if isinstance(inputs, str):
            system_prompt = self.config.get("system_prompt", "你是一个有用的助手。")
            return [
                Message(role="system", content=system_prompt),
                Message(role="user", content=inputs),
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
                tool_results = await self.tool_manager.parallel_call_tools(
                    response.tool_calls
                )

                # 添加工具响应
                for i, (tool_call, result) in enumerate(
                    zip(response.tool_calls, tool_results)
                ):
                    tool_message = Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_call["id"],
                        name=tool_call["function"]["name"],
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
                role="assistant", content=f"执行过程中遇到错误: {str(e)}"
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
                if msg.role != "system":
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
                    role="assistant",
                    content=f"任务超时，已达到最大轮次 {self.max_rounds}",
                )
                messages.append(timeout_message)
                logger.warning(f"任务超时，轮次: {self.runtime.round}")

            logger.info(f"Agent运行完成，总轮次: {self.runtime.round}")
            return messages

        except Exception as e:
            logger.error(f"Agent运行出错: {e}")
            raise
