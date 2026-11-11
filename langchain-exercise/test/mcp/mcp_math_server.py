# mcp_math_server.py —— 一个带工具/资源/提示模板的 MCP 服务器
from mcp.server.fastmcp import FastMCP   # mcp 1.x 导入（配合 langchain-mcp-adapters）

# ① 创建服务器实例（括号里是服务器名字）
mcp = FastMCP("数学工具服务器")


# ② 工具（Tool）：模型可调用的函数。类型注解会自动生成 JSON Schema，docstring 是描述
@mcp.tool()
def add(a: int, b: int) -> int:
    """两个整数相加"""
    return a + b


@mcp.tool()
def get_weather(city: str) -> str:
    """查询某个城市的天气（演示用假数据）"""
    return f"{city} 今天晴，25℃"


# ③ 资源（Resource）：模型可读取的只读数据。URI 前缀 + 名字
@mcp.resource("config://greeting")
def greeting() -> str:
    return "你好，我是 MCP 服务器"


# ④ 提示模板（Prompt）：可复用的提示词
@mcp.prompt()
def code_review(code: str) -> str:
    return f"请审查以下代码并给出改进建议：\n{code}"


# ⑤ 启动服务器
if __name__ == "__main__":
    # 方式一：stdio（本地子进程，Claude Code / langchain-mcp-adapters 默认）
    mcp.run()

    # 方式二：Streamable HTTP（生产远程部署，host/port 在构造时指定）
    # mcp = FastMCP("数学工具服务器", host="0.0.0.0", port=8001)
    # mcp.run(transport="streamable-http")   # 默认路径 /mcp