from dotenv import load_dotenv
import os
import sys

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

sys.stdout.reconfigure(encoding="utf-8")  # 让 Windows 控制台正确显示中文

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                 base_url="https://api.deepseek.com",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 temperature=0.7)


# ============================================================
# 定义工具：用 @tool 装饰器把普通函数变成 LLM 可调用的工具
# ============================================================
@tool
def search(query: str) -> str:
    """搜索互联网信息"""
    return f"关于'{query}'的搜索结果：找到3条相关内容"


@tool
def calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        # ⚠️ eval 会执行任意代码，仅用于演示；生产环境务必换成安全的解析器
        result = eval(expression)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算错误：{e}"


# ============================================================
# 一行创建智能体：模型 + 工具 → 自动生成 ReAct 循环图
# ============================================================
app = create_react_agent(llm, [search, calculator])

# 运行：问题同时涉及"计算"，观察智能体如何自动调用 calculator 工具
result = app.invoke({"messages": [HumanMessage("请帮我计算 123 * 456 等于多少")]})

print("=== 最终回复 ===")
print(result["messages"][-1].content)

print("\n=== 完整消息流（能看到它自动调用了哪些工具） ===")
for m in result["messages"]:
    print(f"[{m.type}] {m.content}")
