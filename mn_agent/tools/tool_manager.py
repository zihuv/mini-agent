from typing import List, Dict, Any, Type

from mn_agent.tools.base import ToolBase
from mn_agent.tools.mcp_client import McpClient
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ToolManager:
    """管理所有工具实现类，并提供统一的工具访问接口"""

    def __init__(self):
        self._tool_implementations: List[ToolBase] = []
        self.register_mcp()

    def register_mcp(self):
        """注册mcp工具"""
        # 读取根目录下的 mcp_config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'mcp_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(config)
                if config:
                    mcp_client = McpClient(config)
                    self.register_tool(mcp_client)
            logger.info(f"注册mcp: {config}")
        else:
            logger.warning(f"mcp_config.json 文件不存在: {config_path}")

    def register_tool(self, tool_impl: ToolBase):
        """注册一个工具实现类"""
        self._tool_implementations.append(tool_impl)

    async def cleanup_all(self):
        """清理所有注册的工具"""
        for tool in self._tool_implementations:
            await tool.cleanup()

    async def list_tools(self):
        """获取所有工具的定义，转换为OpenAI格式"""
        openai_tools = []
        for tool_impl in self._tool_implementations:
            tools = await tool_impl.get_tools()
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool['tool_name'],
                        "description": tool['description'],
                        "parameters": tool.get('parameters', {})
                    }
                })
        return openai_tools

    async def call_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        调用指定工具
        :param tool_name: 工具名
        :param tool_args: 工具参数
        """
        for tool_impl in self._tool_implementations:
            tools = await tool_impl.get_tools()
            for tool in tools:
                if tool['tool_name'] == tool_name:
                    return await tool_impl.call_tool(tool_name=tool_name, tool_args=tool_args)
        raise ValueError(f"Tool {tool_name} not found")