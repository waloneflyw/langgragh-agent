import sys
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END

sys.stdout.reconfigure(encoding="utf-8")  # 让 Windows 控制台正确显示中文

class StreamState(TypedDict):
  text: str
  steps: Annotated[list, add] # 使用 add reducer 自动合并 steps

def step1_node(state: StreamState):
  return {
    "text": state["text"].upper(),
    "steps": ["大写转换"] # 只需返回当前步骤
   }

def step2_node(state: StreamState):
  return {
    "text": f"[{state['text']}]",
    "steps": ["添加标记"]
   }

def step3_node(state: StreamState):
  return {
    "text": f"1. {state['text']}",
    "steps": ["添加序号"]
   }

# 构建Graph
graph = StateGraph(StreamState)
graph.add_node("step1", step1_node)
graph.add_node("step2", step2_node)
graph.add_node("step3", step3_node)

graph.set_entry_point("step1")
graph.add_edge("step1", "step2")
graph.add_edge("step2", "step3")
graph.add_edge("step3", END)

app = graph.compile()

# 方式1：values 模式（输出每一步的完整 State）
print("=== stream_mode='values' ===")
for state in app.stream({"text": "hello langgraph", "steps": []}, stream_mode="values"):
  print(f"  State: {state}")

print()

# 方式2：updates 模式（只输出每一步的增量更新）
print("=== stream_mode='updates' ===")
for update in app.stream({"text": "hello langgraph", "steps": []}, stream_mode="updates"):
  print(f"  节点更新: {update}")


# ASCII可视化：查看Graph结构
app.get_graph().print_ascii()
