# 06 — Tools 工具定义与调用

> 目标：掌握**工具（Tool）**的定义与调用机制。这是从"会说话的模型"迈向"能做事的智能体"的分水岭。
> 本篇文章本身不构成 Agent，但它是 Agent 的"手脚"——先学会造工具，下一篇才能让 Agent 用工具。

---

## 1. 为什么 LLM 需要工具？

LLM 只会生成文本，**不会算数、不会查库、不会调接口、不会写文件**。但现实任务需要这些能力。

**工具（Tool）= 一个可被 LLM 调用的函数**，它有清晰的"输入格式说明"，让模型知道"什么场景该调用它、要传什么参数"。

```
没有工具：   "北京今天天气怎么样？" → LLM 只能瞎编
有了工具：   "北京今天天气怎么样？" → LLM 决定调用 get_weather("北京") → 拿到真实数据 → 组织语言回答
```

---

## 2. 用 @tool 装饰器定义工具（最推荐）

```python
from langchain_core.tools import tool

# 一个普通函数 + @tool 装饰器 = 一个工具
@tool
def add(a: int, b: int) -> int:
    """计算两个整数的和。"""
    return a + b
```

**关键点**：
- **函数名** = 工具名（`add`）
- **docstring（文档字符串）= 工具描述**（模型靠它判断何时调用！）
- **类型注解** = 参数类型说明（模型靠它生成正确的参数！）

查看工具"自我介绍"（这决定了模型会不会正确用它）：

```python
print(add.name)          # add
print(add.description)   # 计算两个整数的和。
print(add.args)          # {'a': {...'type': 'integer'}, 'b': {...}}
```

> 🔑 **工具三要素（面试必背）**：`name`（名字）、`description`（用途描述）、`args_schema`（参数结构）。
> 描述写得好不好，直接决定模型能否正确调用工具——这本质上是"用 docstring 写提示词"。

---

## 3. 工具的三种定义方式

| 方式 | 特点 | 适用 |
|------|------|------|
| `@tool` 装饰器 | 最简洁，自动推断 schema | **日常首选** |
| `StructuredTool.from_function` | 手动指定参数结构 | 需要精确控制参数 |
| 继承 `BaseTool` 类 | 完全自定义 | 复杂工具、需自定义行为 |

### 3.1 StructuredTool：手动指定参数（比 @tool 更可控）

当参数结构复杂，或想显式描述每个参数时：

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# 先定义参数结构
class WeatherInput(BaseModel):
    city: str = Field(description="城市名称，如 北京")

def get_weather(city: str) -> str:
    """查询指定城市的实时天气。"""
    return f"{city}：晴，25℃"   # 实际应接天气API，这里模拟

weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description="查询指定城市的实时天气",
    args_schema=WeatherInput,
)
```

### 3.2 常用参数类型（Pydantic 类型一览）

工具参数本质是 Pydantic schema，类型越明确，模型传参越准：

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class SearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词")
    top_k: int = Field(default=5, description="返回条数，默认5")
    sort_by: Literal["时间", "相关度"] = Field(default="相关度", description="排序方式")
    lang: Optional[str] = Field(default=None, description="语言，可空")
```

---

## 4. 工具的"调用"和"结果"怎么传递？

工具自己不会动，需要两样东西配合：

### 4.1 手动调用工具（理解底层）

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """两个整数相加。"""
    return a + b

# 方式一：直接调用
print(add.invoke({"a": 1, "b": 2}))      # 返回 ToolMessage

# 方式二：像函数一样调用
print(add(1, 2))                          # 返回 3（纯结果）
```

### 4.2 工具调用后返回的是 ToolMessage

```python
result = add.invoke({"a": 1, "b": 2})
print(type(result))       # <class 'langchain_core.messages.tool.ToolMessage'>
print(result.content)     # '3'（注意是字符串）
print(result.tool_call_id)  # 工具调用的唯一ID（把结果和请求对应起来）
```

> 🔑 **`ToolMessage` 是工具调用的"回执"**：它把工具执行结果带回给模型。
> 完整闭环是：模型发起 `tool_calls` → 程序执行工具 → 返回 `ToolMessage` → 模型读结果继续生成。

---

## 5. 工具调用（Tool Calling）的完整原理

现代模型（GPT-4、DeepSeek 等）原生支持 **Function/Tool Calling**：模型不会真的执行函数，而是**"请求"你执行**。

```
① 你把工具列表（name+description+参数）告诉模型
② 模型判断"这个问题需要调工具"，输出一个 tool_calls 请求（含工具名和参数）
③ 你的程序解析这个请求，真正去执行函数
④ 把执行结果（ToolMessage）回传给模型
⑤ 模型读结果，生成最终的自然语言回答
```

用代码演示这个"手工循环"（**看懂这个，就懂了 Agent 的底层**）：

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@tool
def add(a: int, b: int) -> int:
    """两个整数相加。"""
    return a + b

# ① 把工具"绑定"到模型上
llm_with_tools = llm.bind_tools([add])

# ② 模型收到问题，判断需要调工具，输出 tool_calls 请求
response = llm_with_tools.invoke([HumanMessage(content="请帮我算 123 + 456")])
print("模型是否请求调工具？", response.tool_calls)
# 输出类似：[{'name': 'add', 'args': {'a': 123, 'b': 456}, 'id': 'call_xxx'}]

# ③ 解析请求，真正执行工具
tool_call = response.tool_calls[0]
result = add.invoke(tool_call["args"])   # 执行真正的加法
print("工具结果：", result.content)       # '579'

# ④ 把结果回传给模型，让它总结成自然语言
final = llm_with_tools.invoke([
    HumanMessage(content="请帮我算 123 + 456"),
    response,                            # 模型之前的 tool_calls
    result,                              # 工具返回的 ToolMessage
])
print(final.content)                     # "123 + 456 = 579"
```

> 🎯 **这段代码是 Agent 的心脏**。第 07 篇的 Agent，本质就是把这个"模型请求→执行工具→回传结果→再问模型"
> 的循环**自动化**了，并加上"判断何时停止"的逻辑。

---

## 6. bind_tools 关键点

```python
llm.bind_tools([tool1, tool2], tool_choice="auto")
```

| 参数 | 含义 |
|------|------|
| `[tool1, tool2]` | 告诉模型有哪些工具可用 |
| `tool_choice="auto"` | 模型自己决定要不要用、用哪个（默认） |
| `tool_choice="any"` | 强制模型必须调工具 |
| `tool_choice="none"` | 禁止调工具 |

---

## 7. 完整示例：给模型装三个"手脚"

```python
# 06_demo.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

load_dotenv()

@tool
def add(a: int, b: int) -> int:
    """计算两个整数的和，用于加法运算。"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """计算两个整数的积，用于乘法运算。"""
    return a * b

@tool
def get_weather(city: str) -> str:
    """查询指定城市的实时天气。"""
    return f"{city}今天晴，25℃"

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools([add, multiply, get_weather])

# 三个不同类型的问题，观察模型如何"选择"工具
for q in ["3乘以7等于多少", "深圳天气怎么样", "给我讲个笑话"]:
    resp = llm_with_tools.invoke([HumanMessage(content=q)])
    if resp.tool_calls:
        for tc in resp.tool_calls:
            print(f"问题「{q}」→ 模型选择工具「{tc['name']}」参数 {tc['args']}")
    else:
        print(f"问题「{q}」→ 模型不用工具，直接回答")
```

运行后你会看到：乘法问题选 `multiply`，天气问题选 `get_weather`，讲笑话则不用工具——**模型会"自己挑工具"**。

---

## 8. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| docstring 写得含糊 | 模型不调用或乱调工具 | 写清楚"何时用、干什么" |
| 参数类型没注解 | 模型传参错误 | 用 Pydantic 明确类型和 `description` |
| 忘 `bind_tools` | 模型不知道有工具 | 先 `llm.bind_tools([...])` |
| 工具报错未捕获 | Agent 崩溃 | 工具内部 `try/except`，出错返回友好信息 |
| 工具结果没回传 | 模型答非所问 | 把 `ToolMessage` 追加回消息列表 |

---

## 9. 面试高频题

**Q1：什么是工具（Tool）？它的三要素是什么？**
> A：工具是 LLM 可调用的函数，让模型能执行真实操作。三要素是 `name`（名字）、
> `description`（用途描述，模型据此判断何时调用）、`args_schema`（参数结构，模型据此生成参数）。

**Q2：`@tool` 装饰器定义工具时，docstring 和类型注解起什么作用？**
> A：docstring 自动成为工具的 description，告诉模型工具的用途；类型注解自动生成 args_schema，
> 告诉模型参数的类型和含义。两者共同决定模型能否正确调用。

**Q3：什么是 Function/Tool Calling？模型会真的执行函数吗？**
> A：Tool Calling 是模型的特殊能力：它不真正执行函数，而是输出一个结构化的 `tool_calls` 请求
> （含工具名和参数）。由**程序**解析请求并真正执行函数，再把结果（`ToolMessage`）回传，模型据此继续生成。

**Q4：`bind_tools` 的 `tool_choice` 参数有哪些取值？**
> A：`auto`（默认，模型自行决定是否调用）、`any`（强制必须调用）、`none`（禁止调用）。

---

## 10. 练手题

1. 用 `@tool` 定义一个"翻译"工具，观察它的 `name`/`description`/`args`
2. 用 `StructuredTool.from_function` 定义一个带 `Literal` 枚举参数的工具
3. 手工完成一次完整的工具调用闭环（模型请求→执行→回传→总结）
4. 定义 3 个工具，用不同问题测试模型是否选对工具
5. 给工具加 `try/except`，让它出错时返回"查询失败"而不是抛异常

---

👉 下一篇：[07 — Agent 智能体核心](07-agent智能体核心.md) · 返回总目录：[00-README](00-README.md)
