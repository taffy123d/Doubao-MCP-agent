"""MCP服务端启动入口"""
from mcp.server.fastmcp import FastMCP
from skills import register_calculator_tool, register_weather_tool, register_web_search_tool

# 初始化MCP服务（去掉不支持的参数）
mcp = FastMCP(
    name="local-custom-skills"
)

# 注册所有技能工具
register_calculator_tool(mcp)
register_weather_tool(mcp)
register_web_search_tool(mcp)

# 启动MCP服务（stdio模式，MCP标准传输协议）
def main():
    mcp.run()

if __name__ == "__main__":
    main()