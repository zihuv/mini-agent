import asyncio
from .parser import load_workflow_from_file
from .engine import WorkflowEngine
from .nodes import NODE_REGISTRY
from .visualizer import visualize_workflow
import os

def main():
    workflow_path = os.path.join(os.path.dirname(__file__), 'example_workflow.json')
    workflow = load_workflow_from_file(workflow_path)
    engine = WorkflowEngine(workflow, NODE_REGISTRY)
    print('开始执行工作流...')
    asyncio.run(engine.execute())
    print('执行完成，生成流程图...')
    visualize_workflow(workflow, output_path=os.path.join(os.path.dirname(__file__), 'workflow'))
    print('流程图已生成。')

if __name__ == '__main__':
    main()
