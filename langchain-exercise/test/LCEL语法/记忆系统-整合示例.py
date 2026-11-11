import os
import sys
import re
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver   # 短期：多轮对话状态
from langgraph.store.memory import InMemoryStore       # 长期：跨会话记忆
from langgraph.store.base import BaseStore

sys.stdout.reconfigure(encoding="utf-8")  # 让 Windows 控制台正确显示中文

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                 base_url="https://api.deepseek.com",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 temperature=0.7)


# ============================================================
# 1. State：用 add_messages reducer，让消息自动累加（多轮对话的关键）
# ============================================================
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ============================================================
# 2. 节点：LangGraph 会自动注入 config 和 store 两个参数
# ============================================================
def extract_name(text: str):
    """简单规则提取名字（教学用；生产可换成 LLM 或结构化输出）"""
    # 提问句（含"什么/吗/？/谁"等）直接跳过，避免把"我叫什么"误判成自我介绍
    if re.search(r"什么|吗|？|\?|谁|多少|哪里|几岁", text):
        return None
    m = re.search(r"(?:我叫|我是|我的名字(?:叫|是))\s*([一-龥A-Za-z]+)", text)
    return m.group(1) if m else None


def chat_node(state: State, config: RunnableConfig, store: BaseStore) -> dict:
    # ① 从 config 拿 user_id —— 这是"跨会话记忆"的 key，跟 thread_id 是两回事
    user_id = config["configurable"].get("user_id", "anonymous")

    # ② 从 store 读这个用户的名字（长期记忆，跨会话都在）
    item = store.get(("user", user_id), "name")
    name = item.value.get("name") if item else None

    # ③ 如果用户这条消息做了自我介绍，就把名字写进 store
    last = state["messages"][-1]
    if isinstance(last, HumanMessage):
        extracted = extract_name(last.content)
        if extracted:
            store.put(("user", user_id), "name", {"name": extracted})
            name = extracted

    # ④ 用名字（如果有）拼 system prompt，让模型能称呼用户
    system = f"你是一个友好助手，当前用户的名字是「{name}」。" if name \
        else "你是一个友好助手，目前还不知道用户的名字。"

    response = llm.invoke([SystemMessage(content=system), *state["messages"]])
    return {"messages": [response]}


# ============================================================
# 3. 构建图，关键：同时挂上 checkpointer 和 store
# ============================================================
graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

app = graph.compile(
    checkpointer=InMemorySaver(),   # 短期记忆：按 thread_id 保存对话进度
    store=InMemoryStore(),          # 长期记忆：按 namespace+key 保存用户信息
)


# ============================================================
# 4. 场景一：多轮对话（同一 thread_id，checkpointer 记住上下文）
# ============================================================
print("=== 场景一：多轮对话（checkpointer 生效） ===")
cfg1 = {"configurable": {"thread_id": "t1", "user_id": "u1"}}
app.invoke({"messages": [HumanMessage("你好，我叫小明")]}, config=cfg1)
r = app.invoke({"messages": [HumanMessage("我刚才说了我叫什么？")]}, config=cfg1)
print("AI：", r["messages"][-1].content)


# ============================================================
# 5. 场景二：跨会话记忆（换 thread_id，但同一 user_id，store 记住名字）
# ============================================================
print("\n=== 场景二：跨会话记忆（store 生效） ===")
cfg2 = {"configurable": {"thread_id": "t2", "user_id": "u1"}}  # 全新会话，没有历史
r = app.invoke({"messages": [HumanMessage("你还记得我叫什么吗？")]}, config=cfg2)
print("AI：", r["messages"][-1].content)


# ============================================================
# 6. 场景三：不同用户，记忆互不干扰
# ============================================================
print("\n=== 场景三：不同用户隔离 ===")
cfg3 = {"configurable": {"thread_id": "t3", "user_id": "u2"}}  # 另一个用户
r = app.invoke({"messages": [HumanMessage("你知道我叫什么吗？")]}, config=cfg3)
print("AI：", r["messages"][-1].content)


# ============================================================
# 附：切换到 Postgres 只需改"两个后端对象"（节点、图的逻辑完全不变）
# ============================================================
# ① 安装：uv pip install --python .venv langgraph-checkpoint-postgres
# ② 把 InMemorySaver()/InMemoryStore() 换成下面这段（官方推荐的 with 写法）：
#
#   from langgraph.checkpoint.postgres import PostgresSaver, PostgresStore
#   DB_URI = "postgresql://postgres:postgres@localhost:5432/mydb"
#
#   with PostgresSaver.from_conn_string(DB_URI) as checkpointer, \
#        PostgresStore.from_conn_string(DB_URI) as store:
#       checkpointer.setup()   # 必须：建 checkpoint 表
#       store.setup()          # 必须：建 store 表
#       app = graph.compile(checkpointer=checkpointer, store=store)
#       # ... 在 with 块内 invoke
#   # 退出 with 块自动关闭数据库连接
#
# 其余代码（State / chat_node / extract_name / invoke）一行都不用改。
