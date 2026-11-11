from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                  base_url="https://api.deepseek.com", 
                 api_key=os.getenv("DEEPSEEK_API_KEY"), 
                 temperature=0.7)


from typing import Annotated,Sequence,TypedDict
from operator import add
from langchain.tools import tool

from langgraph.graph import StateGraph,END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

@tool
def my_tool(input: str) -> str:
    """这是一个示例工具"""
    return f"工具处理结果：{input}"

@tool
def search(query: str) -> str:
  """搜索互联网信息"""
  return f"关于'{query}'的搜索结果：找到3条相关内容"

@tool
def calculator(expression: str) -> str:
  """计算数学表达式"""
  try:
    result = eval(expression)
    return f"计算结果：{result}"
  except Exception as e:
    return f"计算错误：{e}"

tools = [search, calculator]

from langgraph.prebuilt import tools_condition

# 2. 定义State
class AgentState(TypedDict):
  messages: Annotated[Sequence, add]

  # 3. Agent节点
def agent_node(state: AgentState):
  llm_with_tools = llm.bind_tools(tools)
  response = llm_with_tools.invoke(state["messages"])
  return {"messages": [response]}


# 4. 构建Graph（用 tools_condition 替代手写的 should_continue）
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))


graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition, { # 内置条件路由
  "tools": "tools",
  END: END
})
graph.add_edge("tools", "agent")

app = graph.compile()

# 5. 测试
result = app.invoke({"messages": "帮我计算 99*88"})
print(f"回复：{result['messages'][-1].content}")