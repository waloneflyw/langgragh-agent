# TypeScript 从零到智能体 —— 系列教程设计文档

- 日期：2026-11-11
- 状态：待审阅
- 受众：本项目的学习者本人（会 Python、会一点 Vue，但 JavaScript/TypeScript 从零起步）

---

## 1. 意图与为什么

学习者已经用一套 16 篇的 Python 版 LangChain/LangGraph 教程学会了智能体开发，现在想掌握 **TypeScript**，
目标是两条：一是能**用 TypeScript 开发通用项目**（命令行工具、Node API 服务），二是能**用 TypeScript 开发智能体应用**
（LangChain / LangGraph 的 TypeScript 版）。本系列就是这两条路从零到实战的教学载体。

为什么值得做一套专门的东西（而不是散落的笔记）：TypeScript 是 JS 的超集，直接从"智能体"学会让类型系统、
模块、异步这些地基悬空；从"语言本身"学到"工程化"再到"项目/智能体"，是唯一不缩水、且能迁移到任何 TS 项目的路径。

## 2. 目标

- 从**零 JavaScript 基础**起步，默认读者只会 Python（和一点 Vue 带来的 JS 印象）。
- 掌握 TypeScript 的类型系统、泛型、工具类型，能读懂并写出类型安全的代码。
- 掌握 TS 工程化：Node 环境、包管理、`tsconfig`、编译/构建、调试、测试、规范。
- 能独立开发两个通用项目类型：**命令行工具** 与 **Node HTTP API 服务**。
- 能用 TypeScript 版 LangChain / LangGraph 开发智能体：LLM 调用、结构化输出、RAG、工具、Agent、状态图、MCP。
- 每篇文档配一份**独立可运行**的代码，文档与代码**分开对应**。

## 3. 非目标

- 不教前端框架（React/Vue 本身）——只讲 Node 侧通用项目与智能体，前端不在本次范围内。
- 不追求与 Python 版 16 篇智能体教程**逐篇完全对等**（多智能体、A2A、LangSmith、人机协作等可作为后续扩展，不在首版 24 篇内）。
- 不深讲 JS 的冷门坑或历史包袱（`var` 提升、原型链继承细节、老式 `function` 构造函数等），只讲现代 JS/TS 所需。
- 不做视频/课件，交付物是 Markdown 文档 + 代码文件。

## 4. 反目标（做了反而算失败）

- 读者看完仍然**不会自己搭一个可运行的 TS 工程**。
- 文档里代码和独立代码文件**对不上**（路径错、版本不一致、跑不通）。
- 为追求篇幅堆砌概念，导致"看完不会写"——每篇必须以"能跑、能改、能讲"为准。
- 智能体部分脱离学习者已有的 Python 版认知，另起一套术语，导致迁移困难。

## 5. 约束

- 学习者运行环境：Windows 11，已会 Python，本机可装 Node.js。
- 文档语言：中文；代码注释：中文。
- 运行时默认：Node.js LTS（22+），包管理器用 **npm**（最通用，`pnpm` 作为可选项提示）。
- 运行 TS 代码的方式：学习阶段用 **`tsx`** 直接运行 `.ts`（免去先编译再运行的摩擦），同时用 **`tsc`** 讲清"类型检查"与"编译产物"。
- 智能体部分默认接 **OpenAI 兼容接口**（`base_url` 可换成 DeepSeek / 通义 / Kimi 等），与学习者 Python 系列的做法一致。
- 智能体框架：**LangChain TS v1 + LangGraph TS v1**（当前稳定版，对应其 Python 系列，也衔接已有学习路径），结构输出用 **zod**。注意 v1 已把旧的 `createReactAgent` 改为 `createAgent`、模型接入改为 `initChatModel` / `"provider:model"` 字符串，与 Python 系列旧版命名不同——教学以**当前稳定版为准**，并在文中标注更名点。

## 6. 方案（Approaches）

| 方案 | 说明 | 取舍 | 结论 |
|------|------|------|------|
| **A：一条完整主线** | 一个目录、编号连续、按顺序学，约 24 篇（JS 基础 → TS 核心 → 工程化 → 通用项目 → 智能体） | 完整连贯、沿用已验证的学习方式；篇幅较长 | ✅ 选用 |
| B：拆成三本"书" | JS/TS 基础、通用项目、智能体各成一册 | 可单独学；但拆散、连贯性弱、与 Python 系列风格不一致 | 否 |
| C：精简快车道 | JS/工程化只讲必需，最快进智能体 | 短快；但"通用项目都覆盖"缩水，未满足需求 | 否 |

选择 A 的理由：学习者明确要求"通用项目 + 智能体都覆盖"，A 是唯一不缩水的做法，且能复用其学 Python 系列已验证有效的方式。

## 7. 已决定的实现方式

### 7.1 目录位置与结构

在工作区根目录新建 `typescript-exercise/`，与现有 `langchain-exercise/` 并列：

```
typescript-exercise/
├── docs/                 # 教学文档（Markdown，编号 00 起）
│   ├── 00-README.md
│   ├── 01-xxx.md
│   └── ...
├── code/                 # 每篇文档对应的独立可运行代码
│   ├── 01-hello-js/      # 与 docs/01 一一对应
│   ├── 02-xxx/
│   └── ...
├── package.json          # 根依赖（共享，一次安装）
├── tsconfig.json         # 根类型检查配置
└── .env.example          # API Key 模板（智能体阶段用）
```

### 7.2 文档 ↔ 代码对应规范

- **一篇文档 ↔ 一个 `code/NN-slug/` 目录**，编号与文档编号一致。
- 文档以**讲解为主**：只在需要解释语法点的地方放少量内联示意代码；
  **完整可运行的代码一律放在 `code/NN-slug/` 里**，文档开头用"本讲代码在 `code/NN-slug/`"显式指向。
- 代码目录内每个 `.ts` 文件**独立可运行**（用 `npx tsx code/NN-slug/main.ts`），并附运行命令。
- 文档末尾沿用 Python 系列惯例：**练手题** + **面试高频题**（附参考答案要点）。

### 7.3 每篇文档的统一结构

1. 本篇要解决什么问题（一句话）
2. 概念讲解（对照 Python / 已有认知）
3. 代码走读（指向 `code/NN-slug/`，逐段说明）
4. 运行与实验（怎么跑、改哪里观察变化）
5. 练手题
6. 面试高频题

### 7.4 章节大纲（5 阶段，24 篇）

**第一阶段 · JavaScript 基础（5 篇）** —— TS 的地基，默认零 JS
1. `01-hello-js`：Node.js 安装、运行 JS、`console.log`、JS 是什么、与 Python 对照
2. `02-values-types`：`let`/`const`、七种原始类型、字符串/数字/布尔、模板字符串、类型转换
3. `03-functions-control-flow`：函数声明/箭头函数、`if`/`for`/`while`、三元、短路、`switch`
4. `04-objects-arrays`：对象字面量、数组高阶方法 `map`/`filter`/`reduce`、解构、展开
5. `05-modules-async`：ESM `import`/`export`、`Promise`、`async`/`await`、`fetch`、`try/catch`

**第二阶段 · TypeScript 核心（6 篇）**
6. `06-why-ts`：为什么需要 TS、安装 `tsc`、第一个类型注解、类型推断
7. `07-basic-types`：原始类型、数组、元组、联合、字面量、`type` 别名、`unknown`/`any`、`null`/`undefined`
8. `08-interface-objects`：`interface`、可选属性、`readonly`、索引签名、交叉类型、`interface` vs `type`
9. `09-function-types`：参数/返回值注解、可选/默认/剩余参数、函数类型别名、重载（简述）
10. `10-generics`：泛型函数/接口/类、约束、`keyof`/`typeof`
11. `11-advanced-types-narrowing`：工具类型 `Partial`/`Pick`/`Omit`/`Record`、类型守卫、`as const`、条件类型（简述）

**第三阶段 · TS 工程化（3 篇）**
12. `12-node-project`：`package.json`、npm、依赖与脚本、ESM vs CJS
13. `13-tsconfig-build`：`tsconfig`（`strict`、`target`/`module`、路径别名）、`tsc` 编译、源映射
14. `14-debug-test-lint`：VS Code 断点调试、vitest 基础、eslint + prettier

**第四阶段 · 通用项目（4 篇）**
15. `15-cli`：命令行工具——解析参数、读文件、做一个真实 CLI（待办/笔记 CLI）
16. `16-http-api`：Node HTTP API——用 Fastify 做 REST API（CRUD）、路由、参数校验
17. `17-data-persistence`：文件存储 + SQLite（better-sqlite3）、环境变量与配置（dotenv）
18. `18-comprehensive-project`：综合项目——把 CLI + API + 数据串成一个完整可演示项目，附打包/部署说明

**第五阶段 · 智能体（LangChain / LangGraph TS，6 篇）**
19. `19-langchain-llm`：智能体生态与 LLM 调用——LangChain TS v1 是什么、`langchain`/`@langchain/core` 包、`initChatModel` 与 provider 包（`@langchain/openai` 接国内兼容 `base_url`）、消息、流式
20. `20-prompt-structured-output`：Prompt 模板、结构化输出（zod schema / 内容块 contentBlocks）
21. `21-lcel-rag`：`.pipe()` 链式组合、文档切分、向量库、retriever、RAG 链
22. `22-tools-agent`：`tool()`（zod schema）、`createAgent`（v1 标准 Agent API）
23. `23-langgraph-state`：`StateSchema`/`MessagesValue`/`ReducedValue`、`StateGraph`、节点、条件路由、循环、`MemorySaver` 持久化
24. `24-mcp-comprehensive`：MCP 接入 + 一个完整 TS 智能体项目（多工具 + 状态图 + MCP），收尾总结

> 后续可扩展（不在首版）：多智能体协作、人机协作 `interrupt`、A2A、LangSmith 可观测性——学习者在 Python 系列已学过这些概念，届时可平滑迁移。

## 8. 留给构建者的判断（What's left to the builder）

- 每篇的具体示例选材（用什么例子讲透知识点），原则：小而真实、能跑、能改。
- 根 `package.json` 的依赖清单与版本钉定；`tsconfig.json` 的严格度设置。
- 每篇的练手题与面试题的具体内容。
- 是否需要为"综合项目"单独建独立工程目录（与"每篇一个目录"的通用规则略有不同，视该篇复杂度而定）。
- 智能体阶段的 `.env` 与 API Key 接入方式（沿用 Python 系列的"两套写法"惯例）。
- **API 版本选择**（审阅后定）：教学以 LangChain/LangGraph TS **当前稳定版 v1** 为准；`createReactAgent`→`createAgent`、`DynamicStructuredTool`→`tool()` 等更名点在文中标注，不照抄 Python 系列旧命名。
- **智能体阶段的验证方式**（审阅后定）：构建者按当前文档 API 编写代码、沿用"两套写法"（OpenAI 官方 + DeepSeek `base_url`），由学习者用自己的 Key 运行；构建过程不执行真实 LLM 调用。RAG 篇默认用内存向量库 + 同 provider 的 embedding。

---

**下一步**：本设计文档经审阅并获学习者批准后，进入 `superpowers:writing-plans` 排章写代码。
