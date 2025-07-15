import asyncio
from fastmcp import Client, FastMCP

# HTTP server
client = Client("https://mcp.api-inference.modelscope.net/8d5e6040aeb344/sse")

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
                
        # List available operations
        # tools = await client.list_tools()
        # print(tools)
       
       
        print(await client.call_tool("maps_weather", {"city": "北京"}))


        # Execute operations
        # result = await client.call_tool("example_tool", {"param": "value"})
        # print(result)

asyncio.run(main())