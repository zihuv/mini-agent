import asyncio
import json
import os
from mn_agent.workflow.parser import load_workflow_from_file
from mn_agent.workflow.engine import WorkflowEngine
from mn_agent.workflow.nodes import NODE_REGISTRY

async def test_article_summary_workflow():
    """测试文章概括工作流"""
    
    # 加载工作流配置
    workflow_path = os.path.join(os.path.dirname(__file__), 'article_summary_workflow.json')
    workflow_def = load_workflow_from_file(workflow_path)
    
    # 创建初始上下文数据
    initial_context = {
        "input": {
            "url": "https://httpbin.org/json"  # 使用测试API获取JSON数据
        }
    }
    
    print("=== 文章概括工作流测试 ===")
    print(f"初始URL: {initial_context['input']['url']}")
    print("开始执行工作流...")
    
    try:
        # 创建并执行工作流引擎
        engine = WorkflowEngine(workflow_def, NODE_REGISTRY)
        result = await engine.execute(initial_context)
        
        print("\n=== 工作流执行结果 ===")
        print(f"执行摘要: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 获取上下文摘要
        context_summary = engine.context.get_execution_summary()
        print(f"\n=== 执行摘要 ===")
        print(f"开始时间: {context_summary['start_time']}")
        print(f"结束时间: {context_summary['end_time']}")
        print(f"总更新次数: {context_summary['total_updates']}")
        print(f"错误数量: {context_summary['total_errors']}")
        
        if context_summary['total_errors'] > 0:
            print(f"\n=== 错误信息 ===")
            for error in engine.context.errors:
                print(f"节点: {error['node_id']}")
                print(f"错误: {error['error']}")
                print(f"时间: {error['timestamp']}")
        
        return result
        
    except Exception as e:
        print(f"工作流执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_article_summary_workflow()) 