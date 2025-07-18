import asyncio
from fastmcp import Client, FastMCP


config = {
  "mcpServers": {
    "amap-maps": {
      "type": "sse",
      "url": "https://mcp.api-inference.modelscope.net/1a8578e121ae4e/sse"
    }
  }
}
print(type(config))
# HTTP server
client = Client(config)

async def main():
    async with client:
        print(await client.list_tools())

asyncio.run(main())