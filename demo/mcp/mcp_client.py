import asyncio
from fastmcp import Client, FastMCP

# HTTP server
client = Client("http://localhost:9000/mcp")

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        
        # Execute operations
        result = await client.call_tool("add", {"a": 1, "b": 2})
        print(result)

asyncio.run(main())