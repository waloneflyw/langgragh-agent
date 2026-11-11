import asyncio
import os
import sys
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台正确显示中文
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)


async def main():
    # ① 声明要连哪些 MCP 服务器（可连多个）
    client = MultiServerMCPClient({
        "math": {
            "command": "python",
            "args": ["mcp_math_server.py"],
            "transport": "stdio",        # 本地子进程
        },
        # 远程服务器则用：
        # "weather": {
        #     "url": "http://127.0.0.1:8001/mcp",
        #     "transport": "streamable_http",
        # },
    })

    # ② 把 MCP 工具转成 LangChain 的 BaseTool 列表
    tools = await client.get_tools()

    # ③ 直接挂到 ReAct Agent 上（和 07 篇一模一样）
    agent = create_agent(llm, tools)

    # ④ 运行
    result = await agent.ainvoke(
        {"messages": [("user", "用工具帮我算一下 123 + 456 等于多少")]}
    )
    print(result["messages"][-1].content)


asyncio.run(main())