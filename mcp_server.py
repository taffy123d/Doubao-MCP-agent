"""MCP 服务端启动入口"""
from mcp.server.fastmcp import FastMCP
from skills import register_calculator_tool, register_weather_tool, register_time_tool

# 初始化 MCP 服务
mcp = FastMCP(
    name="local-custom-skills"
)

# 注册所有技能工具
register_calculator_tool(mcp)
register_weather_tool(mcp)
register_time_tool(mcp)

def main():
    """启动 MCP 服务"""
    mcp.run()

if __name__ == "__main__":
    main()
