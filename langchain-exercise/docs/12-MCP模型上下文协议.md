# 12 — MCP 模型上下文协议

> 目标：彻底搞懂 **MCP（Model Context Protocol，模型上下文协议）**——它是什么、为什么要学、怎么用代码把它
> 跑起来，以及如何灵活地把它接进 Claude Code 和 LangChain / LangGraph 里。
> 学完本篇，你就多了一项**跨模型、跨应用、可复用**的工具接入能力，面试和工作中都非常吃香。

---

## 1. 一句话理解 MCP：AI 的 "USB-C 接口"

先记住官方最爱用的一个比喻：

> **MCP 之于 AI 应用，就像 USB-C 之于电子设备。**

在没有 USB-C 之前，手机、硬盘、显示器、键盘各用各的接口，每接一个设备都要一根专用线。
MCP 要解决的问题一模一样：在 MCP 之前，你想让 AI 智能体调用一个工具（查数据库、调 API、读写文件），
**每接一个工具就要手写一套胶水代码**，而且这套代码还绑死了某个模型、某个框架，换一个就得重写。

MCP 的定义（能背下来最好）：

> MCP 是一个**开放标准协议**，它标准化了「AI 应用如何连接外部工具和数据源」这件事。
> 它把服务端的能力统一抽象成三类东西——**工具（Tools）、资源（Resources）、提示模板（Prompts）**，
> 让任何客户端都能用统一的方式**发现、加载、调用**它们。

三个关键词拆开理解：

| 关键词 | 含义 |
|--------|------|
| **Model** | 为「模型 / 智能体」服务，但协议本身**不绑定任何模型**（Claude、GPT、DeepSeek 都能用） |
| **Context** | 它的使命是给模型**喂上下文**——工具执行结果、数据、模板，本质都在补全模型的「知识缺口」 |
| **Protocol** | 它是一个**协议**（类似 HTTP、SQL），不是某个公司的私有功能，是开放的、跨厂商的 |

> 🔑 关键认知：MCP 是 **Anthropic 于 2024 年 11 月开源**的协议，随后开放治理、多厂商共建。
> 它解决的是「**连接**」这一层，和「模型有多聪明」是两码事——再强的模型，接不到工具也做不了事。

---

## 2. 为什么需要 MCP：N×M 问题 → N+M 问题

没有标准协议时，接入是**笛卡尔积爆炸**：

```
N 个 AI 应用  ×  M 个外部工具  =  N×M 套胶水代码

例如：Claude Code、你自己的 LangChain 应用、Claude Desktop（3 个应用）
      都要接 GitHub、数据库、文件系统、浏览器（4 个工具）
      → 要写 3 × 4 = 12 套对接代码，且彼此不通用
```

有了 MCP，就变成**加法**：

```
N 个 AI 应用  +  M 个工具，每个工具只需实现一次「MCP 服务端」
      → 任意应用通过「MCP 客户端」直接连接，共 N + M 个连接
```

这就是 MCP 最大的价值：**写一次、到处复用**。工具提供方专心实现协议，应用方专心做业务，
谁都不用关心对方内部怎么实现的。

---

## 3. 架构：Host / Client / Server 三者分工

MCP 架构是经典的**客户端-服务器**模型，但多了一个「宿主」角色，三个词别搞混：

```
┌─────────────────────────────────────────────┐
│  MCP Host（宿主：AI 应用本身）                │
│   例如：Claude Code / Claude Desktop / 你的 Agent │
│                                             │
│   ┌──────────────┐      ┌──────────────┐     │
│   │ MCP Client 1 │ ───▶ │ MCP Server A │     │   （1 个 Client 只连 1 个 Server）
│   ├──────────────┤      ├──────────────┤     │
│   │ MCP Client 2 │ ───▶ │ MCP Server B │     │
│   └──────────────┘      └──────────────┘     │
└─────────────────────────────────────────────┘
```

| 角色 | 是什么 | 谁来实现 | 举例 |
|------|--------|---------|------|
| **Host（宿主）** | 运行 LLM 的 AI 应用本身，负责发起「连接服务器」这件事 | AI 应用开发者 | Claude Code、Claude Desktop、你的 LangGraph 应用 |
| **Client（客户端）** | 宿主内部、与单个 Server 通信的组件（1 对 1） | 通常由 SDK 自动生成 | `MultiServerMCPClient` |
| **Server（服务端）** | 对外暴露工具/资源/模板的一方 | 工具提供方 | 一个 GitHub 服务器、一个数据库服务器 |

> 记住一句：**Host 里住着很多 Client，每个 Client 连一个 Server。**
> 你既可能写 Server（把自己的 API 变成 AI 能用的工具），也可能写 Client（让 AI 用别人的工具）。

---

## 4. 三大原语：Tools / Resources / Prompts

MCP Server 对外暴露的能力只有三类，这是整个协议的核心，务必分清「可执行」和「只读」的区别：

| 原语 | 中文 | 性质 | 谁能触发 | 类比 |
|------|------|------|---------|------|
| **Tools** | 工具 | **可执行**（有副作用） | 模型根据对话自主决定调用 | POST / 函数 |
| **Resources** | 资源 | **只读**（无副作用） | 客户端主动读取 | GET / 数据 |
| **Prompts** | 提示模板 | 可复用的文本模板 | 用户/客户端选择使用 | 模板函数 |

- **Tools（工具）**：模型可以「调用」的函数。例如 `add(a, b)`、`search(query)`、`create_issue(title)`。
  这是最常用、最重要的一个，是让 LLM 从「只会说话」变成「能做事」的关键。
- **Resources（资源）**：模型可以「读」的数据。例如一个文件内容、一条数据库记录、一份配置。
  它**只读、不能改**，因此更安全，适合暴露给模型做参考。
- **Prompts（提示模板）**：把一段常用提示封装起来复用。例如「代码审查」「生成周报」模板。

> 🔑 判断口诀：**「能改变世界的」是 Tool，「只给世界看的」是 Resource，「教模型怎么说话」的是 Prompt。**

---

## 5. 底层协议：JSON-RPC 与能力协商

MCP 底层跑在 **JSON-RPC 2.0** 上——就是「用 JSON 格式发请求、收响应」的远程调用协议。
理解它，你就明白了 MCP「原理」的全部。

一个典型的完整交互长这样：

```jsonc
// ① 初始化握手：双方互报能力（capability negotiation）
//    客户端 → 服务器
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},                 // 客户端声明自己支持什么
    "clientInfo": {"name": "claude-code", "version": "2.0.0"}
}}
//    服务器 → 客户端（回应自己的能力清单）
{"jsonrpc": "2.0", "id": 1, "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
    "serverInfo": {"name": "math-server", "version": "1.0.0"}
}}

// ② 发现：客户端问「你有哪些工具？」
{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
//    服务器列出每个工具的名字、描述、参数 JSON Schema
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{
    "name": "add",
    "description": "两个整数相加",
    "inputSchema": {"type": "object", "properties": {
        "a": {"type": "integer"}, "b": {"type": "integer"}
    }, "required": ["a", "b"]}
}]}}

// ③ 调用：模型决定要用哪个工具、传什么参数
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
    "name": "add", "arguments": {"a": 1, "b": 2}
}}
//    服务器执行后返回结果
{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "3"}]}}
```

三句话总结原理：

1. **先握手**：`initialize` 让双方知道「对方支持什么」，这叫**能力协商**。
2. **再发现**：`tools/list`、`resources/list`、`prompts/list` 让客户端自动得知服务器有什么。
3. **后调用**：`tools/call` 等把参数发过去，服务器执行并返回结果。

> 所以你**根本不需要手动写这些 JSON**——FastMCP 等 SDK 已经帮你封装好了。但面试时能讲出这三点，
> 说明你真的懂协议，而不是只会 `pip install`。

---

## 6. 传输方式：stdio / SSE / Streamable HTTP

MCP 消息通过什么「管道」传输，有三种，选对场景很重要：

| 传输方式 | 说明 | 适用场景 | 现状 |
|---------|------|---------|------|
| **stdio** | 把服务器作为**本地子进程**启动，通过标准输入/输出通信 | 本地开发、调试，Claude Code 最常用 | ✅ 主流 |
| **SSE** | 基于 HTTP 的 Server-Sent Events 单向流 | 早期远程方案 | ⚠️ 官方已不推荐 |
| **Streamable HTTP** | 2025 年新引入，基于 HTTP 的双向流式传输，可远程部署 | **生产远程部署的首选** | ✅ 2026 推荐 |

一句话决策：

> **本地玩用 stdio，上生产用 Streamable HTTP，SSE 是过去式别再用。**

后面第 7 节会演示 stdio 和 Streamable HTTP 两种跑法。

---

## 7. 上手：用 FastMCP 写第一个 Server

**`FastMCP`** 是官方 Python SDK 里的高层封装，风格极像 FastAPI——用装饰器就能把普通函数变成工具。

> ⚠️ **版本提示（重要，先读再装）**：
> - `mcp` 从 **2.0 起把 `FastMCP` 改名为 `MCPServer`**（`from mcp.server.mcpserver import MCPServer`）。
> - 但 **`langchain-mcp-adapters`（0.3.x）目前只支持 `mcp<2`**。本篇既要写 Server、又要接进 LangChain，
>   两者必须用**同一个 mcp 版本**，所以本教程统一锁 **mcp 1.x（FastMCP）**。
> - 只写 Server、不接 adapter 的话可升 v2，把 `FastMCP` 换成 `MCPServer` 即可。装包：

```bash
pip install "mcp>=1,<2"     # v1（本教程以此为准，配合 langchain-mcp-adapters）
# 只写 Server 才用 v2：pip install "mcp>=2,<3"
```

下面是一个**完整可运行**的 MCP Server，涵盖了三种原语，存成 `mcp_math_server.py`：

```python
# mcp_math_server.py —— 一个带工具/资源/提示模板的 MCP 服务器
from mcp.server.fastmcp import FastMCP   # mcp 1.x 导入（配合 langchain-mcp-adapters）

# ① 创建服务器实例（括号里是服务器名字）
mcp = FastMCP("数学工具服务器")


# ② 工具（Tool）：模型可调用的函数。类型注解会自动生成 JSON Schema，docstring 是描述
@mcp.tool()
def add(a: int, b: int) -> int:
    """两个整数相加"""
    return a + b


@mcp.tool()
def get_weather(city: str) -> str:
    """查询某个城市的天气（演示用假数据）"""
    return f"{city} 今天晴，25℃"


# ③ 资源（Resource）：模型可读取的只读数据。URI 前缀 + 名字
@mcp.resource("config://greeting")
def greeting() -> str:
    return "你好，我是 MCP 服务器"


# ④ 提示模板（Prompt）：可复用的提示词
@mcp.prompt()
def code_review(code: str) -> str:
    return f"请审查以下代码并给出改进建议：\n{code}"


# ⑤ 启动服务器
if __name__ == "__main__":
    # 方式一：stdio（本地子进程，Claude Code 默认）
    mcp.run()

    # 方式二：Streamable HTTP（生产远程部署，host/port 在构造时指定）
    # mcp = FastMCP("数学工具服务器", host="0.0.0.0", port=8001)
    # mcp.run(transport="streamable-http")   # 默认路径 /mcp
```

直接运行 `python mcp_math_server.py`，它会以 stdio 方式启动，等待客户端连接。
（stdio 服务器自己不会打印输出，这是正常的——它的「对话」走标准输入输出，不是给人类看的。）

**三个装饰器各自在做什么**，这是这套装饰器 API 的精髓：

| 装饰器 | 作用 | 生成什么 |
|--------|------|---------|
| `@mcp.tool()` | 把函数注册成**工具** | 用类型注解生成参数 JSON Schema，docstring 当描述 |
| `@mcp.resource("uri")` | 把函数注册成**资源** | 用 URI 定位、可被客户端读取 |
| `@mcp.prompt()` | 把函数注册成**提示模板** | 一个返回字符串/消息序列的模板 |

---

## 8. 两种使用模式：Claude Code 还是自己的应用

> 动手之前先想清楚一件事：**「Agent 跑在哪？」** 这决定了你走哪套流程。
> MCP 本地使用有两条**互斥**的路，很多人把它们混成一条线，结果卡在「到底要不要先跑 server」、
> 「`.mcp.json` 和 client 代码是什么关系」上。这一节先把这条线理清。

### 8.1 一张表看清两条路

| | 模式 A：给 Claude Code 用 | 模式 B：给自己的 LangChain 应用用 |
|---|---|---|
| 「Agent」是谁 | Claude Code 本身 | 你写的 Python（`create_agent`） |
| 谁来发现/加载工具 | Claude Code 内置 MCP 客户端 | 你代码里的 `MultiServerMCPClient` |
| 配置文件 | `.mcp.json` | 无（配置直接写在代码字典里） |
| 谁来启动 server | Claude Code 自动 spawn | `MultiServerMCPClient` 自动 spawn |

> 🔑 **`.mcp.json` 只在 Claude Code 里被读取**，你的 Python 程序根本不认识它；反过来 `MultiServerMCPClient`
> 只在你的代码里出现，Claude Code 不用它。所以「配置 `.mcp.json`」和「用 client 拿工具挂 agent」
> 是**两条路的步骤，不是同一条路的上下游**。

### 8.2 两条正确流程

**模式 A（Claude Code）——见下一节第 9 节：**

```
写 .mcp.json（声明 command + args）
   → 重启 Claude Code，它自动 spawn server（stdio 子进程）
   → 自动发现工具
   → 你在对话里直接说「用 math 算 123+456」（/mcp 查看）
```

全程**不写一行 client 代码，也不手动跑 server**。

**模式 B（自己的 LangChain 应用）——见第 10 节：**

```
写 Python：MultiServerMCPClient({...})   ← 这里自动 spawn server
   → await client.get_tools()            ← 自动发现工具
   → create_agent(llm, tools)            ← 挂 agent
   → agent.ainvoke(...)
```

全程**不碰 .mcp.json，也不手动跑 server**。

### 8.3 一个最常见的误解

很多人以为流程是「**先跑起 server → 配 .mcp.json → 用 client 拿工具挂 agent**」的串行三步。逐条看：

| 步骤 | 对不对 | 原因 |
|------|--------|------|
| ① 先跑起 mcp server | ❌（stdio 下） | stdio server 由**客户端自动 spawn**，不是你手动先起的；手动跑会卡住等 stdin，客户端连的时候还会再 spawn 一个，白占一个进程 |
| ② 配置 .mcp.json | ⚠️ 看模式 | 只在 Claude Code 模式里用；走 LangChain 代码时这个文件**没人读** |
| ③ client 拿工具挂 agent | ✅ 对 | 这是模式 B 的核心动作 |

> 唯一例外：**只有 streamable-http / SSE 远程传输，才需要「先跑起 server」**——那种 server 是监听端口的
> 独立服务，要先启动、再让 client 用 `url` 连过去。本地 stdio 不是这样。

### 8.4 上手建议

1. 先问自己「Agent 跑在哪？」再选模式。
2. stdio 交给客户端 spawn，别手动先起 server；只有切 streamable-http 才手动起服务。
3. `.mcp.json` 的 `command` 建议写死 venv 的 python 绝对路径（如 `d:/myagent/.venv/Scripts/python.exe`），
   别依赖 PATH——否则可能 spawn 到 Anaconda 的 python（它没装 mcp）。
4. 同一个 server 要给多个应用复用 / 上生产时，升级到 streamable-http（先起服务 + 远程 `url` 连接），
   这时才是「先跑起 server → client 连过去」。

---

## 9. 把 Server 接进 Claude Code

你现在就身在 **Claude Code** 里，所以这一步对你来说是「立刻能用」的技能。

MCP 服务器通过项目根目录的 `.mcp.json` 文件声明。在你项目根目录（`d:\myagent`）新建 `.mcp.json`：

```jsonc
{
  "mcpServers": {
    "math": {                              // 你给这个服务器起的别名
      "command": "d:/myagent/.venv/Scripts/python.exe",   // 用 venv 的 python（装了 mcp），别用裸 python 以免命中 Anaconda
      "args": ["langchain-exercise/mcp/mcp_math_server.py"],  // 脚本路径（注意是 mcp 目录，不是 docs）
      "env": {}                            // 可选：注入环境变量（放 API Key 等）
    }
  }
}
```

> ⚠️ 两个最常见的连接失败：① `args` 路径写错（server 文件在 `langchain-exercise/mcp/`，不是 `docs/`）；
> ② `command` 用裸 `python` 命中 Anaconda（它没装 mcp）。上面两处都建议写死 venv 的 python 绝对路径。

也可以直接用命令行添加（等价操作）：

```bash
claude mcp add math -- d:/myagent/.venv/Scripts/python.exe langchain-exercise/mcp/mcp_math_server.py
claude mcp list          # 查看已配置的 MCP 服务器
claude mcp remove math   # 移除
```

配置完成后，在 Claude Code 里输入 `/mcp` 可以查看服务器和它提供的工具是否加载成功，
之后你就可以直接说「用 math 工具帮我算 123 + 456」，Claude 会自动发现并调用。

> 🔑 关键认知：MCP 的「工具自动发现」是它的杀手锏——**你不需要在应用里硬编码工具列表**，
> 服务器一变，客户端自动感知。这正是它比「每个工具手写适配器」先进的地方。

---

## 10. 把 MCP 接进 LangChain / LangGraph

对正在学 LangChain 的你来说，这是**最该重点掌握**的一节：如何让 MCP 工具变成 LangChain 的工具，
并挂到 Agent 上（对应你学过的 06 工具篇 + 07 Agent 篇）。

用官方适配器 `langchain-mcp-adapters`：

```bash
pip install langchain-mcp-adapters
```

```python
# mcp_langchain_demo.py —— MCP 工具 → LangChain Agent
import asyncio
import os
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

load_dotenv()
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)


async def main():
    # ① 声明要连哪些 MCP 服务器（可连多个）
    client = MultiServerMCPClient({
        "math": {
            "command": "python",
            "args": ["mcp_math_server.py"],
            "transport": "stdio",        # 本地子进程
        },
        # 远程服务器则用：
        # "weather": {
        #     "url": "http://127.0.0.1:8001/mcp",
        #     "transport": "streamable_http",
        # },
    })

    # ② 把 MCP 工具转成 LangChain 的 BaseTool 列表
    tools = await client.get_tools()

    # ③ 直接挂到 Agent 上（LangChain 1.x 新 API create_agent，取代旧的 create_react_agent）
    agent = create_agent(llm, tools)

    # ④ 运行
    result = await agent.ainvoke(
        {"messages": [("user", "用工具帮我算一下 123 + 456 等于多少")]}
    )
    print(result["messages"][-1].content)


asyncio.run(main())
```

关键点：

- `MultiServerMCPClient` 是**客户端**，参数是一个字典：`别名 → 连接配置`。
- `await client.get_tools()` 是**异步**的（所以外面要 `asyncio.run`），返回 LangChain 认识的 `BaseTool`。
- 拿到的 `tools` 可以直接喂给 `create_agent`，和你在 06/07 篇自己用 `@tool` 定义的工具**用法完全一致**。

除了工具，适配器还能读资源和模板：

```python
tools     = await client.get_tools()                    # 拿工具
resources = await client.get_resources("math")          # 拿资源
prompt    = await client.get_prompt("math", "code_review", arguments={"code": "print(1)"})
```

> 🔑 这样你就打通了一条完整链路：**MCP Server（暴露工具）→ langchain-mcp-adapters（转成 LangChain 工具）
> → LangGraph Agent（编排调用）**。这是 2026 年多智能体架构里非常主流的一种组合。

---

## 11. MCP vs Function Calling：别再搞混

面试极爱问这一题，务必分清。

| 维度 | Function Calling（函数调用） | MCP |
|------|------------------------------|-----|
| 本质 | **模型的一种能力**（模型能输出「我想调哪个函数」的意图） | **一个开放协议**（约定工具如何被发现、描述、调用） |
| 归属 | 模型厂商（OpenAI / Anthropic 各自实现） | 开放标准，跨厂商 |
| 工具暴露方式 | 你自己写 JSON Schema，手动喂给模型 | 服务器声明，客户端**自动发现** |
| 复用性 | 换模型/换应用通常要重写 | 写一次，到处复用 |
| 关系 | 是 MCP 落地时「模型这一侧」的底层机制 | 是对 Function Calling 的**协议化、标准化封装** |

一句话记忆：

> **Function Calling 是「模型会调工具」这件事本身；MCP 是「工具该怎么接、怎么发现、怎么描述」的通用标准。**
> 两者不冲突，MCP 里的 Tool 最终仍是靠模型的 Function Calling 能力来触发的。

---

## 12. 什么时候该用 MCP？（决策表）

不是所有场景都值得上 MCP，学会判断才算「灵活专业」。

| 场景 | 建议 |
|------|------|
| 要接**很多**外部工具，且希望**跨多个应用复用** | ✅ 强烈推荐 MCP，收益最大 |
| 只想在**一个** LangChain 应用里用一两个简单工具 | ⚠️ 直接 `@tool` 定义即可，别过度设计 |
| 要暴露给**团队/第三方**使用，或希望工具可远程部署 | ✅ 用 MCP + Streamable HTTP |
| 纯本地、一次性脚本 | ❌ 直接写函数，不需要协议层 |
| 工具提供方已经提供了 MCP Server（如 GitHub、数据库） | ✅ 直接用 `MultiServerMCPClient` 接，别自己造轮子 |

> 🔑 决策原则：**MCP 解决的是「连接与复用」问题。连接对象越分散、复用需求越高，MCP 越划算；**
> 反之，单点、一次性场景用原生 Function Calling 更轻量。

---

## 13. 生产安全（2026 年的血泪教训）

MCP 让「接工具」变简单了，但简单背后是安全风险。2026 年对公开 MCP 服务器的扫描发现了一些触目惊心的数据：

- 被扫描的 8000+ 个公开 MCP 服务器里，**有 492 个完全没有认证**；
- **约 36.7%** 的服务器存在 **SSRF（服务端请求伪造）** 漏洞风险；
- **约 53%** 依赖**静态 API Key**，且把密钥**硬编码在源码里**。

这些数字要记住，面试聊「MCP 安全」时很有分量。对应到实践中：

| 风险 | 应对 |
|------|------|
| 服务器无认证、谁都能连 | Streamable HTTP 暴露时，**必须加鉴权**（OAuth / Token） |
| SSRF 漏洞（模型诱骗服务器去请求内网地址） | 严格校验工具参数里的 URL，限制可访问的网段 |
| 密钥硬编码 | **一律从环境变量读取**，绝不写死在代码里 |
| 工具输出被投毒（prompt injection） | 不信任工具返回的内容，必要时隔离、清洗后再进上下文 |
| 读写权限混在一起 | 用**分离的只读/写入 Token**，最小权限原则 |

> 🔑 一句话：**MCP 把「信任边界」从你的代码扩展到了外部工具，任何外部工具的输出都要当成「不可信输入」。**

---

## 14. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 装 `langchain-mcp-adapters` 后 mcp 被降级 | 之前 mcp 2.x 的 Server 突然报 `No module named 'mcp.server.mcpserver'` | adapter 只支持 mcp<2，装它会自动把 mcp 拉回 1.x；Server 统一改用 `FastMCP`（v1） |
| mcp 2.x 里还写 `FastMCP` | `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | v2 已改名 `MCPServer`，导入改 `from mcp.server.mcpserver import MCPServer` |
| 工具名用了中文（如 `天气`） | 启动告警 `Tool name contains invalid characters` | MCP 工具名按 SEP-986 只允许字母/数字/下划线/连字符/点，改用英文名（如 `get_weather`） |
| stdio 服务器没反应 | 运行后看不到任何输出 | 正常！stdio 服务器走标准输入输出，靠客户端来连，不是给人看的 |
| `get_tools()` 报异步错误 | `coroutine ... was never awaited` | 它是 async 函数，要用 `await` 且外层 `asyncio.run` |
| 类型注解缺失 | 工具的参数 Schema 变成空 `{}` | 给参数写上类型注解（`a: int`），FastMCP 靠它生成 Schema |
| 传输方式写错 | `streamable_http` vs `http` 混用 | 适配器里 `http` / `streamable_http` 都可；服务端用 `transport="streamable-http"` |
| 服务器能连但工具不出现 | Claude Code 里看不到工具 | 检查 `.mcp.json` 的 `command`/`args` 路径是否正确，用 `/mcp` 看加载状态 |
| 中文字符乱码 | 工具返回中文显示 `����` | Windows 下服务端/客户端脚本加 `sys.stdout.reconfigure(encoding="utf-8")` |

---

## 15. 面试高频题

**Q1：MCP 是什么？解决什么问题？**
> A：MCP（Model Context Protocol）是 Anthropic 开源的开放标准协议，用于标准化「AI 应用连接外部工具与数据」。
> 它把连接从 N×M 套胶水代码变成 N+M，让工具「写一次、到处复用」。

**Q2：MCP 架构里 Host / Client / Server 分别是什么？**
> A：Host 是运行 LLM 的 AI 应用本身；Client 是宿主内部与单个服务器通信的组件（1 对 1）；
> Server 是暴露能力的服务方。宿主里住着多个 Client，每个 Client 连一个 Server。

**Q3：MCP 有哪三类能力？区别是什么？**
> A：Tools（可执行、有副作用，模型自主调用）、Resources（只读数据，客户端读取）、Prompts（可复用提示模板）。
> 记忆口诀：能改变世界的是 Tool，只给世界看的是 Resource，教模型说话的是 Prompt。

**Q4：MCP 底层基于什么？交互流程是怎样的？**
> A：基于 JSON-RPC 2.0。流程是：`initialize` 能力协商 → `tools/list` 等发现 → `tools/call` 调用。
> 其中「能力协商」和「自动发现」是它区别于硬编码工具列表的关键。

**Q5：MCP 的传输方式有哪些？生产用哪个？**
> A：stdio（本地子进程，调试/Claude Code 常用）、SSE（早期 HTTP 流，已不推荐）、Streamable HTTP（2025 引入，生产远程首选）。

**Q6：MCP 和 Function Calling 是什么关系？**
> A：Function Calling 是模型「会调工具」的能力，MCP 是把工具「如何发现、描述、调用」做成开放标准协议。
> 两者不冲突，MCP 的 Tool 最终仍靠模型的 Function Calling 触发。

**Q7：如何把 MCP 工具接进 LangChain？**
> A：用 `langchain-mcp-adapters` 的 `MultiServerMCPClient`，`await client.get_tools()` 把 MCP 工具转成
> LangChain 的 `BaseTool` 列表，再喂给 `create_agent` 等编排组件。

**Q8：MCP 在生产上有哪些安全风险？**
> A：无认证暴露、SSRF 漏洞、密钥硬编码、工具输出投毒等。应对：加鉴权、校验参数 URL、密钥走环境变量、
> 只读/写入 Token 分离、不信任工具输出。

---

## 16. 练手题

1. 用 FastMCP 写一个「待办清单」服务器，包含 `add_task`、`list_tasks` 两个工具，本地 stdio 跑通
2. 给上面的服务器再加一个 `notes://readme` 资源和一个 `summary` 提示模板
3. 在 Claude Code 里用 `.mcp.json` 接入这个服务器，用 `/mcp` 确认工具已加载，并让它帮你加一条待办
4. 用 `langchain-mcp-adapters` 把这个服务器接进 LangChain，用 `create_agent` 跑一个多轮 Agent
5. 把服务器改成 `streamable-http` 方式远程部署，再用 `MultiServerMCPClient` 以 `url` 方式远程连接
6. 给远程服务器加上一个简单的 Token 鉴权（在客户端请求头里带上），验证不带 Token 时无法访问

---

## 参考资料

- [Model Context Protocol 官方文档](https://modelcontextprotocol.io)（权威规范）
- [LangChain + FastMCP 搭建大模型工具调用服务](https://cloud.tencent.com/developer/article/2729181)（FastMCP + 适配器实战）
- [FastMCP 与 langchain-mcp-adapters 多服务器协作](https://www.cnblogs.com/LyShark/p/22549291)（多服务器 + 资源/模板示例）

---

👉 下一篇：[13 — LangGraph 人机协作：审批模式与反馈模式](13-LangGraph人机协作审批与反馈.md) · 上一篇：[11 — 开发流程与工作方法](11-开发流程与工作方法.md) · 返回总目录：[00-README](00-README.md)
