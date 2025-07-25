import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from mini_agent.workflow.engine import WorkflowEngine
from mini_agent.workflow.nodes import (
    TriggerManualNode,
    TransformMapNode,   
    ActionAIAgentNode,
    LogicSwitchNode,
    ActionHttpNode,
)
from dotenv import load_dotenv


load_dotenv()


# 注册节点类型
node_registry = {
    "trigger/manual": TriggerManualNode,
    "transform/map": TransformMapNode,
    "action/ai_agent": ActionAIAgentNode,
    "logic/switch": LogicSwitchNode,
    "action/http": ActionHttpNode,
}


def build_ai_switch_http_workflow():
    """构建包含AI Agent决策、动态分支和HTTP调用的工作流"""
    workflow_def = {
        "name": "AI决策与HTTP调用工作流",
        "nodes": [
            {
                "id": "start",
                "type": "trigger/manual",
                "name": "手动触发",
            },
            {
                "id": "ai_decision",
                "type": "action/ai_agent",
                "name": "AI决策",
                "config": {
                    "prompt": "请根据输入内容判断应该走A路径还是B路径，如果是 True，回答 A，如果是 False，回答 B。只回答A或B，不要有其他内容。输入内容：{{test.path}}",
                    "model": "deepseek-chat",
                    "base_url": os.getenv("BASE_URL"),  # 可配置为实际API
                    "openai_api_key": os.getenv("SECRET_KEY"),  # 可配置为实际key
                    "outputMapping": {"decision": "{{aiOutput}}"},
                },
            },
            {
                "id": "switch",
                "type": "logic/switch",
                "name": "分支选择",
                "config": {
                    "expression": "context.get('ai_decision', {}).get('decision', 'A')",
                    "cases": {"A": "http_a", "B": "http_b"},
                    "default": "http_a",
                },
            },
            {
                "id": "http_a",
                "type": "action/http",
                "name": "HTTP接口A",
                "config": {
                    "url": "https://httpbin.org/get?path=A",
                    "method": "GET",
                },
            },
            {
                "id": "http_b",
                "type": "action/http",
                "name": "HTTP接口B",
                "config": {
                    "url": "https://httpbin.org/get?path=B",
                    "method": "GET",
                },
            },
        ],
        "connections": [
            {"from": "start", "to": "ai_decision"},
            {"from": "ai_decision", "to": "switch"},
            {"from": "switch", "to": "http_a"},  # switch节点会根据decision动态选择
            {"from": "switch", "to": "http_b"},
        ],
    }
    return workflow_def


async def test_ai_switch_http_workflow():
    workflow_def = build_ai_switch_http_workflow()
    engine = WorkflowEngine(workflow_def, node_registry)
    result_a = await engine.execute_workflow(
        initial_context={"test": {"path": "A"}}
    )  # 走A
    result_b = await engine.execute_workflow(
        initial_context={"test": {"path": "B"}}
    )  # 走B
    print("AI决策与HTTP调用工作流执行结果:", result_a)
    print("执行摘要:", result_a.get("summary"))
    print("--------------------------------")
    print("AI决策与HTTP调用工作流执行结果:", result_b)
    print("执行摘要:", result_b.get("summary"))


if __name__ == "__main__":
    asyncio.run(test_ai_switch_http_workflow())
