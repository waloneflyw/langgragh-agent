# 01 — LangChain 是什么 + LLM 调用

> 目标：理解 LangChain 的定位与生态结构，掌握**用 LangChain 调用任意 LLM** 的四种姿势（同步/异步/流式/批量），
> 并彻底搞懂"消息"这个贯穿全程的核心概念。

---

## 1. LangChain 到底解决了什么问题？

### 1.1 不用 LangChain 会怎样？

假设你要让 LLM 帮你写一个"翻译助手"，不用框架直接调 OpenAI SDK：

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxx")
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "你是翻译助手"},
              {"role": "user", "content": "翻译：你好"}],
)
print(resp.choices[0].message.content)
```

看起来也不难。但当需求升级——"翻译完还要校验格式、还要查字典、还要记住上下文、还要能调内部接口"——你会发现：

1. **换模型厂商**要改一堆代码（OpenAI / DeepSeek / 文心接口各不相同）
2. **提示词管理**散落在字符串里，难以复用和测试
3. **组合多个步骤**（翻译→校验→格式化）要自己写一堆胶水代码
4. **加工具、加记忆、加检索**每次都从零搭

**LangChain 的价值 = 一套统一的"接口标准" + 一套现成的"积木"。**

### 1.2 核心抽象：让一切变得可替换、可组合

```
LangChain 提供两个关键能力：

① 统一接口（可替换）：
   任何模型都通过同一个 ChatModel 接口调用
   OpenAI → ChatOpenAI
   DeepSeek → ChatOpenAI(base_url=...)   ← 同一个类！换厂商只改配置不改代码
   文心 → QianfanChatEndpoint
   本地 → ChatOllama

② 可组合（可拼装）：
   prompt | model | parser | retriever | tool ...
   每个环节都是一个 "Runnable"（可运行块），用 | 管道串起来（第 03 篇详解）
```

### 1.3 生态地图（面试常问）

```
                    ┌─────────────────────────────┐
                    │        你的智能体应用         │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────┬───────────┴───────────┬──────────────┐
        ▼              ▼                       ▼              ▼
   langchain      langgraph           langchain-openai   langchain-community
   (高级组件:     (状态图编排:          (模型接入)          (第三方集成:
    链/智能体/     多步/循环/            langchain-community  文档加载/向量库)
    记忆)         多智能体)
        │              │
        └──────┬───────┘
               ▼
        langchain-core   ← 地基：消息、Prompt、Runnable、工具、输出解析器
```

**一句话记住**：`langchain-core` 是地基（所有抽象），`langchain-openai` 负责连模型，
`langchain-community` 负责连外部系统，`langgraph` 负责编排流程，`langchain` 是聚合入口。

---

## 2. 最核心的概念：消息（Message）

在 LangChain 里，**与模型的每一次交流都是一串"消息"**。消息有三种，对应对话里的三种角色：

| 类 | 角色 | 含义 | 类比 |
|----|------|------|------|
| `SystemMessage` | system | 设定模型的"人设/规则" | 面试官开场："你今天是英语面试官" |
| `HumanMessage` | user | 用户说的话 | 应聘者的回答 |
| `AIMessage` | assistant | 模型说的话 | 面试官的反应 |

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage(content="你是一名严谨的 Python 面试官，只考基础语法。"),
    HumanMessage(content="请出一道题"),
    AIMessage(content="请说出 list 和 tuple 的区别。"),
    HumanMessage(content="list 可变，tuple 不可变。"),
]
```

> 🔑 **为什么消息这么重要？** 因为后面所有的组件——Prompt 模板、记忆、Agent 的思考轨迹——
> 本质上都是在**操作这一串消息**。现在把消息对象看熟，后面会轻松很多。

---

## 3. 调用模型的四种姿势

### 3.1 同步调用 `invoke`（最常用）

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

result = llm.invoke("用一句话介绍杭州")   # 传入字符串，自动当成 HumanMessage
print(type(result))      # <class 'langchain_core.messages.ai.AIMessage'>
print(result.content)    # 真正的文本在这里
```

**关键点**：`invoke` 返回的不是字符串，而是 `AIMessage` 对象，文本在 `.content` 里。
为什么返回对象？因为模型除了文本还会返回其他信息（见 3.5）。

### 3.2 流式调用 `stream`（打字机效果）

让输出像 ChatGPT 一样一个字一个字蹦出来，用户体验更好：

```python
for chunk in llm.stream("用 5 句话介绍大语言模型"):
    print(chunk.content, end="", flush=True)   # end="" 不换行
print()  # 最后换个行
```

原理：LLM 是逐 token 生成的，`stream` 每次吐一小块（chunk），边生成边显示。

### 3.3 批量调用 `batch`（一次处理多条）

```python
questions = ["1+1=?", "中国的首都是？", "写一句关于秋天的诗"]
results = llm.batch(questions)   # 内部会并发处理，比 for 循环快
for q, r in zip(questions, results):
    print(f"Q: {q}\nA: {r.content}\n")
```

### 3.4 异步调用 `ainvoke`（高并发场景）

Web 服务里要同时处理几百个请求时，用异步避免阻塞：

```python
import asyncio

async def main():
    result = await llm.ainvoke("异步调用测试")
    print(result.content)

asyncio.run(main())
```

> 四种姿势总结成一张表（**面试必背**）：

| 方法 | 场景 | 返回 |
|------|------|------|
| `invoke` | 普通单次调用 | 完整结果 |
| `stream` | 需要流式打字机效果 | 逐块迭代器 |
| `batch` | 一次处理多条输入 | 结果列表 |
| `ainvoke` / `astream` | 异步/高并发 | await 结果 |

> 🧠 更深一层：这四种方法**不只是模型的接口，而是所有 `Runnable` 的统一接口**。
> 后面你会看到 `chain.invoke()`、`agent.stream()`、`retriever.invoke()` 都是同一套——这就是 LangChain 最优雅的地方。

### 3.5 完整返回：拿到 token 用量等元信息

```python
result = llm.invoke("你好")
print(result.content)                 # 文本
print(result.response_metadata)       # 元信息：token 用量、模型名、finish_reason 等
```

```python
# 典型输出
{'token_usage': {'completion_tokens': 12, 'prompt_tokens': 8, 'total_tokens': 20},
 'model_name': 'gpt-4o-mini',
 'finish_reason': 'stop'}
```

`finish_reason` 的含义（面试可能问）：

| 值 | 含义 |
|----|------|
| `stop` | 正常结束（说完自然停） |
| `length` | 因 max_tokens 上限被截断 |
| `tool_calls` | 模型想调用工具了（第 06 篇重点） |

---

## 4. 控制模型行为的三个关键参数

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,     # ① 随机性
    max_tokens=500,      # ② 输出长度上限
    timeout=30,          # ③ 超时秒数
)
```

| 参数 | 作用 | 取值建议 |
|------|------|---------|
| `temperature` | 控制创造性：越低越稳定保守，越高越天马行空 | **做工具调用/结构化输出用 0**；写文案/创意用 0.7~1.0 |
| `max_tokens` | 限制输出最大 token 数，防止超长/超费钱 | 按需设置，问答 500、长文 2000 |
| `timeout` | 请求超时时间，防止服务卡死 | 生产环境必设，默认 600s 太长 |

> 🔑 **temperature=0 的行业共识**：凡是让模型做"逻辑严谨"的事——工具调用、结构化输出、代码生成、分类——
> 一律 `temperature=0`。因为此时你追求的是**稳定可复现**，而不是创意。这个细节面试很加分。

---

## 5. 完整可运行示例：一个迷你翻译助手

把本篇知识串起来，写一个带人设、带流式输出的翻译器：

```python
# 01_demo.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

messages = [
    SystemMessage(content="你是专业翻译，把用户输入翻译成英文，只输出译文，不要解释。"),
    HumanMessage(content="今天天气很好，我们去爬山吧。"),
]

for chunk in llm.stream(messages):          # 传入消息列表（而不是字符串）
    print(chunk.content, end="", flush=True)
print()
```

运行：

```bash
python 01_demo.py
# The weather is nice today, let's go hiking.
```

---

## 6. 常见坑与避坑指南

| 坑 | 现象 | 解决 |
|----|------|------|
| 忘了 `.content` | `print(result)` 打出 `content='...'` 的对象 | 用 `result.content` 取文本 |
| 直接打印流式 | 输出一堆对象地址 | 流式要 `chunk.content` 拼接 |
| temperature 乱设 | 工具调用/结构化输出不稳定 | 这类场景一律设 0 |
| 国内模型连不上 | 报 connection / 404 | 用 `base_url` 指向兼容接口（见 README） |
| 密钥硬编码 | 把 key 写死在代码里 | 用 `.env` + `load_dotenv()`，且 `.env` 进 `.gitignore` |

---

## 7. 面试高频题

**Q1：LangChain 的 `langchain-core`、`langchain-community`、`langchain-openai` 有什么区别？**
> A：`langchain-core` 是核心抽象层，定义了 Message、Prompt、Runnable、Tool 等所有基础接口；
> `langchain-openai` 负责接入 OpenAI 及 OpenAI 兼容模型；
> `langchain-community` 是社区维护的第三方集成（向量库、文档加载器等）；
> 拆分的目的是让核心层稳定、第三方集成快速迭代、避免一个包无限膨胀。

**Q2：`invoke` 返回的是什么？为什么不是纯字符串？**
> A：返回 `AIMessage` 对象。因为模型输出不仅有文本，还有 token 用量、结束原因（`finish_reason`）、
> 工具调用请求等元信息，需要用结构化对象承载，方便后续组件（如 Agent）读取和传递。

**Q3：`temperature` 参数是干什么的？工具调用场景应该设多少？为什么？**
> A：控制采样的随机性，值越大输出越随机。工具调用/结构化输出场景应设 0，因为要追求稳定可复现，
> 避免模型每次输出格式不一致导致解析失败。

**Q4：如何在代码里切换不同的模型厂商而不改业务逻辑？**
> A：LangChain 用统一的 ChatModel 接口抽象了模型。切换厂商只换实现类或配置
> （如 `ChatOpenAI` 换 `base_url` 接 DeepSeek，或换 `QianfanChatEndpoint` 接文心），
> 业务代码中的 `invoke/stream` 调用保持不变。

---

## 8. 练手题

1. 写一个"英语老师"助手：用 `SystemMessage` 设定人设，让它指出你句子里的语法错误
2. 用 `stream` 实现一个命令行聊天循环（`while True: input()` → 流式打印回复 → 继续）
3. 用 `batch` 同时翻译 5 句中文，打印对照表
4. 分别用 `temperature=0` 和 `temperature=1.5` 让模型"想 3 个创业点子"，对比稳定性差异
5. 打印一次调用的 `response_metadata`，找出 `total_tokens`，理解成本从哪里来

---

👉 下一篇：[02 — Prompt 模板与输出解析](02-prompt模板与输出解析.md) · 返回总目录：[00-README](00-README.md)
