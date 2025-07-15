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
    SEPARATOR = '___'

    @staticmethod
    def join_tool_name(server_name: str, tool_name: str) -> str:
        """拼接 server_name 和 tool_name"""
        return f"{server_name}{ToolManager.SEPARATOR}{tool_name}"

    @staticmethod
    def split_tool_name(full_tool_name: str) -> tuple[str, str]:
        """拆分 server_name 和 tool_name"""
        parts = full_tool_name.split(ToolManager.SEPARATOR, 1)
        if len(parts) != 2:
            raise ValueError(f"工具名格式错误: {full_tool_name}")
        return parts[0], parts[1]
    
    def __init__(self):
        self._tool_implementations: List[ToolBase] = []
        self.register_mcp()
        
    
    def register_mcp(self):
        """注册mcp工具"""
        # 读取根目录下的 mcp_config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'mcp_config.json')
        print(config_path)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            mcp_servers = config.get('mcpServers', {})
            for server_name, server_info in mcp_servers.items():
                url = server_info.get('url')
                if url:
                    mcp_client = McpClient(server_name, url)
                    self.register_tool(mcp_client)
            logger.info(f"注册mcp: {mcp_servers}")
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
            impl_tools = await tool_impl.get_tools()
            for server_name, tools in impl_tools.items():
                for tool in tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": self.join_tool_name(server_name, tool['tool_name']),
                            "description": tool['description'],
                            "parameters": tool.get('parameters', {})
                        }
                    })
        return openai_tools
    
    async def call_tool(self, full_tool_name: str, tool_args: dict) -> str:
        """
        调用指定工具
        :param full_tool_name: 格式为 "server_name___tool_name"
        :param tool_args: 工具参数
        """
        server_name, tool_name = self.split_tool_name(full_tool_name)
        for tool_impl in self._tool_implementations:
            tools = await tool_impl.get_tools()
            if server_name in tools:
                for tool in tools[server_name]:
                    if tool['tool_name'] == tool_name:
                        return await tool_impl.call_tool(
                            server_name=server_name,
                            tool_name=tool_name,
                            tool_args=tool_args
                        )
        raise ValueError(f"Tool {full_tool_name} not found")