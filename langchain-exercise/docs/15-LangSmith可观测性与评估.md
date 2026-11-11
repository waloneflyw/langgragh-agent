# 15 — LangSmith：LLM 应用的可观测性与评估

> 目标：掌握 **LangSmith**——LangChain 官方的可观测性/评估平台。学完你能给智能体装上「行车记录仪」（追踪每一步）、
> 用「质检流水线」（数据集 + 评估器）量化它的好坏，而不是拍脑袋说「我觉得它还行」。
> 这是把智能体从「能跑」推进到「可信、可上线」的关键一步。

---

## 1. 一句话理解 LangSmith：行车记录仪 + 质检流水线

LLM 应用和传统软件最大的不同：**它是个黑盒**。传统代码出错能打断点、看日志；LLM 应用出错时，
你面对的是「一段 prompt → 一堆 token → 一段回答」，中间发生了什么、为什么答错了，完全看不见。

LangSmith 做两件事：

| 能力 | 类比 | 解决什么 |
|------|------|---------|
| **追踪（Tracing）** | 行车记录仪 | 记录一次请求里每一步（LLM 调用、工具调用、检索）的输入输出、耗时、token |
| **评估（Evaluation）** | 质检流水线 | 用数据集 + 评估器，离线、可重复地给应用打分 |

> 🔑 一个专业智能体工程师的标配：**先追踪定位问题，再评估量化质量，然后迭代。** LangSmith 把这两件事串起来了。

---

## 2. 为什么需要：LLM 应用开发的三大痛点

1. **不可见**：一次回答可能经过 5 次 LLM 调用 + 3 次工具调用，中间哪一步错了看不到。
2. **不可量化**：改了 prompt 是变好了还是变差了？没指标就只能凭感觉。
3. **不可复现**：同一个问题，模型输出不稳定，没法「回归测试」。

LangSmith 分别用 **Trace / Dataset+Experiment / Dataset 版本化** 解决这三点。

---

## 3. 快速开始：三行环境变量 + 自动追踪

> ⚠️ 前提：需要一个 LangSmith 账号和 API Key（`lsv2_...`），在 smith.langchain.com 免费注册获取。
> 国内访问可能需要网络条件；本节的机制理解不受影响。

在 `.env` 里加：

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_你的key
LANGSMITH_PROJECT=my-agent
```

只要这三行就位，**你现有的 LangChain 代码不用改一行，调用会自动被追踪**：

```python
from dotenv import load_dotenv
load_dotenv()   # 关键：要在导入其他模块前就读到环境变量

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="deepseek-v4-pro", base_url="https://api.deepseek.com", ...)

print(llm.invoke("1+1=？").content)
# 跑完去 LangSmith 网页，就能看到这次调用的 Trace
```

> 🔑 第一个常见坑就在这：**`LANGSMITH_TRACING` 必须在导入模块之前设置**。否则那部分模块的调用不会被追踪。

---

## 4. 手动追踪：@traceable 装饰器

自动追踪只能覆盖 LangChain 内部调用；你自己写的业务函数，用 `@traceable` 装饰即可：

```python
import os
from langsmith import traceable
from langchain_openai import ChatOpenAI

@traceable(run_type="chain", name="回答问题")   # 给这段逻辑起个名，方便在 Trace 里找
def 回答问题(question: str) -> str:
    llm = ChatOpenAI(model="deepseek-v4-pro", base_url="https://api.deepseek.com",
                     api_key=os.getenv("DEEPSEEK_API_KEY"))
    return llm.invoke(question).content

print(回答问题("中国首都是哪？"))
```

- `@traceable` 会自动记录函数的输入、输出、耗时、异常；
- **嵌套调用会自动建立父子关系**（靠 Python 的 contextvars，不用手动传 parent）；
- 想给 LLM 厂商 SDK「零改动」追踪，还可用 `wrap_openai()` / `wrap_anthropic()` 包装器。

---

## 5. 核心概念（背下来，面试常考）

| 概念 | 是什么 |
|------|--------|
| **Run** | 一次单独操作（一次 LLM 调用 / 一次工具调用），是最小单元 |
| **Trace** | 同一次请求里所有 Run 串成的树，用 `trace_id` 关联 |
| **Thread** | 一段对话里的多次 Trace，用 `thread_id` 关联 |
| **Project** | 一组相关 Trace 的容器（`LANGSMITH_PROJECT`） |
| **Dataset** | 一组 `{inputs, outputs}` 例子，用于离线评估 |
| **Experiment** | 对某个 Dataset 跑一次 `evaluate()` 得到的结果集 |
| **Feedback** | 挂在 Run 上的评分/标签（数值、分类、自由文本） |

> 心智模型：**Run 是树叶，Trace 是树，Project 是森林，Dataset 是考试卷，Experiment 是一次考试，Feedback 是打分。**

---

## 6. 用数据集 + evaluate() 做离线评估

评估三步：**建数据集 → 写评估器 → 跑 evaluate**。

**① 建数据集（考试卷）：**

```python
from langsmith import Client

client = Client()
dataset = client.create_dataset("问答评估")
client.create_examples(
    dataset_id=dataset.id,
    examples=[
        {"inputs": {"question": "1+1等于几？"}, "outputs": {"answer": "2"}},
        {"inputs": {"question": "中国首都是哪？"}, "outputs": {"answer": "北京"}},
    ],
)
```

**② 写评估器（阅卷）：**

```python
def 答案正确(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    # inputs 是数据集里给的输入；outputs 是应用返回的；reference_outputs 是标准答案
    return outputs.get("answer") == reference_outputs.get("answer")
```

**③ 跑评估（考试）：**

```python
from langsmith import evaluate

results = evaluate(
    回答问题,               # 你的应用函数（第 4 节的 @traceable 函数）
    data="问答评估",        # 数据集名字
    evaluators=[答案正确],  # 评估器列表
)
print(results)   # 每个例子的分数汇总
```

> 🔑 最高频的坑：**评估器里 `outputs.get(...)` 的 key 必须和应用函数返回的 key 一致**。
> 应用返回字符串会被自动包成 `{"output": "..."}`，返回 dict 就用 dict 的 key——key 对不上会得到一堆「假 0 分」。

---

## 7. LLM-as-judge：让 LLM 当评委

精确匹配只能评「对错」，评不了「好坏」。开放题（总结、翻译、写作）要用 **LLM 当评委**：

```python
from langchain_openai import ChatOpenAI

def 质量评委(inputs: dict, outputs: dict) -> bool:
    裁判 = ChatOpenAI(model="deepseek-v4-pro", base_url="https://api.deepseek.com", ...)
    # 让裁判模型读「问题 + 回答」，判断质量是否过关，返回 True/False 或分数
    评判 = 裁判.invoke(
        f"问题：{inputs['question']}\n回答：{outputs['output']}\n回答是否准确、通顺？只回答是/否"
    ).content
    return "是" in 评判
```

或直接用现成的 `openevals` 库，一行拿到常见裁判：

```python
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT

正确性裁判 = create_llm_as_judge(prompt=CORRECTNESS_PROMPT, model="openai:o3-mini", feedback_key="correctness")
results = client.evaluate(回答问题, data="问答评估", evaluators=[正确性裁判])
```

> 评估器可以是返回 `bool`/`数字`/`字符串`/`dict` 的任何函数；签名支持 `(inputs, outputs)` 或
> `(inputs, outputs, reference_outputs)`。

---

## 8. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| `LANGSMITH_TRACING` 设晚了 | 部分/全部调用不出现 | 在导入模块前就 `load_dotenv()` |
| 评估器 key 对不上 | 一堆「假 0 分」 | 让评估器 `outputs.get(...)` 的 key 和应用返回一致 |
| 进程退出太快 | 最后一批 Trace 丢失 | 用 `atexit.register(client.flush)` 或优雅退出 |
| 跨线程/`asyncio.create_task` 丢失上下文 | 父子 Trace 树断裂 | 用 SDK 提供的上下文传播方式，别裸用线程池 |
| 把评估当一次性 | 改一次 prompt 就重新「凭感觉」 | 建立 Dataset，每次改动都跑 `evaluate` 对比 Experiment |

---

## 9. 面试高频题

**Q1：LangSmith 是什么？解决什么问题？**
> A：LangChain 官方的可观测性/评估平台，用追踪（Tracing）解决 LLM 应用「黑盒不可见」，
> 用数据集 + 评估器（Evaluation）解决「不可量化、不可复现」。

**Q2：Run / Trace / Project / Dataset 的关系？**
> A：Run 是单次操作，Trace 是同请求的 Run 树，Project 是 Trace 容器，Dataset 是评估用的例子集。

**Q3：@traceable 装饰器的作用？**
> A：自动记录函数输入输出/耗时/异常，并靠 contextvars 自动建立嵌套父子 Trace，无需手动传 parent。

**Q4：怎么评估一个 LLM 应用？**
> A：建 Dataset（例子）→ 写评估器（精确匹配或 LLM-as-judge）→ `evaluate()` 跑出 Experiment；
> 每次改动都重跑，对比分数。

**Q5：什么是 LLM-as-judge？**
> A：用另一个 LLM 当评委，对开放式回答（总结/翻译/写作）评质量，返回分数或布尔值，替代无法精确匹配的场景。

---

## 10. 练手题

1. 配好三个环境变量，跑一个现有的 LangChain 调用，去网页确认 Trace 出现
2. 用 `@traceable` 包一个自己的多步函数，观察父子 Run 的结构
3. 建一个 5 条例子的 Dataset，写一个精确匹配评估器，跑一次 `evaluate`
4. 写一个 LLM-as-judge 评估器，评「回答是否礼貌」，观察分数分布
5. 改一下 prompt，重新 `evaluate`，对比两次 Experiment 的分数变化

---

👉 上一篇：[14 — A2A 智能体互联协议](14-A2A智能体互联协议.md) · 返回总目录：[00-README](00-README.md)
