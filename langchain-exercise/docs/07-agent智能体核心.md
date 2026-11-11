# 07 — Agent 智能体核心

> 目标：掌握**Agent（智能体）**的核心概念与两种实现方式。这是整套课程的核心篇章——
> 理解 Agent 与 Chain 的本质区别、ReAct 原理，并能用**现代标准 `create_react_agent`** 造出第一个真正会规划的智能体。

---

## 1. Agent 和 Chain 的本质区别

前几篇你写的都是 **Chain（链）**：固定的流水线，输入→一步步→输出，路径写死。

**Agent（智能体）** 则不同：**路径由模型动态决定**。模型在每一步"思考"后，自主决定下一步做什么。

| 维度 | Chain（链） | Agent（智能体） |
|------|------------|----------------|
| 执行路径 | 写死的，固定 | **动态，模型决定** |
| 是否有循环 | 无 | 有（反复"思考→行动→观察"） |
| 能否用工具 | 需要你手动编排 | **模型自主选择调用工具** |
| 适合场景 | 流程明确、可预测 | 任务开放、需要多步推理 |
| 类比 | 流水线 | 一个有自主权的员工 |

```
Chain（流水线）：  input → [步骤A] → [步骤B] → [步骤C] → output    （一条直线）

Agent（自主）：    input → [思考] → [用工具1] → [观察结果] → [思考] → [用工具2] → ... → output
                        ↑______________________________________________|
                                 （循环，直到模型觉得完成了）
```

> 🔑 **一句话记住**：Chain 是"我怎么安排，它就怎么走"；Agent 是"给它目标和工具，它自己想办法"。

---

## 2. ReAct 原理：Agent 的经典范式

ReAct = **Re**asoning（推理）+ **Act**ing（行动）。Agent 每轮做三件事：

```
循环执行：
  ① Thought（思考）：分析当前情况，想下一步该怎么办
  ② Action（行动）：决定调用哪个工具、传什么参数
  ③ Observation（观察）：拿到工具返回结果，更新认知
  直到：模型判断"任务完成"，输出最终答案（Finish）
```

用一个具体任务演示。问题："上海今天天气怎么样？适合跑步吗？"

```
Thought: 用户想知道上海天气，我需要调用天气工具
Action: get_weather("上海")
Observation: "上海今天多云，22℃，微风"
Thought: 22℃ 微风适合跑步，可以直接回答了
Finish: "上海今天22℃，多云微风，很适合跑步。"
```

**现代实现**：ReAct 的"思考"和"行动"已由模型的 **Tool Calling** 能力（第 06 篇）原生承载——模型不再需要显式输出"Thought:"文字，而是直接输出结构化的 `tool_calls`。但**这个循环逻辑不变**。

---

## 3. 方式一：经典 AgentExecutor（了解，面试会问）

LangChain 早期用 `AgentExecutor` 实现上述循环。**现在已被 LangGraph 取代**，但面试可能问，了解其 API 和局限：

```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询城市天气。"""
    return f"{city}：晴，25℃"

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是助手，能用工具解决问题。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),   # 存放"思考轨迹"
])

# 创建 agent + 执行器
agent = create_tool_calling_agent(llm, [get_weather], prompt)
executor = AgentExecutor(agent=agent, tools=[get_weather])

print(executor.invoke({"input": "深圳天气怎么样？"}))
```

**AgentExecutor 的局限**：不易加自定义步骤、不易持久化、难以实现复杂的循环/分支控制。
因此 LangChain 官方已把重心转向 **LangGraph**。

> 面试话术：*"早期的 AgentExecutor 把 ReAct 循环封装成黑盒，扩展性和可控性差，
> 现代实践推荐用 LangGraph 显式构建状态图，自己掌控每一步。"*

---

## 4. 方式二：现代标准 —— `create_react_agent`（重点掌握）

LangGraph 提供了 **一行代码创建 Agent** 的 `create_react_agent`，它内部就是一个"模型→工具→循环"的状态图：

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@tool
def add(a: int, b: int) -> int:
    """计算两个整数的和。"""
    return a + b

@tool
def get_weather(city: str) -> str:
    """查询城市实时天气。"""
    return f"{city}：晴，25℃"

# 一行创建智能体：给它模型和工具
agent = create_react_agent(llm, tools=[add, get_weather])

# ① 普通调用（invoke 返回完整消息轨迹）
result = agent.invoke({"messages": [("human", "算一下 3+5 等于多少，再看看北京天气")]})
# 最终答案在最后一条消息里
print(result["messages"][-1].content)
```

### 4.1 流式输出（观察 Agent 的思考过程）

```python
for chunk in agent.stream(
    {"messages": [("human", "北京天气如何？适合出门吗？")]},
    stream_mode="values",   # 每个状态变化都输出
):
    msg = chunk["messages"][-1]
    if msg.type == "tool":
        print(f"🔧 调用工具：{msg.name}")
    elif msg.type == "ai" and msg.content:
        print(f"🤖 回答：{msg.content}")
```

运行后你能亲眼看到 Agent **先调工具、再回答**的全过程——这就是 ReAct 循环的可视化。

### 4.2 关键细节：输入输出都是"消息列表"

`create_react_agent` 的输入/输出都围绕 `messages` 这个 key（状态是一串消息）：

```python
# 输入
{"messages": [("human", "你的问题")]}          # 元组会被自动转成 HumanMessage
{"messages": [HumanMessage(content="...")]}    # 也可以直接传消息对象

# 输出
result["messages"]   # 完整的消息轨迹（含工具调用、结果、最终回答）
```

---

## 5. 完整示例：一个"能做事的"实用智能体

做一个"餐厅推荐 + 算账"助手，串联工具调用和多步推理：

```python
# 07_demo.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@tool
def search_restaurants(cuisine: str) -> str:
    """根据菜系搜索推荐餐厅，返回餐厅名和人均价格。"""
    data = {
        "川菜": "蜀香园（人均80元）、麻辣空间（人均60元）",
        "粤菜": "陶陶居（人均120元）、点都德（人均90元）",
        "日料": "寿司之森（人均200元）",
    }
    return data.get(cuisine, "没有找到相关菜系的餐厅")

@tool
def calculate_total(price_per_person: int, people: int) -> int:
    """计算总费用：人均价格 × 人数。"""
    return price_per_person * people

agent = create_react_agent(llm, tools=[search_restaurants, calculate_total])

# 一个需要多步推理的问题：先搜餐厅，再算账
question = "4个人想吃川菜，帮我推荐餐厅并算一下大概总花费（按人均80元算）"
result = agent.invoke({"messages": [("human", question)]})
print("最终回答：", result["messages"][-1].content)
```

> 🎯 你会看到 Agent 自己完成了"搜索川菜餐厅 → 计算总价 → 综合回答"多步任务。
> **这就是 Agent 和 Chain 的区别**：你没有写任何编排代码，是模型自己规划的。

---

## 6. 如何给 Agent 加"人设"和"规则"？

`create_react_agent` 默认用内置 prompt，你也可以自定义系统提示词：

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

custom_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是专业的餐厅顾问，回答简洁专业，只推荐真实存在的菜系。"),
    MessagesPlaceholder("messages"),   # 必须保留这个名字
])

agent = create_react_agent(llm, tools=[...], state_modifier=custom_prompt)
```

| 参数 | 作用 |
|------|------|
| `model` | 底层 LLM |
| `tools` | 可用工具列表 |
| `state_modifier` | 自定义系统提示词（人设/规则/约束） |
| `prompt` | 完全替换 prompt（更底层） |

---

## 7. Agent 的三种实现层次（面试必背）

| 层次 | 方式 | 特点 | 现状 |
|------|------|------|------|
| 低层 | 手动循环（第 06 篇的手工 tool calling） | 完全掌控，代码多 | 教学理解用 |
| 中层 | `AgentExecutor` + `create_tool_calling_agent` | 封装好，但黑盒 | 已过时，了解即可 |
| 高层 | **LangGraph `create_react_agent`** | 一行创建、可扩展、可持久化 | **现代标准** |

---

## 8. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 工具描述含糊 | Agent 不调用或反复调错工具 | 写好 docstring，说明"何时用" |
| 死循环 | Agent 反复调同一工具不停止 | 设 `max_iterations`、优化工具描述 |
| temperature 太高 | 工具调用不稳定 | Agent 场景用 temperature=0 |
| 忘了 `.content` | 打印出消息对象 | 取 `result["messages"][-1].content` |
| 工具出错 | Agent 拿到异常不知所措 | 工具内捕获异常返回友好信息 |

> 关于死循环：`create_react_agent` 可通过 `config={"recursion_limit": N}` 限制最大迭代次数。

---

## 9. 面试高频题

**Q1：Agent 和 Chain 的本质区别是什么？**
> A：Chain 的执行路径是预先写死的流水线；Agent 的执行路径由模型动态决定，模型在每步"思考"后
> 自主选择是否调用工具、调用哪个工具，形成"思考→行动→观察"的循环，直到任务完成。

**Q2：什么是 ReAct？它的三要素是什么？**
> A：ReAct 是 Reasoning + Acting 范式，Agent 循环执行 Thought（思考）、Action（行动/调工具）、
> Observation（观察结果）三步，直到判断任务完成输出最终答案。现代实现中，思考与行动由模型的
> Tool Calling 能力承载。

**Q3：为什么现代实践推荐 LangGraph 的 `create_react_agent` 而不是 `AgentExecutor`？**
> A：`AgentExecutor` 把 ReAct 循环封装成黑盒，难以扩展自定义步骤、持久化和复杂控制流；
> LangGraph 用显式状态图构建 Agent，每一步可见可控，支持中断、持久化、多智能体，是官方主推方向。

**Q4：如何限制 Agent 的迭代次数防止死循环？**
> A：通过 `config={"recursion_limit": N}` 限制图的最大执行步数；同时优化工具描述、
> 设置 temperature=0、在工具内捕获异常，从根源上减少循环。

---

## 10. 练手题

1. 用 `create_react_agent` 做一个"计算器 + 翻译"智能体
2. 用 `stream_mode="values"` 观察 Agent 的完整思考轨迹
3. 自定义 `state_modifier` 给 Agent 加人设，测试行为变化
4. 写一个需要 3 步以上工具调用的复杂问题，验证多步推理
5. 故意把工具描述写模糊，观察 Agent 是否调错工具，再改好验证

---

👉 下一篇：[08 — LangGraph 状态图](08-langgraph状态图.md) · 返回总目录：[00-README](00-README.md)
