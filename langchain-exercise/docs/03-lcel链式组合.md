# 03 — LCEL 链式组合（LangChain Expression Language）

> 目标：掌握 LangChain 最核心的编程范式 **LCEL**——用 `|` 管道把提示词、模型、解析器、函数等
> 任意组合成"链"。这是理解后面 RAG、Agent、LangGraph 的**必经之路**，也是面试高频考点。

---

## 1. LCEL 是什么？

**LCEL（LangChain Expression Language）** 是 LangChain 提出的**组合式编程语法**。
核心思想一句话：

> **每个环节都是一个 `Runnable`（可运行块），用 `|`（管道）把它们串起来。**

你已经在前两篇用过了：

```python
chain = prompt | llm | parser   # 提示词 → 模型 → 解析
```

- `|` 相当于"把左边的结果传给右边"
- 组合出来的 `chain` 本身**也是一个 Runnable**，所以可以继续组合
- 每个 Runnable 都有统一的 `invoke / stream / batch / ainvoke` 接口

这就像 Vue 里的"组件化"：`prompt`、`llm`、`parser` 是三个组件，`|` 是把它们拼起来的模板语法。

---

## 2. Runnable 是什么？为什么这么重要？

### 2.1 Runnable 是"统一接口"

不管底层是模型、提示词、函数还是检索器，只要实现了 `Runnable` 接口，就能：

```python
runnable.invoke(输入)    # 同步执行
runnable.stream(输入)    # 流式
runnable.batch([...])    # 批量
runnable.ainvoke(输入)   # 异步
```

**这就是 LangChain 的灵魂设计**：接口统一 → 万物可组合 → 复杂流程也能用简单语法表达。

### 2.2 三种最重要的 Runnable

| 类 | 作用 | 类比 |
|----|------|------|
| `RunnableLambda` | 把普通函数包装成 Runnable | 一个"纯函数"组件 |
| `RunnableParallel` | 并行执行多个 Runnable | 一个"并发"容器 |
| `RunnablePassthrough` | 原样透传数据（不改动） | 一个"直通管道" |

---

## 3. RunnableLambda：把函数变成链上的一环

普通 Python 函数不能直接用 `|` 串，需要 `RunnableLambda` 包装：

```python
from langchain_core.runnables import RunnableLambda

# 普通函数
def 转大写(text: str) -> str:
    return text.upper()

# 包装成 Runnable
upper = RunnableLambda(转大写)

# 现在可以参与组合了
chain = upper | upper   # 转两次大写（其实是幂等，演示用）
print(chain.invoke("hello"))   # HELLO
```

**最常用的场景**：在模型输出之后，接一个函数做后处理。

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_messages([("human", "写一句关于 {topic} 的话")])

def 取前20字(msg):
    return msg.content[:20] + "..."

chain = prompt | llm | RunnableLambda(取前20字)   # 模型 → 截断

print(chain.invoke({"topic": "人工智能"}))
```

> 💡 也可以直接传函数，LangChain 会自动包装，但**显式写 `RunnableLambda` 更清晰**（面试也显得专业）。

### 3.1 用 lambda 快速写内联逻辑

```python
chain = prompt | llm | RunnableLambda(lambda msg: msg.content.upper())
```

---

## 4. RunnableParallel：并行执行，合并结果

当多个步骤**互相独立**时，可以并行跑，最后把结果合并成一个 dict：

```python
from langchain_core.runnables import RunnableParallel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 两个独立的任务
写标题 = ChatPromptTemplate.from_messages([("human", "给关于{topic}的文章起个标题")]) | llm
写摘要 = ChatPromptTemplate.from_messages([("human", "给关于{topic}的文章写句摘要")]) | llm

# 并行执行，结果是一个 dict，key 是字段名
parallel = RunnableParallel(标题=写标题, 摘要=写摘要)

result = parallel.invoke({"topic": "量子计算"})
print(result["标题"].content)
print(result["摘要"].content)
```

```
执行流程（两条线同时跑，省时间）：

        ┌→ 写标题 ─┐
 input ─┤           ├→ {"标题": ..., "摘要": ...}
        └→ 写摘要 ─┘
```

> 🎯 **为什么重要？** 后面做 RAG 时，"改写问题"和"检索"经常并行；做 Agent 时也常并行调用多个工具。
> `RunnableParallel` 就是那个"分叉再汇合"的开关。

---

## 5. RunnablePassthrough：数据透传

有些环节你希望**数据原样穿过**，同时还附带一点额外数据。`RunnablePassthrough` 就是"直通管道"：

```python
from langchain_core.runnables import RunnablePassthrough

# 场景：你想让 prompt 同时拿到"原始问题"和"处理后的上下文"
chain = (
    {"原始问题": RunnablePassthrough(), "处理后": 处理函数}   # dict 形式=自动并行
    | prompt
    | llm
)
```

三个常见用法：

```python
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

# ① 完全透传
RunnablePassthrough().invoke("hello")        # 返回 "hello"

# ② 透传时附带数据
RunnablePassthrough.assign(长度=len).invoke("hello")   # 返回 "hello"（并带属性）

# ③ 只取 dict 的某个 key（配合 itemgetter，超常用）
chain = RunnablePassthrough.assign(x=itemgetter("a"))
chain.invoke({"a": 1, "b": 2})   # x 取到 1
```

> `itemgetter("a")` 是 Python 标准库函数，作用是"从 dict 里取 key 为 a 的值"。
> 在 LCEL 里常用来**从输入里挑选字段传给下游**。

---

## 6. 组合套路大全

### 6.1 最常见的链：prompt → model → output

```python
chain = prompt | llm | StrOutputParser()
```

### 6.2 数据预处理后再进模型（dict 分叉）

```python
chain = (
    {"topic": itemgetter("topic"), "time": RunnableLambda(取当前时间)}  # 分叉收集数据
    | prompt
    | llm
    | StrOutputParser()
)
```

### 6.3 模型输出后做多路后处理

```python
chain = prompt | llm | RunnableParallel(原文=RunnablePassthrough(), 大写=RunnableLambda(lambda m: m.content.upper()))
```

---

## 7. 串起来看一个完整例子：中文周报生成器

输入一个项目名，并行生成"标题"和"内容"，再合成一篇周报：

```python
# 03_demo.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

写标题 = ChatPromptTemplate.from_messages([("human", "为「{项目}」本周工作写一个8字以内的标题，只输出标题")]) | llm | StrOutputParser()
写内容 = ChatPromptTemplate.from_messages([("human", "为「{项目}」本周工作写3条进展要点，每条一行")]) | llm | StrOutputParser()

# 并行生成标题和内容，再合并成周报
周报 = (
    RunnableParallel(标题=写标题, 内容=写内容)
    | RunnableLambda(lambda d: f"## {d['标题']}\n{d['内容']}")
)

print(周报.invoke({"项目": "智能客服系统"}))
```

运行后你会得到一篇结构清晰的周报。**注意体会**：整个流程没有一行 `if/for` 胶水代码，全靠管道拼出来。

---

## 8. LCEL 的核心优势（面试必背）

| 优势 | 说明 |
|------|------|
| **统一接口** | 所有 Runnable 都是 `invoke/stream/batch/ainvoke`，切换实现零成本 |
| **自动流式** | 链上任意一环支持流式，整条链就支持流式（不用自己管） |
| **自动异步** | 需要并发时，`ainvoke` 一行切换 |
| **自动批量** | `batch` 内部自动并行 |
| **可观测** | 每个环节可挂日志/追踪（LangSmith），方便调试 |
| **可组合** | 链可以再组合成更大的链，像搭积木 |

---

## 9. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 用 `|` 串普通函数 | 报错 "not a Runnable" | 用 `RunnableLambda` 包装 |
| dict 里写错 key | 下游拿不到变量 | 检查 dict 的 key 和 prompt 占位符是否一致 |
| 忘了解析器 | 拿到 AIMessage 对象 | 结尾接 `StrOutputParser()` 或自定义解析 |
| 并行任务有依赖 | 结果错乱 | 有依赖的步骤不能并行，要串行（顺序排布） |

---

## 10. 面试高频题

**Q1：什么是 LCEL？它解决什么问题？**
> A：LCEL 是 LangChain 的组合式编程语法，核心是把每个环节抽象成 `Runnable`，用 `|` 管道连接。
> 它让提示词、模型、解析器、函数、检索器能像积木一样组合，且统一了 `invoke/stream/batch` 接口，
> 自动获得流式、异步、批量能力，极大减少胶水代码。

**Q2：`RunnableParallel` 和 `RunnablePassthrough` 分别有什么作用？**
> A：`RunnableParallel` 并行执行多个独立任务并把结果合并成 dict，用于无依赖步骤的并发；
> `RunnablePassthrough` 让数据原样穿过，常用于在链中透传原始输入或给下游补充字段。

**Q3：一个 Runnable 有哪些统一的调用方式？**
> A：`invoke`（同步单次）、`stream`（流式）、`batch`（批量并发）、`ainvoke/astream`（异步）。
> 任何 Runnable（含组合出的链）都支持这几种，这是 LangChain 可组合性的基础。

**Q4：如何把一个普通的 Python 函数接入到链里？**
> A：用 `RunnableLambda` 包装，使其实现 Runnable 接口，之后就能用 `|` 和其他环节组合。

---

## 11. 练手题

1. 写一条链：输入一句话 → 模型翻译成英文 → `RunnableLambda` 统计字数
2. 用 `RunnableParallel` 同时让模型写"优点"和"缺点"，合并输出
3. 用 `itemgetter` 从 `{"name": ..., "age": ...}` 中只取 name 传给 prompt
4. 把第 7 节的周报生成器改成流式输出（`.stream`）
5. 组合一条 5 个环节的链，并画出它的数据流向图

---

👉 下一篇：[04 — RAG 检索增强生成](04-rag检索增强生成.md) · 返回总目录：[00-README](00-README.md)
