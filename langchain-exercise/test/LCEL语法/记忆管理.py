"""
记忆管理 demo —— 05 篇练手题 4
把 InMemoryChatMessageHistory 换成「持久化」实现：

  1. SQLChatMessageHistory —— 存 SQLite 数据库，进程重启记忆不丢
  2. RedisChatMessageHistory —— 存 Redis，分布式 / 高并发场景

对比：InMemoryChatMessageHistory 存在内存里，进程一关就忘；
      下面这两种都落在外部存储上，重启后记忆仍在。
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")   # 让控制台正确显示中文

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import (
    SQLChatMessageHistory,
    RedisChatMessageHistory,
)

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是乐于助人的助手，要记住用户说过的话。"),
    MessagesPlaceholder("history"),     # 历史消息自动注入到这里
    ("human", "{input}"),
])
chain = prompt | llm


# ============================================================
# 一、SQLChatMessageHistory（SQLite 持久化）
# ============================================================
def get_sql_history(session_id: str) -> SQLChatMessageHistory:
    # 每次新建一个对象也没关系：它读写的是同一个 sqlite 文件，记忆在文件里
    return SQLChatMessageHistory(
        session_id=session_id,
        connection="sqlite:///chat_history.db",   # 本地 sqlite 文件
    )

sql_bot = RunnableWithMessageHistory(
    chain,
    get_sql_history,
    input_messages_key="input",
    history_messages_key="history",
)

print("========== 一、SQL 记忆 ==========")
cfg_sql = {"configurable": {"session_id": "user-sql-1"}}
print("问:", "我叫小明")
print("答:", sql_bot.invoke({"input": "我叫小明"}, config=cfg_sql).content)
print("问:", "我叫什么？")
print("答:", sql_bot.invoke({"input": "我叫什么？"}, config=cfg_sql).content)

# 关键：因为记忆落在 sqlite 文件里，就算你把上面"写入记忆"那行注释掉、
# 重新跑一次脚本，再问"我叫什么"，它依然记得 —— 这就是"持久化"和 InMemory 的区别。


# ============================================================
# 二、RedisChatMessageHistory（Redis 持久化）
# ============================================================
def get_redis_history(session_id: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=session_id,
        url="redis://localhost:6379/0",   # 需要本机先跑一个 Redis
    )

redis_bot = RunnableWithMessageHistory(
    chain,
    get_redis_history,
    input_messages_key="input",
    history_messages_key="history",
)

print("\n========== 二、Redis 记忆 ==========")
cfg_redis = {"configurable": {"session_id": "user-redis-1"}}
try:
    print("问:", "我喜欢蓝色")
    print("答:", redis_bot.invoke({"input": "我喜欢蓝色"}, config=cfg_redis).content)
    print("问:", "我喜欢什么颜色？")
    print("答:", redis_bot.invoke({"input": "我喜欢什么颜色？"}, config=cfg_redis).content)
except Exception as e:
    print(f"⚠️ Redis 部分跑不起来：{e}")
    print("   请先启动 Redis（例如 docker run -p 6379:6379 redis），再运行本脚本。")
