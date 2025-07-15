from abc import ABC, abstractmethod
from typing import Dict, List, Any
from mn_agent.llm.utils import Tool

class ToolBase(ABC):
    """工具基类"""
    
    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass
    
    @abstractmethod
    async def get_tools(self) -> Dict[str, List[Tool]]:
        """获取工具定义"""
        pass
    
    @abstractmethod
    async def call_tool(self, server_name: str, *, tool_name: str, tool_args: dict) -> str:
        """调用工具"""
        pass