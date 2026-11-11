# 02 — Prompt 模板与输出解析

> 目标：掌握**提示词模板**（把 prompt 变成可复用、可传参的组件），
> 和**输出解析器**（让 LLM 稳定输出结构化数据，而不是自由文本）。
> 这两样是后面所有智能体的地基——Agent 的每一步，本质都是"填模板 → 调模型 → 解析结果"。

---

## 1. 为什么需要 Prompt 模板？

看这段"朴素"代码的问题：

```python
name = "张三"
product = "洗衣机"
# 直接用 f-string 拼 prompt
prompt = f"你是销售，向{name}推荐{product}，写一段推销话术"
result = llm.invoke(prompt)
```

问题：
1. **不可复用**：换个人名/产品，逻辑和 prompt 混在一起
2. **不可测试**：没法单独验证 prompt 写得好不好
3. **容易出错**：手动拼字符串容易漏空格、漏引号

**模板 = 把 prompt 的"骨架"和"数据"分离**。骨架固定，数据动态填入：

```python
from langchain_core.prompts import ChatPromptTemplate

# 骨架：{name} 和 {product} 是"占位符"，像 Vue 模板里的 {{ name }}
template = ChatPromptTemplate.from_messages([
    ("system", "你是销售，向客户推荐产品，语气热情专业。"),
    ("human", "客户叫{name}，请向他推荐{product}，写一段推销话术。"),
])

# 填入数据
prompt_value = template.invoke({"name": "张三", "product": "洗衣机"})
print(prompt_value)   # 变成了一串完整的消息
```

---

## 2. PromptTemplate vs ChatPromptTemplate

LangChain 有**两类**模板，分别对应两类模型（旧/新）：

| 类 | 用于 | 结果 | 何时用 |
|----|------|------|--------|
| `PromptTemplate` | 旧版文本模型 | 一段纯文本 | 基本不用了，了解即可 |
| `ChatPromptTemplate` | 现代对话模型 | 一串消息 | **日常全部用这个** |

```python
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

# ① 文本模板 → 返回字符串
pt = PromptTemplate.from_template("把 {word} 翻译成英文")
print(pt.invoke({"word": "苹果"}).text)     # .text 是字符串

# ② 对话模板 → 返回消息列表
ct = ChatPromptTemplate.from_messages([
    ("system", "你是翻译"),
    ("human", "把 {word} 翻译成英文"),
])
print(ct.invoke({"word": "苹果"}))           # 是一个 ChatPromptValue（消息列表）
```

> 🔑 面试被问"两者区别"：`PromptTemplate` 产出纯文本字符串，面向旧版补全类模型；
> `ChatPromptTemplate` 产出结构化消息列表，能区分 system/user/assistant 角色，面向现代对话模型。

---

## 3. ChatPromptTemplate 的三种写法

### 3.1 用元组（最常用，简洁）

```python
template = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}"),          # ("角色", "内容")
    ("human", "{input}"),                  # 元组第一项是角色
    ("ai", "好的，我是{role}"),            # "ai" 是 "assistant" 的简写
])
```

### 3.2 用消息类（更明确）

```python
from langchain_core.messages import SystemMessage, HumanMessage

template = ChatPromptTemplate.from_messages([
    SystemMessage(content="你是一个{role}"),
    HumanMessage(content="{input}"),
])
```

### 3.3 部分填充（先填一部分，剩下的后面填）

```python
template = ChatPromptTemplate.from_messages([
    ("system", "你是{role}，语气{tone}"),
    ("human", "{input}"),
])

# 先把 role 固定住，得到一个"半成品"模板
partial = template.partial(role="客服", tone="耐心")
# 之后只填剩下的 input
print(partial.invoke({"input": "我手机坏了"}))
```

> 部分填充的妙用：把"固定配置"（人设、风格）提前锁死，业务代码只关注"变化的部分"。

---

## 4. 占位符进阶：MessagesPlaceholder

如果模板里要插入**一整段已有的对话历史**（比如多轮聊天），普通 `{变量}` 不够用，
需要 `MessagesPlaceholder`：

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

template = ChatPromptTemplate.from_messages([
    ("system", "你是乐于助人的助手"),
    MessagesPlaceholder("history"),     # 这里会塞入一串历史消息
    ("human", "{question}"),
])

# 使用时传入一列消息对象
from langchain_core.messages import HumanMessage, AIMessage
template.invoke({
    "history": [
        HumanMessage(content="我叫小王"),
        AIMessage(content="你好小王！"),
    ],
    "question": "我叫什么？",
})
```

> 这是第 05 篇"对话记忆"的核心机制，先混个脸熟：**历史消息通过这个占位符注入**。

---

## 5. 输出解析器（Output Parser）：让 LLM 说"人话"之外的格式

### 5.1 问题：为什么需要解析器？

LLM 的输出是自由文本。但程序需要的是**结构化数据**。看这个尴尬：

```python
# 你希望拿到 JSON
result = llm.invoke("输出一个人的信息：姓名、年龄、城市")
# 实际输出可能长这样 ↓ 带了一堆废话，程序没法直接解析
# "好的，以下是信息：\n```json\n{\"name\": \"张三\", ...}\n```\n希望能帮到你"
```

输出解析器 = **在 prompt 里明确格式要求 + 自动把文本解析成 Python 对象**。

### 5.2 最常用的三种解析器

| 解析器 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `StrOutputParser` | 任意 | 纯字符串 | 只要文本 |
| `JsonOutputParser` | 要求 JSON | `dict` | 拿字典 |
| `PydanticOutputParser` | 按 schema 生成 | Pydantic 对象 | **拿强类型对象（最推荐）** |

### 5.3 PydanticOutputParser（重点，面试 + 工作必会）

用 `Pydantic` 定义一个"数据结构"，解析器会：①自动生成格式说明塞进 prompt；②把输出解析成对象。

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# ① 定义你想要的数据结构（类似 TypeScript 的 interface）
class Person(BaseModel):
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")
    city: str = Field(description="居住城市")
    hobbies: list[str] = Field(description="爱好列表")

# ② 创建解析器
parser = PydanticOutputParser(pydantic_object=Person)

# ③ 把解析器生成的"格式说明"注入 prompt（这是关键一步！）
template = ChatPromptTemplate.from_messages([
    ("system", "你负责从文本中抽取人物信息。\n{format_instructions}"),
    ("human", "请分析：{text}"),
])
# get_format_instructions() 会自动生成一段"请按如下JSON格式输出..."的说明
prompt = template.partial(format_instructions=parser.get_format_instructions())

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ④ 串起来执行
chain = prompt | llm | parser

result = chain.invoke({"text": "张三，今年30岁，住在杭州，喜欢打篮球和游泳"})

print(type(result))        # <class '__main__.Person'>
print(result.name)         # 张三（可以直接 .属性 访问！）
print(result.hobbies)      # ['打篮球', '游泳']
```

> 🎯 **这一步是全书最重要的模式之一，务必背下来**：
> `prompt | llm | parser` —— 提示词 → 模型 → 解析。这就是"链"的雏形，下一篇 LCEL 会正式展开。

### 5.4 JsonOutputParser（拿到 dict，轻量）

不需要定义 class，直接要 JSON：

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()

template = ChatPromptTemplate.from_messages([
    ("system", "输出 JSON，不要多余内容。{format_instructions}"),
    ("human", "{input}"),
]).partial(format_instructions=parser.get_format_instructions())

chain = template | llm | parser

result = chain.invoke({"input": "列出3种水果及价格"})
# result 就是一个 dict：{"水果": [{"名称": ..., "价格": ...}, ...]}
print(type(result), result)
```

### 5.5 三种解析器对比选择

```
只要一段文字          → StrOutputParser
要一个字典（简单）     → JsonOutputParser
要强类型对象（复杂业务） → PydanticOutputParser  ← 生产环境首选
```

---

## 6. 结构化输出还能更简单：with_structured_output

LangChain 还提供了更现代的写法，直接把 schema 绑到模型上（底层用 function calling，更稳定）：

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class Person(BaseModel):
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 一步到位：绑定结构化输出
structured_llm = llm.with_structured_output(Person)

result = structured_llm.invoke("张三今年30岁")
print(type(result))   # <class '__main__.Person'>
print(result.name, result.age)
```

**两种方式怎么选？**

| 方式 | 特点 | 适用 |
|------|------|------|
| `PydanticOutputParser` + 手动塞格式说明 | 你完全掌控 prompt，兼容所有模型 | 需要精细控制、兼容非 function-calling 模型 |
| `with_structured_output` | 简洁，底层走 function calling，更稳 | **优先用这个**，现代模型都支持 |

---

## 7. 完整示例：一个"简历信息抽取器"

综合运用：用 Pydantic 定义结构 → 抽取简历文本 → 得到结构化对象。

```python
# 02_demo.py
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

class Resume(BaseModel):
    name: str = Field(description="姓名")
    years_of_experience: int = Field(description="工作年限（年）")
    skills: List[str] = Field(description="技能列表")
    is_management: bool = Field(description="是否有管理经验")

parser = PydanticOutputParser(pydantic_object=Resume)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 HR 助理，从简历中抽取信息。\n{format_instructions}"),
    ("human", "简历内容：\n{text}"),
]).partial(format_instructions=parser.get_format_instructions())

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
chain = prompt | llm | parser

text = "李四，5年后端开发经验，精通 Python、Docker、MySQL，曾带领3人小组完成项目。"
resume = chain.invoke({"text": text})

print(f"姓名：{resume.name}")
print(f"年限：{resume.years_of_experience}年")
print(f"技能：{resume.skills}")
print(f"管理经验：{resume.is_management}")
```

---

## 8. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 忘了注入 `format_instructions` | 模型输出带废话/格式不对 | 一定要 `.partial(format_instructions=parser.get_format_instructions())` |
| temperature 设太高 | 每次格式都变，解析失败 | 结构化输出场景 temperature=0 |
| Pydantic 字段没写 description | 模型乱猜字段含义 | 每个字段都用 `Field(description=...)` 说明 |
| 解析失败直接崩 | 抛 `OutputParserException` | 生产中加 `with_retry` 或 `parser.with_retry()` |

---

## 9. 面试高频题

**Q1：`PromptTemplate` 和 `ChatPromptTemplate` 有什么区别？**
> A：前者生成纯文本字符串，面向旧版补全模型；后者生成结构化的消息列表，能区分 system/user/assistant
> 三种角色，是现代对话模型的标准用法。

**Q2：输出解析器解决了什么问题？如何让 LLM 稳定输出 JSON？**
> A：LLM 输出是自由文本，可能带废话和 markdown 包裹，程序无法直接使用。解析器一方面通过
> `get_format_instructions()` 把格式要求写进 prompt，另一方面把模型的文本输出解析成 dict 或 Pydantic
> 对象。配合 `temperature=0` 可显著提升稳定性。更现代的做法是 `with_structured_output`，
> 底层用 function calling，稳定性更高。

**Q3：`PydanticOutputParser` 和 `with_structured_output` 怎么选？**
> A：`with_structured_output` 简洁、底层走 function calling，稳定性好，是现代模型首选；
> `PydanticOutputParser` 让你完全掌控 prompt 格式，兼容不支持 function calling 的模型，
> 需要精细定制 prompt 时使用。

**Q4：`MessagesPlaceholder` 是干什么的？**
> A：在模板中占位，用于动态注入一整段对话历史消息列表（如多轮对话的历史记录），
> 是构建记忆功能的关键机制。

---

## 10. 练手题

1. 定义一个 `Book` 结构（书名/作者/出版年份/评分），从一段书评文字中抽取
2. 用 `JsonOutputParser` 让模型分析一句话的情感，输出 `{"sentiment": "正面", "score": 0.9}`
3. 用 `MessagesPlaceholder` 写一个模板，传入 3 条历史消息后再提问
4. 对比 `temperature=0` 和 `temperature=1` 下结构化输出的成功率（各跑 5 次）
5. 用 `partial` 把"角色=美食评论家"锁死，做成一个只填菜名的模板

---

👉 下一篇：[03 — LCEL 链式组合](03-lcel链式组合.md) · 返回总目录：[00-README](00-README.md)
