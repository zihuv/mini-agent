from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Agent配置类"""
    
    # OpenAI配置
    openai_api_key: str
    model: str = "deepseek-chat"
    base_url: Optional[str] = None
    
    # 系统提示词
    system_prompt: str = "你是一个有用的助手。"   
    # 运行参数
    max_rounds: int = 10   
    max_errors: int = 3
    # 文档路径（RAG）
    document_path: Optional[str] = None
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AgentConfig':
        """从字典创建配置对象"""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "openai_api_key": self.openai_api_key,
            "model": self.model,
            "base_url": self.base_url,
            "system_prompt": self.system_prompt,
            "max_rounds": self.max_rounds,
            "max_errors": self.max_errors,
            "document_path": self.document_path,
        }
    
    def validate(self) -> None:
        """验证配置的有效性"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key不能为空")
        if self.max_rounds <= 0:
            raise ValueError("max_rounds必须大于0")
        if self.max_errors <= 0:
            raise ValueError("max_errors必须大于0")
        # document_path 可选，不做强制校验 