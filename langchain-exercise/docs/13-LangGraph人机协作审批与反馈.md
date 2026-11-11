# 13 — LangGraph 人机协作：审批模式与反馈模式

> 目标：掌握 LangGraph 的 **Human-in-the-Loop（人机协作）** 两大模式——**审批模式**和**反馈模式**。
> 学完你能让智能体在「关键动作」或「关键产物」上**主动停下来等人拍板/修改**，而不是一路狂奔。
> 这是智能体从「玩具」走向「生产可用」的最后一公里，也是面试必考。

---

## 1. 为什么智能体需要"人"参与

智能体（Agent）的威力在于**自主执行**，但自主也意味着风险：

```
危险场景：用户说「帮我把不活跃用户全删了」
          → Agent 真的去执行删除 → 一夜删光 → 事故
```

两类「人必须介入」的情况：

| 类型 | 什么时候需要人 | 例子 |
|------|--------------|------|
| **安全/合规** | 动作不可逆、代价高 | 删除数据、发邮件、转账、部署上线 |
| **质量/偏好** | 机器生成的不够好、或不符合预期 | 写文案、做方案、改代码、出报告 |

LangGraph 为此提供了**打断机制**：让 Agent 在某个点**暂停**，把控制权交回给人，人决定后再继续。
这个机制就派生出两种经典模式——**审批**（决定「做不做」）和**反馈**（决定「改不改」）。

---

## 2. 核心机制：interrupt() / Command(resume) / checkpointer

先吃透这一个原语，两种模式都是它的排列组合。**这段代码跑得通，就是后面一切的基础：**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command       # interrupt 和 Command 都从这里导入
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict):
    count: int

def 节点(state):
    # ① 在这里暂停，把 "是否批准？" 交给人类；返回值 = 人类后来给的答复
    答复 = interrupt("是否批准？yes/no")
    return {"count": state["count"] + (1 if 答复 == "yes" else 0)}

g = StateGraph(State)
g.add_node("节点", 节点)
g.add_edge(START, "节点")
g.add_edge("节点", END)
app = g.compile(checkpointer=MemorySaver())   # ② 必须配 checkpointer，否则无法暂停

config = {"configurable": {"thread_id": "会话1"}}   # ③ thread_id 标识"这一个会话"

# ④ 第一次调用：跑到 interrupt 就暂停返回
app.invoke({"count": 0}, config=config)

# ⑤ 查看"卡在哪、问的是什么"
快照 = app.get_state(config)
print(快照.interrupts[0].value)   # 输出：是否批准？yes/no

# ⑥ 人类决定后，用 Command(resume=...) 恢复，interrupt 会返回这个值
app.invoke(Command(resume="yes"), config=config)
print(app.get_state(config).values)   # {'count': 1}
```

### 三个必须理解的要点

| 要点 | 说明 |
|------|------|
| `interrupt(value)` | 把 `value` 交回调用方并**暂停**；恢复时它**返回**人类给的 resume 值 |
| `Command(resume=值)` | 把「人类决定」喂回暂停点，让图从那里继续跑 |
| `checkpointer` | **没有它 `interrupt` 直接报错**——因为暂停后状态要持久化，下次恢复才能接着跑 |

### 为什么一定要 checkpointer + thread_id

`interrupt` 的本质是「**跑一半 → 存盘 → 下次接着跑**」。所以：

- **checkpointer** 负责「存盘」（状态存到内存 / 数据库）；
- **thread_id** 负责「分账本」——不同会话各存各的状态，互不串扰。

> 🔑 一句话：**interrupt 是把图"冻住"，Command(resume) 是把它"解冻"，checkpointer 是冰箱，thread_id 是冰箱里的抽屉。**

---

## 3. 两种模式一图看清

| | 审批模式（Approve） | 反馈模式（Feedback / Edit） |
|---|---|---|
| 回答的问题 | **「这件事要不要做？」** | **「这个结果要不要改？」** |
| interrupt 放哪 | **敏感动作之前** | **生成结果之后** |
| 人做什么 | 批准 / 拒绝（二选一） | 审阅 / 修改 / 补充 |
| resume 给回什么 | 一个决定（`批准`/`拒绝`） | 修改后的内容 |
| 典型场景 | 删除、发邮件、转账、部署 | 文案、方案、代码、报告 |

同一个原语，区别只在**「打断的位置」**和**「人交回的东西」**。

---

## 4. 审批模式：敏感操作前先问人

> 思路：在**执行敏感动作之前** `interrupt`，人批准才继续，拒绝就跳过。

**完整可运行示例（删除用户前先审批）：**

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台正确显示中文

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict):
    user_id: int
    result: str

def 删除节点(state):
    # 敏感动作（删用户）之前先打断，请人审批
    决定 = interrupt({
        "type": "审批",
        "操作": f"删除用户 {state['user_id']}",
        "选项": ["批准", "拒绝"],
    })
    if 决定 == "批准":
        # 这里接你真实会调用的删除函数
        return {"result": f"已删除用户 {state['user_id']}"}
    return {"result": f"已取消，用户 {state['user_id']} 未删除"}

g = StateGraph(State)
g.add_node("删除", 删除节点)
g.add_edge(START, "删除")
g.add_edge("删除", END)
app = g.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "会话A"}}

# 第一步：Agent 发起"删除用户 123"，跑到审批处停下
app.invoke({"user_id": 123}, config=config)
快照 = app.get_state(config)
print("等待审批：", 快照.interrupts[0].value)
# 输出：{'type': '审批', '操作': '删除用户 123', '选项': ['批准', '拒绝']}

# 第二步：人类点「批准」（点「拒绝」则走另一分支）
app.invoke(Command(resume="批准"), config=config)
print("最终状态：", app.get_state(config).values["result"])   # 已删除用户 123
```

> 🔑 审批模式的关键：**interrupt 的返回值是一个「决定」**。你可以用字符串（`批准`/`拒绝`）、
> 布尔值（`True`/`False`）或结构化字典（`{"allowed": True, "reason": "..."}`），随业务需要。

---

## 5. 反馈模式：生成后让人审查修改

> 思路：在**生成结果之后** `interrupt`，把产物交给人审阅，人改完再继续。

**完整可运行示例（写方案 → 人审改 → 定稿）：**

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict):
    topic: str
    draft: str
    final: str

def 生成初稿(state):
    # 模拟 LLM 生成一版初稿
    draft = f"关于「{state['topic']}」的初稿：第一点……第二点……（待完善）"
    return {"draft": draft}

def 人工审阅(state):
    # 初稿生成后打断，把初稿交给人，人返回修改后的定稿
    定稿 = interrupt({
        "type": "反馈",
        "初稿": state["draft"],
        "说明": "请审阅修改，返回最终版本",
    })
    return {"final": 定稿}

g = StateGraph(State)
g.add_node("生成", 生成初稿)
g.add_node("审阅", 人工审阅)
g.add_edge(START, "生成")
g.add_edge("生成", "审阅")
g.add_edge("审阅", END)
app = g.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "会话B"}}

# 第一步：生成初稿，在"审阅"处停下
app.invoke({"topic": "年度总结"}, config=config)
快照 = app.get_state(config)
print("待审阅初稿：", 快照.interrupts[0].value["初稿"])

# 第二步：人审阅后，把修改好的定稿交回去
app.invoke(Command(resume="（人类修改后的最终版：优化了结构，补充了数据……）"), config=config)
print("定稿：", app.get_state(config).values["final"])
```

> 🔑 反馈模式的关键：**interrupt 的返回值是「修改后的内容」**，而不是一个 yes/no。
> 人在恢复时把改好的东西整个交回来，图用它继续往下跑（比如发出去、存起来、再加工）。

---

## 6. 和 create_agent 结合：interrupt_before / interrupt_after

你在 [12 篇](12-MCP模型上下文协议.md) 用过的 `create_agent`（LangChain 1.x）**内建支持人机协作**，
不用手动写 `interrupt()`，传两个参数即可：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

agent = create_agent(
    llm, tools,
    checkpointer=MemorySaver(),       # 同样必须配 checkpointer
    interrupt_before=["tools"],       # 审批：工具执行前暂停，人工决定放不放行
    # interrupt_after=["tools"],      # 反馈：工具执行后暂停，人看结果再决定下一步
)
config = {"configurable": {"thread_id": "会话C"}}

# 触发一次会调工具的请求，会在 tools 前停下
agent.invoke({"messages": [("user", "删除用户 123")]}, config=config)

# 人工放行后恢复
agent.invoke(Command(resume={"allow": True}), config=config)
```

- `interrupt_before=["tools"]` → **审批模式**：模型要调工具时，先停下等人批准。
- `interrupt_after=["tools"]` → **反馈/审查模式**：工具跑完后停下，人看结果再决定。

> 它底层就是第 2 节那套 `interrupt()` 机制，只是把「在哪个节点前后打断」做成了参数。
> 具体 resume 该传什么值，取决于你打断的节点，实践中以 `get_state().interrupts` 里看到的信息为准。

---

## 7. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 忘配 `checkpointer` | `interrupt` 直接报错 | `compile(checkpointer=MemorySaver())` 或数据库版 |
| `thread_id` 不一致 | 恢复时找不到状态 / 状态串到别的会话 | 同一会话恢复必须用**同一个** `thread_id` |
| resume 值类型对不上 | 节点里拿到 `None` 或类型错误 | 恢复时传的值要和 `interrupt` 处约定的结构一致 |
| 把 interrupt 放循环里 | 每一轮都停下来问人 | 只在真正需要人的节点里打断，或加条件跳过 |
| 用 `MemorySaver` 上生产 | 重启后「冻结」的会话全丢 | 生产换 Postgres / Redis 等持久化 checkpointer |
| 手动跑 server 式的误区 | 以为要自己起个服务 | 这是图内部的暂停/恢复，不是进程，别和第 12 篇的 MCP 搞混 |

---

## 8. 面试高频题

**Q1：LangGraph 人机协作有哪两种典型模式？本质区别是什么？**
> A：审批模式（Approve）和反馈模式（Feedback/Edit）。区别在「打断的位置」和「人交回的东西」：
> 审批在**敏感动作前**打断、人交回**决定**；反馈在**生成结果后**打断、人交回**修改后的内容**。

**Q2：`interrupt()` 的原理？为什么必须 `checkpointer`？**
> A：`interrupt` 把图在某个点「冻住」并返回信息给调用方，恢复时 `Command(resume=...)` 让它接着跑。
> 因为要「跑一半存盘、下次接着跑」，所以必须靠 `checkpointer` 持久化状态，否则无法恢复。

**Q3：`Command(resume=...)` 的作用？**
> A：它是恢复指令，把「人类的决定/修改」喂回 `interrupt` 暂停点，`interrupt` 会把该值返回给节点继续执行。

**Q4：`thread_id` 的作用？**
> A：标识一个会话/线程。checkpointer 按 thread_id 分开存状态，保证多用户、多会话之间不串账本。

**Q5：如何用 `create_agent` 快速实现审批和反馈？**
> A：传 `interrupt_before=["tools"]` 实现工具执行前审批，`interrupt_after=["tools"]` 实现工具执行后审查，
> 配 `checkpointer` 后同样用 `Command(resume=...)` 恢复。

**Q6：生产环境 checkpointer 怎么选？**
> A：开发调试用 `MemorySaver`；生产要持久化、支持多实例，用 Postgres（`langgraph-checkpoint-postgres`）
> 或 Redis 等实现，避免重启丢状态、也不受单机内存限制。

---

## 9. 练手题

1. 把第 4 节改成「发邮件」场景：发之前审批，批准才发、拒绝则不发生成一句话说明
2. 实现一个「三连审批」：删除用户需要依次经过「组长→经理→管理员」三级批准才执行
3. 把第 5 节改成「翻译审校」：先翻译初稿，人审校修改后返回定稿
4. 用 `create_agent(interrupt_before=["tools"])` 接一个工具，验证每次调工具前都会停下来等人放行
5. 把 `MemorySaver` 换成持久化 checkpointer（如 sqlite），验证暂停后重启程序仍能恢复
6. 给第 4 节加一个「拒绝时记录拒绝原因」的分支，并把原因写回状态

---

👉 下一篇：[14 — A2A 智能体互联协议](14-A2A智能体互联协议.md) · 上一篇：[12 — MCP 模型上下文协议](12-MCP模型上下文协议.md) · 返回总目录：[00-README](00-README.md)
