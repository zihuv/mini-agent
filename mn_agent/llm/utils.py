# Copyright (c) Alibaba, Inc. and its affiliates.
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from typing_extensions import Literal, Required, TypedDict


class ToolCall:
    def __init__(self, id, type, tool_name, arguments):
        self.id = id
        self.type = type
        self.tool_name = tool_name
        self.arguments = arguments

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.tool_name, "arguments": self.arguments},
        }


class Tool(TypedDict, total=False):
    tool_name: Required[str]
    description: Required[str]
    parameters: Dict[str, Any]


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]

    content: str = ""

    tool_calls: List[ToolCall] = field(default_factory=list)

    tool_call_id: Optional[str] = None

    name: Optional[str] = None


    def to_dict(self):
        d = asdict(self)
        # 修复tool_calls的序列化
        d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        return d
