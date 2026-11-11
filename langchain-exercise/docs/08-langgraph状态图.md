# 08 — LangGraph 状态图

> 目标：掌握 **LangGraph**——现代智能体编排的核心引擎。用"图（Graph）"显式建模智能体的
> 状态流转，实现 `create_react_agent` 做不到的**自定义多步流程、条件分支、循环**。
> 这是把 Agent 从"玩具"变成"生产级系统"的关键，也是高级岗位面试的分水岭。

---

## 1. 为什么需要 LangGraph？

`create_react_agent`（第 07 篇）虽然好用，但它是**固定的循环结构**（模型→工具→模型→工具…）。
现实中的复杂智能体往往需要：

- "先 A 后 B，A 失败就转 C"（条件分支）
- "某个步骤要重复 N 次直到满足条件"（循环）
- "中途要停下来等人工确认"（人机协作）
- "流程要能断点续跑、要能回放"（持久化）

**LangGraph 把这些都建模成一张"图"**：节点 = 步骤，边 = 流转关系，状态 = 数据。

```
LangGraph 的三个核心概念：

① State（状态）：在节点间流动的数据（通常是一串消息 + 自定义字段）
② Node（节点）：一个处理步骤（调模型、执行工具、普通函数）
③ Edge（边）：节点间的流转规则（固定边 / 条件边）
```

---

## 2. 从最简图开始：StateGraph 的骨架

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# ① 定义状态结构（图里流动的数据）
class State(TypedDict):
    text: str

# ② 定义节点（每个节点是一个函数：接收状态，返回要更新的字段）
def node_a(state: State):
    return {"text": state["text"] + "A"}

def node_b(state: State):
    return {"text": state["text"] + "B"}

# ③ 建图
graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")   # 从入口到 a
graph.add_edge("a", "b")     # a → b
graph.add_edge("b", END)     # b → 结束

# ④ 编译成可运行对象
app = graph.compile()

# ⑤ 运行
result = app.invoke({"text": "X"})
print(result)   # {'text': 'XAB'}
```

```
图结构：  START → [a] → [b] → END

执行时状态变化：
  输入 {"text":"X"}
  → 节点a 返回 {"text":"XA"}
  → 节点b 返回 {"text":"XAB"}
  → 输出 {"text":"XAB"}
```

> 🔑 **节点函数的返回值 = 对状态的"增量更新"**。只返回要改的字段，LangGraph 会自动合并进状态。

---

## 3. 条件边：让流程"会判断"

用 `add_conditional_edges` 根据状态决定走哪条路：

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class State(TypedDict):
    score: int

def 打分(state: State):
    return {"score": state["score"]}   # 假设已有分数

def 合格(state: State):
    return {"score": state["score"], "result": "通过"}

def 不合格(state: State):
    return {"score": state["score"], "result": "不通过"}

# 路由函数：返回下一步节点的名字
def route(state: State) -> str:
    return "合格" if state["score"] >= 60 else "不合格"

graph = StateGraph(State)
graph.add_node("打分", 打分)
graph.add_node("合格", 合格)
graph.add_node("不合格", 不合格)
graph.add_edge(START, "打分")
graph.add_conditional_edges("打分", route, {"合格": "合格", "不合格": "不合格"})
graph.add_edge("合格", END)
graph.add_edge("不合格", END)

app = graph.compile()
print(app.invoke({"score": 80}))   # {'score': 80, 'result': '通过'}
print(app.invoke({"score": 50}))   # {'score': 50, 'result': '不通过'}
```

```
             ┌─ score>=60 → [合格] ─┐
START → [打分]┤                     ├→ END
             └─ score<60  → [不合格]─┘
```

> 路由函数的返回值，必须对应 `add_conditional_edges` 第三参数里定义的名字。

---

## 4. 循环：让流程"反复执行"

图的强大之处在于可以**回环**。比如"最多重试 3 次直到成功"：

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class State(TypedDict):
    attempts: int
    done: bool

def 尝试(state: State):
    # 模拟：前两次失败，第三次成功
    return {"attempts": state["attempts"] + 1, "done": state["attempts"] + 1 >= 3}

def route(state: State) -> str:
    if state["done"]:
        return "结束"
    if state["attempts"] >= 3:
        return "结束"
    return "重试"   # 回到 尝试 节点

graph = StateGraph(State)
graph.add_node("尝试", 尝试)
graph.add_edge(START, "尝试")
graph.add_conditional_edges("尝试", route, {"重试": "尝试", "结束": END})
app = graph.compile()

print(app.invoke({"attempts": 0, "done": False}))
# {'attempts': 3, 'done': True}
```

```
START → [尝试] ── 未完成 ──→ [尝试]（循环，最多3次）
              └── 完成 ──→ END
```

---

## 5. 用 LangGraph 手写一个 Agent（理解 create_react_agent 的底层）

第 07 篇的 `create_react_agent`，本质就是下面这张图。**自己写一遍，彻底搞懂 Agent 内部原理**：

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

# ① 状态 = 消息列表（add_messages 表示"追加"而非覆盖）
class State(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@tool
def add(a: int, b: int) -> int:
    """两个整数相加。"""
    return a + b

# 绑定工具
llm_with_tools = llm.bind_tools([add])

# ② 节点1：调用模型（模型可能输出 tool_calls）
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# ③ 节点2：执行工具
def tool_node(state: State):
    from langgraph.prebuilt import ToolNode
    return ToolNode([add]).invoke(state)

# ④ 路由：模型请求了工具 → 去执行；否则结束
def should_continue(state: State) -> str:
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"       # 还有工具要执行
    return END               # 没工具了，结束

# ⑤ 建图
graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "chatbot")   # 工具执行完回到模型（循环！）
app = graph.compile()

# ⑥ 运行
result = app.invoke({"messages": [HumanMessage(content="3+5等于多少")]})
print(result["messages"][-1].content)
```

```
        ┌────────────────────────────────┐
        │                                │
START → [chatbot(模型)] ──请求工具──→ [tools(执行)]
              │  ▲                         │
              │  └─────────循环─────────────┘
              └── 无工具 ──→ END
```

> 🎯 **这就是 Agent 的真相**：一个"模型节点"和一个"工具节点"之间循环，靠路由函数决定何时停止。
> 你之前用的 `create_react_agent`，内部就是这张图。理解了它，任何自定义 Agent 都能画出来。

---

## 6. 给状态加自定义字段：记录中间结果

实际业务里，状态不只是消息，还会记录"中间产物"（检索结果、计算结果、计数器等）：

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_docs: str      # 自定义字段：检索到的资料
    step_count: int          # 自定义字段：步数
```

每个节点都能读写这些字段，实现"数据在流程中积累"。

---

## 7. 高级能力速览（了解，作为进阶方向）

| 能力 | 作用 | 关键字 |
|------|------|--------|
| **持久化** | 流程存到数据库，可断点续跑、回放 | `checkpointer` |
| **人工介入** | 关键步骤停下来等人工确认 | `interrupt_before` / `interrupt` |
| **子图** | 大图拆成可复用的子图 | `add_node(subgraph)` |
| **流式** | 逐步观察执行过程 | `.stream(..., stream_mode=...)` |

```python
# 持久化示例（保存执行状态到内存，重启可恢复）
from langgraph.checkpoint.memory import MemorySaver

app = graph.compile(checkpointer=MemorySaver())
# 每次调用带 thread_id，状态按线程保存
result = app.invoke({"messages": [...]}, config={"configurable": {"thread_id": "1"}})
```

> 多智能体（第 09 篇）就是"把多个这样的 Agent 作为子图/子节点，再拼成一张更大的图"。

---

## 8. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 节点返回类型不对 | 报错或状态没更新 | 节点返回 dict，且 key 是 State 里定义的字段 |
| 路由返回未定义的节点名 | 运行时报 KeyError | 路由返回值要在 `add_conditional_edges` 第三参数里 |
| 消息状态忘了 `add_messages` | 消息被覆盖而不是追加 | 用 `Annotated[list, add_messages]` |
| 忘记编译 | 直接 invoke 报错 | 先 `.compile()` 得到 app |
| 死循环 | 无限执行 | 设 `recursion_limit`，检查路由函数逻辑 |

---

## 9. 面试高频题

**Q1：LangGraph 的三个核心概念是什么？**
> A：State（状态，在节点间流动的数据）、Node（节点，一个处理步骤，如调模型/执行工具）、
> Edge（边，节点间的流转规则，分固定边和条件边）。用这三者显式建模智能体的控制流。

**Q2：`create_react_agent` 内部的图结构是怎样的？**
> A：本质是一个"模型节点 ↔ 工具节点"的循环：模型节点调用 LLM，若输出 `tool_calls` 就转到工具节点
> 执行工具，执行完回到模型节点；路由函数判断无工具调用时结束。可以用 `StateGraph` 手写复现。

**Q3：`add_conditional_edges` 是做什么的？**
> A：实现条件分支——根据路由函数对当前状态的判断结果，决定下一个执行的节点，让流程"会判断"。

**Q4：LangGraph 相比 Chain 和 AgentExecutor 的优势是什么？**
> A：支持显式的分支、循环、持久化（断点续跑）、人工介入、子图复用，把 Agent 控制流从黑盒变成
> 可控可观测的图，是生产级复杂智能体的标准方案。

---

## 10. 练手题

1. 画一个 3 节点顺序图，验证状态在节点间传递
2. 写一个"登录校验"条件图：密码正确→欢迎页，错误→重试（最多3次）
3. 手写一个"模型↔工具"循环的 Agent（第 5 节代码），加一个自定义状态字段记录工具调用次数
4. 给图加 `MemorySaver` 持久化，用同一个 thread_id 调用两次观察状态保持
5. 把第 5 节的 Agent 改成流式输出，观察每一步状态

---

👉 下一篇：[09 — 多智能体协作](09-多智能体协作.md) · 返回总目录：[00-README](00-README.md)
