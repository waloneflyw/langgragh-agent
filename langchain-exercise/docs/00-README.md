# 🚀 LangChain 智能体开发 —— 从零到实战

## 这套文档是什么？

这是一套**面向面试与工作**的 LangChain 智能体（Agent）开发教学文档，用**边敲代码边理解**的方式，
带你从"调用一个 LLM"一路走到"能独立开发、部署一个多智能体系统"。

和之前学 Vue 一样：**每一篇都以可运行的代码为核心**，你照着敲一遍、改一改，就能真正掌握。
每篇末尾都附有**练手题**和**面试高频题**，帮你把知识转化为面试时的表达能力。

> 💡 本文档全部使用 **Python**。LangChain 生态中 Python 版是最主流、更新最快、企业招聘最常考的版本
> （JS 版能力相对滞后，学会 Python 版后 JS 版可平滑迁移）。

---

## 为什么学 LangChain 做智能体？

一句话：**LLM 只能"说话"，智能体要能"做事"。**

```
普通 LLM 调用：          你问 → 它答（只会生成文本，不会查数据、不会调接口、不会写文件）

智能体（Agent）：         你下达目标 → 它自己规划步骤 → 调用工具（搜索/查库/算数/调API）
                          → 观察结果 → 决定下一步 → 直到完成任务
```

LangChain 提供了一套**标准化积木**，让你不必重复造轮子，就能把 LLM、提示词、工具、记忆、检索、
流程编排拼装成可控的智能体。学它，本质是在学**一套工业级的智能体工程方法论**——即使以后不用 LangChain，
这套思维（提示词工程、工具调用、RAG、状态编排）也是通用的。

---

## 学习路线

文档编号从 `01` 到 `15`，知识点层层递进，**强烈建议按顺序学**：

| 阶段 | 序号 | 文档 | 核心知识点 | 你能做出什么 |
|------|------|------|-----------|-------------|
| **基础篇** | 01 | [LangChain 是什么 + LLM 调用](01-langchain-基础与llm调用.md) | 生态组成、`ChatOpenAI`、消息类型、流式输出 | 能调用任意 LLM 并控制输出格式 |
| | 02 | [Prompt 模板与输出解析](02-prompt模板与输出解析.md) | `ChatPromptTemplate`、结构化输出、`PydanticOutputParser` | 让 LLM 稳定输出 JSON/对象 |
| **组合篇** | 03 | [LCEL 链式组合](03-lcel链式组合.md) | `Runnable`、`\|` 管道、`RunnableParallel`、分支 | 用"管道"像搭积木一样拼流程 |
| | 04 | [RAG 检索增强生成](04-rag检索增强生成.md) | 文档切分、向量库、`Retriever`、RAG 链 | 做一个"能回答私有知识"的问答 |
| | 05 | [对话记忆与多轮会话](05-对话记忆与多轮.md) | 消息历史、`RunnableWithMessageHistory`、多会话 | 让机器人"记住"上下文 |
| **智能体篇** | 06 | [Tools 工具定义与调用](06-tools工具定义与调用.md) | `@tool`、`StructuredTool`、工具调用原理 | 让 LLM 会"用工具" |
| | 07 | [Agent 智能体核心](07-agent智能体核心.md) | Agent vs Chain、ReAct、`create_react_agent` | 做出第一个真正会规划的智能体 |
| | 08 | [LangGraph 状态图](08-langgraph状态图.md) | `StateGraph`、节点、条件路由、循环、持久化 | 用"图"编排复杂多步流程 |
| **进阶篇** | 09 | [多智能体协作](09-多智能体协作.md) | Supervisor 模式、多 Agent 分工、共享状态 | 让多个 Agent 各司其职、协同工作 |
| | 10 | [综合项目实战](10-综合项目实战.md) | 完整项目串联全部知识 | 交付一个可面试展示的项目 |
| | 11 | [开发流程与工作方法](11-开发流程与工作方法.md) | 需求拆解、五步法、决策表、避坑、面试题 | 把能力变成工作方法与谈资 |
| | 12 | [MCP 模型上下文协议](12-MCP模型上下文协议.md) | Host/Client/Server、FastMCP、工具接入、Claude Code | 用标准协议给智能体接任意工具 |
| | 13 | [LangGraph 人机协作：审批与反馈](13-LangGraph人机协作审批与反馈.md) | `interrupt`、`Command(resume)`、审批/反馈模式 | 让智能体在关键动作/产物上停下来等人把关 |
| | 14 | [A2A 智能体互联协议](14-A2A智能体互联协议.md) | Agent Card、Task、AgentExecutor、A2A vs MCP | 让智能体之间互相发现、派活、协作 |
| | 15 | [LangSmith 可观测性与评估](15-LangSmith可观测性与评估.md) | 追踪、`@traceable`、数据集、`evaluate`、LLM-as-judge | 给智能体装可观测性并量化评估 |

---

## 环境准备

### 第 1 步：安装 Python

Windows 下到 [python.org](https://www.python.org/downloads/) 下载 Python 3.10 ~ 3.12 并安装。
**安装时勾选 "Add Python to PATH"**。

验证：

```bash
python --version
# 应输出类似：Python 3.11.9
```

### 第 2 步：创建项目与虚拟环境

```bash
# 进入你的练习目录
cd d:/Vue-exercise/langchain-exercise

# 创建虚拟环境（隔离依赖，避免污染全局）
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate
# 激活成功后命令行前会出现 (.venv) 前缀

# 升级 pip
python -m pip install --upgrade pip
```

> 💡 虚拟环境是 Python 的必备习惯：每个项目一套独立依赖，互不干扰。
> 退出虚拟环境用 `deactivate`。

### 第 3 步：安装 LangChain 全家桶

```bash
pip install langchain langchain-core langchain-openai langchain-community
pip install langchain-text-splitters
pip install langgraph
pip install python-dotenv          # 读取 .env 环境变量
pip install pydantic               # 数据模型校验（结构化输出要用）
```

可选（RAG 篇会用到）：

```bash
pip install faiss-cpu              # 本地向量库 FAISS
pip install langchain-chroma       # 或者用 Chroma
```

各包职责（面试常问"这些包有什么区别"）：

| 包名 | 职责 |
|------|------|
| `langchain-core` | 核心抽象：消息、Prompt、`Runnable`、工具、输出解析器（**一切的地基**） |
| `langchain` | 面向用户的聚合入口（链、智能体、记忆等高级组件） |
| `langchain-openai` | OpenAI 及 **OpenAI 兼容**模型接入 |
| `langchain-community` | 社区维护的第三方集成（向量库、文档加载器等） |
| `langgraph` | **状态图**引擎，现代智能体编排的事实标准 |

### 第 4 步：准备 API Key

LLM 调用需要密钥。**国内常用 OpenAI 兼容模型**（更便宜、无需翻墙），本文档所有示例默认给两套写法：

**方案 A：OpenAI 官方**（需可访问 OpenAI）

```
# 在项目根目录新建 .env 文件（注意：不要提交到 git）
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

**方案 B：国内 OpenAI 兼容模型（推荐）**

DeepSeek、通义千问、Kimi、智谱等**都兼容 OpenAI 接口**，只需换 `base_url` 和 `model`：

```
# .env 文件
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
```

```python
# 通用接入模板（后面的文档都会用到，先看懂结构）
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # 自动读取 .env 文件

# 方案 A：OpenAI 官方
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 方案 B：DeepSeek（把注释去掉即可）
# llm = ChatOpenAI(
#     model="deepseek-chat",                         # DeepSeek 的模型名
#     base_url="https://api.deepseek.com/v1",         # 兼容接口地址
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     temperature=0,
# )
```

> 🔑 **关键认知**：`ChatOpenAI` 并不只能用 OpenAI——只要传入 `base_url`，它就能连**任何 OpenAI 兼容接口**。
> 这是国内开发的必修技能，面试也常问。

### 第 5 步：验证能跑通

新建 `test.py`，粘贴下面代码并运行：

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # 国内模型按上面改成 base_url 写法

reply = llm.invoke("用一句话介绍你自己")
print(reply)  # 会打印一个 AIMessage 对象，里面有 .content
```

```bash
python test.py
```

如果打印出了模型的回复，说明环境就绪 ✅。接下来从 [01 开始 →](01-langchain-基础与llm调用.md)。

---

## 学习方法建议

1. **按顺序敲代码**：编号层层递进，跳过会断链
2. **每行都手动敲**：不要复制粘贴，手敲记忆更深
3. **改代码做实验**：把 temperature 调大、换 prompt、换工具，观察输出变化
4. **跑通一个项目再学下一个**：每个综合项目都要能独立复现
5. **对着面试题自问自答**：每篇末尾的面试题，先自己讲一遍，再看参考答案

---

## 你需要的前置知识

- ✅ Python 基础（变量、函数、类、`if`/`for`、`dict`/`list`）
- ✅ 能看懂简单 JSON
- ✅ 用过至少一个 LLM（ChatGPT / DeepSeek / 文心一言等）

**不需要**：机器学习背景、深度学习知识。智能体开发本质是**软件工程**，不是炼丹。

---

## 学完后你将具备的能力

- ✅ 独立调用任意 LLM，并让它稳定输出结构化数据
- ✅ 搭建 RAG 系统，让 LLM 基于私有知识回答
- ✅ 定义工具，让 LLM 调用真实函数（查库、调 API、算数）
- ✅ 用 LangGraph 编排多步、有循环、有条件的智能体流程
- ✅ 设计多智能体协作系统
- ✅ 用"五步法"把业务需求落地为可运行的智能体

准备好开始了吗？👉 [从 01 开始 →](01-langchain-基础与llm调用.md)
