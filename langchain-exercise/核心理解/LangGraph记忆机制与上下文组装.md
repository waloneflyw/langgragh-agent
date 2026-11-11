# LangGraph 记忆机制与上下文组装（核心理解）

> 目标：彻底搞清楚 LangGraph 里 **短期记忆 vs 长期记忆** 的本质区别，以及**一次 LLM 调用的上下文是怎么拼出来的**。
> 这是面试里区分"背过 API"和"真懂 Agent 底层"的高频考点，也是写生产级 Agent 的必备认知。

---

## 0. 一句话结论（先记住这个，再往下展开）

| 概念 | 一句话 | 底层机制 | 作用域 |
|------|--------|----------|--------|
| **短期记忆** | "这一段对话说了什么" | **Checkpointer（检查点）**，存图的状态 `State` | 绑定 `thread_id`（单会话） |
| **长期记忆** | "这个用户是谁、有什么偏好" | **Store（存储）**，存 JSON 文档 | 跨线程（全局 / 按用户） |
| **一次上下文** | 系统提示 + 长期记忆 + 会话历史 + 当前输入 + 工具定义 | 运行时逐层拼装 | 发给模型的那一坨 |

> ⚠️ **最常见的误区**：以为"短期 = 内存、重启就丢；长期 = 数据库、永远在"。
> **错**。真正的区别是**作用域（scope）**：短期记忆按 thread 隔离，长期记忆跨 thread 共享。
> 持久化与否只取决于你给它们各自配了哪个后端。

---

## 1. 总览对比表（面试直接背这张）

| 维度 | 短期记忆 Short-term | 长期记忆 Long-term |
|------|---------------------|---------------------|
| 实现机制 | `checkpointer`（检查点） | `store`（存储） |
| 存的数据 | 图的 `State`（消息历史 + 自定义字段） | JSON 文档（用户画像、事实、偏好） |
| 定位方式 | `thread_id` | `namespace`（命名空间）+ `key`（键） |
| 作用域 | 单个线程/会话，线程之间互不可见 | 跨线程，全局或按命名空间隔离 |
| 作用 | 多轮对话不"失忆"、断点续跑、时间旅行 | 跨会话记住用户、共享知识 |
| 生命周期 | 跟随一个 thread；换 thread 就换一套 | 独立于任何 thread，会话删了它还在 |
| 典型后端 | `MemorySaver` / `SqliteSaver` / `PostgresSaver` | `InMemoryStore` / `PostgresStore` |
| 典型数据 | `[HumanMessage, AIMessage, ToolMessage, ...]` | `{"name": "小明", "style": "简洁"}` |

---

## 2. 短期记忆：Checkpointer（线程级状态）

### 2.1 存什么

存的是**整张图在每个"超步（super-step）"的状态快照**，也就是你定义的 `State`。最常见的 `MessagesState` 里：

- `messages`：本轮会话**完整**的消息列表（`HumanMessage` / `AIMessage` / `ToolMessage` / `SystemMessage`）
- 你在 `State` 里自己加的任何字段：`current_step`、`retrieved_docs`、`step_count`、中间计算结果……

一个 checkpoint 内部 = **状态数据 + 元信息**（来源节点、步号、时间戳、下一步指针等），所以才能支持"回放 / 续跑"。

### 2.2 作用

1. **多轮对话**：同一个 thread 里记得之前说过的话、做过的步骤
2. **断点续跑 / 时间旅行（time-travel）**：回到任意历史 checkpoint 重放
3. **human-in-the-loop**：关键步骤中断，等人工审批后从断点继续

### 2.3 生命周期

绑定 `thread_id`。**同一个 `config`（同一个 thread_id）调用 → 接着上次状态继续；换 thread_id → 全新会话**。

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState

graph = StateGraph(MessagesState)
# ... 加节点、边 ...
app = graph.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-123"}}

app.invoke({"messages": [("user", "你好")]}, config)
app.invoke({"messages": [("user", "我叫小明")]}, config)   # 还记得"你好"

# 换 thread_id = 全新会话，看不到上面的消息
config2 = {"configurable": {"thread_id": "user-456"}}
```

> 🔑 换成 `SqliteSaver` / `PostgresSaver`，检查点也能跨进程重启保存——但**它依然是短期记忆**，
> 因为它是**按 thread 隔离**的：A 会话永远看不到 B 会话的内容。

### 2.4 后端怎么选（生命周期差异就在这）

| 后端 | 持久化 | 适用场景 |
|------|--------|----------|
| `MemorySaver` | ❌ 仅内存，进程重启即丢 | 本地调试、跑 demo |
| `SqliteSaver` | ✅ 本地单文件 | 单机小规模、桌面应用 |
| `PostgresSaver` | ✅ 数据库 | 生产环境、多实例共享 |

> 注意：即使用了 `PostgresSaver`，一条 thread 的 checkpoint 也不会"跨 thread 共享"——这就是它
> 区别于长期记忆的根本点。

---

## 3. 长期记忆：Store（跨线程共享）

### 3.1 存什么

Store 里存的是**任意 JSON 文档**，用「**命名空间 + 键**」两级定位：

- **namespace**（命名空间）：层级元组，通常 `("memories", user_id)`，用来隔离不同用户/不同类别
- **key + value**：一条具体事实，如用户偏好、名字、提炼过的摘要

### 3.2 作用

- **跨会话记住信息**：用户下次开新 thread（新会话）还能想起"他叫小明、喜欢简洁回答"
- 存**全局或按用户共享**的知识、用户画像、语义记忆、情节记忆
- 常用来实现认知科学里的三种记忆：**语义记忆**（事实）、**情节记忆**（过去事件）、**程序记忆**（怎么做）

### 3.3 生命周期

**独立于任何 thread**。只要存储后端还在就一直在；删除某个会话不影响它。

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 写：命名空间 ("memories", "user-123")，键 "preference"，值 JSON
store.put(("memories", "user-123"), "preference",
          {"value": {"name": "小明", "style": "简洁"}})

# 读 / 搜（按命名空间前缀批量检索）
store.get(("memories", "user-123"), "preference")
store.search(("memories", "user-123"))
```

### 3.4 命名空间设计（面试能聊出彩的点）

命名空间本质是一棵"路径树"，用元组表达层级：

```
("memories",)                    ← 所有记忆
("memories", "user-123")         ← 用户 123 的所有记忆
("memories", "user-123", "prefs") ← 用户 123 的偏好类记忆
```

`store.search(("memories", "user-123"))` 会返回该前缀下的所有文档，天然支持"按用户/按类别"批量拉取。

---

## 4. 一次上下文是怎么组装的（重点）

一次 LLM 调用前，上下文是这样**层层拼出来**的：

```
新输入 (user message)
   │
   ▼
① 按 thread_id 加载最新 checkpoint ──→ 得到 State["messages"]（短期记忆：会话历史）
   │
   ▼
② 从 Store 检索长期记忆 ──→ 得到用户画像/事实（跨会话）
   │
   ▼
③ 拼装 prompt：
     系统提示 (system prompt)
   + 检索到的长期记忆（通常插入系统提示，或单独一条消息）
   + 会话消息历史（短期记忆）
   + 当前用户输入
   + 工具定义 (tool schemas)
   │
   ▼
④ bind_tools 绑定工具后发给模型
```

### 4.1 一次上下文的典型构成（5 部分）

1. **系统提示**（SystemMessage / 开发者指令）：角色设定、行为约束、输出格式要求
2. **长期记忆**：从 Store 检索出的用户偏好、事实（通常插进系统提示）
3. **会话历史**：`State["messages"]` 里的完整消息列表 —— **这是短期记忆**
4. **当前输入**：本次用户刚发的那条消息
5. **工具定义**：`bind_tools` 绑定的函数 schema，让模型决定是否调用工具

### 4.2 代码示意（把抽象概念落成一行行调用）

```python
def call_model(state, store, user_id):
    # ① 短期记忆：会话历史（来自 State）
    messages = state["messages"]

    # ② 长期记忆：跨会话检索（来自 Store）
    memories = store.search(("memories", user_id))
    memory_text = "\n".join(str(m.value) for m in memories)

    # ③ 拼装系统提示
    system = f"你是助手。已知用户信息：{memory_text}"
    full_prompt = [{"role": "system", "content": system}] + messages

    # ④ 绑定工具后调用
    return {"messages": [llm.bind_tools(tools).invoke(full_prompt)]}
```

> 🎯 **一句话记忆**：短期记忆决定"这一段对话"；长期记忆决定"跨对话你是谁"；上下文 = 两者 + 系统提示 + 工具，一起喂给模型。

---

## 5. 易混淆点 / 常见坑

| 坑 | 现象 / 误区 | 正确认知 |
|----|-------------|----------|
| 把"短期"当"内存" | 以为短期记忆一定重启就丢 | 短期=作用域是 thread，持久化与否看 checkpointer 后端 |
| 只配了 `MemorySaver` 就上线 | 生产环境重启后对话全丢 | 生产用 `PostgresSaver` / `SqliteSaver` |
| 忘了传 `thread_id` | 每次 invoke 都是新会话 | 长期对话必须固定 `config` 里的 `thread_id` |
| 短期记忆里塞长期数据 | 用户画像只存在某个 thread 里 | 跨会话的放 Store，会话内的放 State |
| 长期记忆不设命名空间 | 所有用户数据混在一起 | 用 `("memories", user_id)` 隔离 |
| 把检索结果全塞进系统提示 | 上下文爆炸、token 超限 | 按需检索 + 摘要压缩，只取相关记忆 |

---

## 6. 面试高频题（含参考答案）

**Q1：LangGraph 的短期记忆和长期记忆本质区别是什么？**
> A：本质区别是**作用域**，不是持久化。短期记忆由 `checkpointer` 实现，存图的 `State`，绑定 `thread_id`，
> 只在单个会话内可见；长期记忆由 `store` 实现，存 JSON 文档，用命名空间 + 键定位，跨线程共享。
> 两者是否持久化取决于各自的后端（`MemorySaver` vs `PostgresSaver`、`InMemoryStore` vs `PostgresStore`）。

**Q2：为什么用了 PostgresSaver，检查点能跨重启保存，它仍然是"短期"记忆？**
> A：因为它按 thread 隔离，A 会话看不到 B 会话的内容，作用域仍是单线程。"长期"的含义是跨线程
> 共享、独立于会话生命周期，这是 Store 才具备的能力。

**Q3：一次发给 LLM 的上下文包含哪些内容？**
> A：① 系统提示（角色/约束/格式）；② 从 Store 检索的长期记忆（用户画像）；③ 会话历史（State 里的
> messages，即短期记忆）；④ 当前用户输入；⑤ `bind_tools` 绑定的工具定义。

**Q4：checkpoint 里除了消息还有什么？**
> A：整个 `State`（包括自定义字段）＋元信息（来源节点、步号、时间戳、下一步指针），正因如此才能
> 支持断点续跑、时间旅行回放和 human-in-the-loop。

**Q5：怎么设计长期记忆的命名空间？**
> A：用层级元组表达路径，如 `("memories", user_id, "prefs")`，这样 `store.search(("memories", user_id))`
> 能按前缀批量检索某用户的所有记忆，实现按用户/类别隔离。

---

## 7. 自测 / 练手

1. 用 `MemorySaver` 建一个最小图，同一个 `thread_id` 调两次，观察第二次是否记得第一次的输入
2. 换一个 `thread_id` 再调，确认看不到之前的消息（验证作用域隔离）
3. 用 `InMemoryStore` 写入一条 `("memories", "u1")` 下的偏好，再用 `search` 读回来
4. 写一个 `call_model` 函数，把「Store 检索结果 + State 会话历史」拼成一次完整 prompt
5. 口头复述：为什么 `PostgresSaver` 持久化的检查点仍然是"短期"记忆

---

👉 关联阅读：[08 — LangGraph 状态图](../docs/08-langgraph状态图.md) · [05 — 对话记忆与多轮](../docs/05-对话记忆与多轮.md)
