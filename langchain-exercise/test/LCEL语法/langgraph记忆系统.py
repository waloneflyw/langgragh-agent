# 	新版（推荐）
# 短期记忆	RunnableWithMessageHistory	MemorySaver (Checkpointer)
# 长期记忆	无官方方案	InMemoryStore / PostgresStore
# 会话隔离	session_id	thread_id
# 依赖	langchain-core	langgraph
# 生产持久化	需自己实现	PostgresSaver / PostgresStore
# 举例：笔记本 vs 档案柜

# 新项目请使用 LangGraph 的 Checkpointer + Store。

# MemorySaver 将数据存储在内存中，程序重启后数据会丢失。仅用于开发测试，生产环境请使用 PostgresSaver。
#InMemoryStore 数据存储在内存中，程序重启后数据丢失。仅用于开发测试，生产环境请使用 PostgresStore

import os
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict
from operator import add
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                 base_url="https://api.deepseek.com",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 temperature=0.7)
# 1. 定义State
class ChatState(TypedDict):
  messages: Annotated[Sequence, add]

# 2. 定义聊天节点
def chat_node(state: ChatState):
  response = llm.invoke(state["messages"])
  return {"messages": [response]}

# 3. 构建Graph
graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.set_entry_point("chat")
graph.add_edge("chat", END)

# 4. 关键：添加 Checkpointer
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# 5. 使用 thread_id 区分不同会话
config_a = {"configurable": {"thread_id": "user-alice"}}
config_b = {"configurable": {"thread_id": "user-bob"}}

# === 用户A的对话 ===
print("=== 用户A ===")

result = app.invoke({"messages": [HumanMessage("我叫张三")]}, config_a)
print(f"第1轮 AI：{result['messages'][-1].content}")

result = app.invoke({"messages": [HumanMessage("我25岁，住在北京")]}, config_a)
print(f"第2轮 AI：{result['messages'][-1].content}")

result = app.invoke({"messages": [HumanMessage("我叫什么名字？多大？住哪？")]}, config_a)
print(f"第3轮 AI：{result['messages'][-1].content}")

# == 用户B的对话（独立的会话） ===
print("\n=== 用户B ===")

result = app.invoke({"messages": [HumanMessage("我叫什么名字？")]}, config_b)
print(f"用户B问 AI：{result['messages'][-1].content}")

# === 用户A继续对话（记忆还在） ===
print("\n=== 用户A继续 ===")

result = app.invoke({"messages": [HumanMessage("你还记得我喜欢什么吗？")]}, config_a)
print(f"用户A问 AI：{result['messages'][-1].content}")


#长期记忆
from langgraph.store.memory import InMemoryStore

# 1. 创建 Store
store = InMemoryStore()

# 2. 写入数据（put）
# put(命名空间, key, value)
store.put(
   ("users", "user-001"),     # 命名空间：用户user-001
  "profile",            # key
   {"name": "张三", "age": 25, "city": "北京", "job": "Python开发者"}
)

store.put(
   ("users", "user-001"),
  "preferences",
   {"language": "Python", "framework": "LangChain", "theme": "dark"}
)

store.put(
   ("users", "user-002"),
  "profile",
   {"name": "李四", "age": 30, "city": "上海", "job": "前端开发"}
)

# 3. 读取数据（get）
profile = store.get(("users", "user-001"), "profile")
print(f"用户信息：{profile.value}")

prefs = store.get(("users", "user-001"), "preferences")
print(f"偏好设置：{prefs.value}")

# 4. 更新数据（put 相同 key 会覆盖）
store.put(
   ("users", "user-001"),
  "profile",
   {"name": "张三", "age": 26, "city": "北京", "job": "全栈开发"}
)

profile = store.get(("users", "user-001"), "profile")
print(f"更新后：{profile.value}")

# 5. 搜索数据（search）
results = store.search(("users", "user-001"))
print(f"\nuser-001 的所有记忆：")
for item in results:
  print(f"  {item.key}: {item.value}")


  
# 4. 系统提示：让Agent主动记住用户信息
SYSTEM_PROMPT = """你是一个友好的AI助手。
当用户提到自己的个人信息时（姓名、年龄、城市、工作等），
请主动调用 save_user_info 工具保存到长期记忆中。
用户ID固定为 "user-001"。
"""
