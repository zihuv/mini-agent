from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def add(a, b):
    """
    计算两个数的和
    参数: a (int), b (int)
    返回: int
    """
    return a + b

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000)