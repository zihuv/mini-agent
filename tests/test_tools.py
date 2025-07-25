from mini_agent.tools.tool_manager import ToolManager
from mini_agent.tools.filesystem_tool import FileSystemTool
import asyncio
from mini_agent.agent.agent import Agent
import dotenv
import os
dotenv.load_dotenv()
from mini_agent.config.agent_config import AgentConfig


config = {
    "model": os.getenv("MODEL"),
    "openai_api_key": os.getenv("SECRET_KEY"),
    "base_url": os.getenv("BASE_URL")
}



async def test_agent():
    agent = Agent(AgentConfig.from_dict(config))
    tools = await agent.tool_manager.list_tools()
    print(tools)
    result = await agent.run("帮我查下北京的天气如何？")
    print(result)


async def test_tool():
    # 1. 初始化工具管理器
    tool_manager = ToolManager()
    
    # 2. 注册各种工具
    tool_manager.register_tool(FileSystemTool())
    # tool_manager.register_tool(OtherTool1())
    # tool_manager.register_tool(OtherTool2())
    
    try:
        # 4. 获取所有工具定义(OpenAI格式)
        openai_tools = await tool_manager.list_tools()
        print(openai_tools)
        
        # 5. 调用工具示例
        # result = await tool_manager.call_tool(
        #     tool_name="list_files",
        #     tool_args={"directory": "./"}
        # )
        result = await tool_manager.call_tool(
            tool_name="maps_weather",
            tool_args={"city": "北京"}
        )
        print(result)
        
    finally:
        # 6. 清理所有工具
        await tool_manager.cleanup_all()


asyncio.run(test_tool())