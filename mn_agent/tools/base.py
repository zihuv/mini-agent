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
    async def get_tools(self) -> List[Tool]:
        """获取工具定义"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, tool_args: dict) -> str:
        """调用工具"""
        pass