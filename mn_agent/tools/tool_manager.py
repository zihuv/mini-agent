from typing import List, Dict, Any, Type
from dataclasses import asdict

from mn_agent.tools.base import ToolBase

class ToolManager:
    """管理所有工具实现类，并提供统一的工具访问接口"""
    
    def __init__(self):
        self._tool_implementations: List[ToolBase] = []
    
    def register_tool(self, tool_impl: ToolBase):
        """注册一个工具实现类"""
        self._tool_implementations.append(tool_impl)
    
    async def initialize_all(self):
        """初始化所有注册的工具"""
        for tool in self._tool_implementations:
            await tool.connect()
    
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
                            "name": f"{server_name}.{tool['tool_name']}",
                            "description": tool['description'],
                            "parameters": tool['parameters']
                        }
                    })
        return openai_tools
    
    async def call_tool(self, full_tool_name: str, tool_args: dict) -> str:
        """
        调用指定工具
        :param full_tool_name: 格式为 "server_name.tool_name"
        :param tool_args: 工具参数
        """
        server_name, tool_name = full_tool_name.split('.', 1)
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