from mn_agent.tools.tool_manager import ToolManager
from mn_agent.tools.filesystem_tool import FileSystemTool
import asyncio

async def main():
    # 1. 初始化工具管理器
    tool_manager = ToolManager()
    
    # 2. 注册各种工具
    tool_manager.register_tool(FileSystemTool())
    # tool_manager.register_tool(OtherTool1())
    # tool_manager.register_tool(OtherTool2())
    
    # 3. 初始化所有工具
    await tool_manager.initialize_all()
    
    try:
        # 4. 获取所有工具定义(OpenAI格式)
        openai_tools = await tool_manager.list_tools()
        print(openai_tools)
        
        # 5. 调用工具示例
        result = await tool_manager.call_tool(
            full_tool_name="file_system.list_files",
            tool_args={"directory": "./"}
        )
        print(result)
        
    finally:
        # 6. 清理所有工具
        await tool_manager.cleanup_all()


asyncio.run(main())