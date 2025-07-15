from typing import Dict, List
from .base import ToolBase
from mn_agent.llm.utils import Tool
from fastmcp import Client

class McpClient(ToolBase):
    """MCP客户端工具类"""

    def __init__(self, server_name: str, url: str):
        self.server_name = server_name
        self.url = url
        self.client = None

    async def connect(self) -> None:
        self.client = Client(self.url)

    async def cleanup(self) -> None:
        pass

    async def get_tools(self) -> Dict[str, List[Tool]]:
        # 获取mcp工具列表并转换为OpenAI Tool格式
        mcp_tools = []
        if self.client:
            async with self.client:
                mcp_tools = await self.client.list_tools()
        tools = []
        for tool in mcp_tools:
            tools.append({
                'tool_name': tool.name,
                'description': tool.description,
                'parameters': tool.inputSchema
            })
        return {self.server_name: tools}

    async def call_tool(self, server_name: str, *, tool_name: str, tool_args: dict) -> str:
        # 调用指定工具
        if not self.client:
            raise RuntimeError('MCP client not connected')
        async with self.client:
            result = await self.client.call_tool(tool_name, tool_args)
            return str(result)
        