# 04 — RAG 检索增强生成

> 目标：掌握**RAG（Retrieval-Augmented Generation）**——让 LLM 能回答"私有知识"的核心技术。
> 这是企业里最落地、面试必考的方向：文档问答、智能客服、知识库助手，本质都是 RAG。

---

## 1. 为什么需要 RAG？

LLM 有两个致命短板：

| 短板 | 例子 | RAG 怎么解决 |
|------|------|-------------|
| **知识过时** | 训练数据有截止日期，不知道最新新闻 | 检索最新文档喂给它 |
| **不知道私有数据** | 问"我们公司的报销制度"它瞎编 | 检索公司内部文档喂给它 |

**RAG 的思路**：别让模型"背"知识，而是**每次提问时，先去知识库搜出相关资料，塞进 prompt，让模型"看着资料回答"**。

```
普通问答：   问题 → LLM → 答案（可能胡说八道）
RAG 问答：   问题 → 检索器(从知识库找相关文档) → 拼进 prompt → LLM → 答案（有据可依）
```

---

## 2. RAG 的两阶段

RAG 系统分**两个独立阶段**：

### 阶段一：离线建库（Indexing）—— 把文档变成"可搜索"

```
原始文档 → 切分(TextSplitter) → 向量化(Embeddings) → 存进向量库(VectorStore)
```

### 阶段二：在线问答（Querying）—— 用户提问时检索 + 生成

```
用户问题 → 向量化 → 向量库相似度检索(Retriever) → 取出Top-K文档 → 拼进prompt → LLM生成
```

> 🔑 为什么是"向量"？因为**语义相似**不等于**字面相同**。
> "怎么报销打车费" 和 "交通费用如何申请" 字面不同，但语义一样。
> 向量化能把语义编码成数字，用"距离"衡量语义接近度。

---

## 3. 手把手：从零搭一个 RAG

### 3.1 准备文档

先用一段"公司制度"当私有知识：

```python
docs_text = """
第一条：员工因公产生的交通费用，可在次月5日前提交报销申请。
第二条：报销需提供发票原件，并填写报销单交部门经理审批。
第三条：单次报销金额超过5000元，需额外经财务总监审批。
第四条：出差住宿标准为一线城市每晚不超过800元，其他城市不超过500元。
"""
```

### 3.2 切分文档（TextSplitter）

文档太长不能直接塞，要切成小块（chunk）。**分块是 RAG 质量的关键**：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,        # 每块最多100字符
    chunk_overlap=20,      # 相邻块重叠20字符（防止语义被切断）
)

# 注意：传入的是列表
chunks = splitter.split_text(docs_text)
for i, c in enumerate(chunks):
    print(f"块{i}: {c}\n")
```

> 🔑 `chunk_overlap` 是容易被忽视但很重要的参数：重叠能保证"一句话被切断时"语义仍完整。
> 面试聊到分块策略（chunk_size / overlap 调优）会很加分。

### 3.3 向量化 + 存库（Embeddings + VectorStore）

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# 向量化模型（把文字转成向量）
embeddings = OpenAIEmbeddings()  # 国内模型可传 base_url，见文末

# 从切好的块直接建向量库
vectorstore = FAISS.from_texts(chunks, embedding=embeddings)

# 向量库也是 Runnable，可以直接检索（相似度搜索）
result = vectorstore.similarity_search("怎么报销打车费", k=2)
for doc in result:
    print(doc.page_content)
```

> `FAISS` 是 Meta 开源的向量检索库，纯本地运行、零成本，适合学习和小规模场景。
> 生产环境常用 Milvus / Chroma / pgvector 等。

### 3.4 转成 Retriever

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})   # 检索器，取Top3
```

`Retriever` 是 RAG 里的标准接口：`retriever.invoke(问题) → 相关文档列表`。

### 3.5 组装 RAG 链

现在用 LCEL 把"检索"和"生成"串起来：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 关键：prompt 里要有 {context}（检索到的资料）和 {question}（用户问题）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是公司制度助手，只根据以下资料回答问题，资料里没有就说不知道：\n\n{context}"),
    ("human", "{question}"),
])

# 组装：检索 → 拼装 → 生成
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}   # ① 同时拿"检索结果"和"原问题"
    | prompt                                                     # ② 填入模板
    | llm                                                        # ③ 生成
    | StrOutputParser()                                          # ④ 取文本
)

answer = rag_chain.invoke("打车费怎么报销？")
print(answer)
```

```
数据流向：

"打车费怎么报销？"
        │
        ├──→ retriever（向量检索）→ ["第一条：交通费用...", ...]
        │                                    │
        └──→ RunnablePassthrough（原样保留）─┤
                                             ▼
                              {"context": [...], "question": "..."}
                                             ▼
                                  prompt → llm → 答案
```

> 🎯 **这是 RAG 的"标准套路"，务必能默写**：`{"context": retriever, "question": RunnablePassthrough()}` 这行
> 同时给下游提供"检索到的资料"和"用户原始问题"。

---

## 4. 完整可运行示例

```python
# 04_demo.py
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# 私有知识
docs_text = """
第一条：员工因公产生的交通费用，可在次月5日前提交报销申请。
第二条：报销需提供发票原件，并填写报销单交部门经理审批。
第三条：单次报销金额超过5000元，需额外经财务总监审批。
第四条：出差住宿标准为一线城市每晚不超过800元，其他城市不超过500元。
"""

# ① 切分
splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
chunks = splitter.split_text(docs_text)

# ② 建向量库
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_texts(chunks, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ③ 组装 RAG 链
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是公司制度助手，只根据资料回答，资料里没有就说不知道：\n{context}"),
    ("human", "{question}"),
])
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt | llm | StrOutputParser()
)

# ④ 提问
for q in ["打车费怎么报销？", "单次报销8000元需要谁审批？", "公司团建去哪玩？"]:
    print(f"Q: {q}")
    print(f"A: {rag_chain.invoke(q)}\n")
```

第三个问题"公司团建去哪玩"资料里没有，好的 RAG 会回答"不知道"，而不是瞎编——这就是 RAG 抑制幻觉的价值。

---

## 5. RAG 的质量优化（面试加分项）

RAG 效果不好时，从这几个方向调：

| 环节 | 常见问题 | 优化手段 |
|------|---------|---------|
| **分块** | 块太大信息杂、太小语义碎 | 调 `chunk_size`/`overlap`，按文档结构（标题/段落）分 |
| **检索** | 检索不到 / 检索不准 | 换 embedding 模型、混合检索（向量+关键词）、`k` 调优 |
| **生成** | 模型不理资料、乱答 | 强化 prompt 约束、降低 temperature |
| **重排** | Top-K 里混入无关内容 | 加 rerank 重排序模型 |

> 进阶方向（了解即可，可作谈资）：**Hybrid Search**（向量+关键词混合）、**Rerank**（重排序）、
> **Multi-query**（把问题改写成多个变体再检索，提高召回）。

---

## 6. 国内模型的 Embedding 接入

和 `ChatOpenAI` 一样，`OpenAIEmbeddings` 也能接国内兼容接口（如硅基流动、阿里 DashScope）：

```python
embeddings = OpenAIEmbeddings(
    model="你的embedding模型名",
    base_url="https://兼容接口地址/v1",
    api_key="你的key",
)
```

> ⚠️ 注意：embedding 模型和对话模型是**两种**模型，接口和计费都不同。别拿对话模型当 embedding 用。

---

## 7. 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| 忘装 FAISS | 报 `ImportError` | `pip install faiss-cpu` |
| 向量库没持久化 | 每次运行重新建库 | 生产用 `vectorstore.save_local()` 或持久化向量库 |
| `split_text` 传了字符串 | 报错 | 记得传**列表** `splitter.split_text([text])` |
| prompt 没写 `{context}` | 检索结果没被用上 | 检查占位符和 dict key 一致 |
| 模型瞎编资料外内容 | RAG 失效 | prompt 里强调"资料里没有就说不知道" |

---

## 8. 面试高频题

**Q1：什么是 RAG？为什么需要它？**
> A：RAG 是检索增强生成，在生成前先检索相关资料注入 prompt，让模型基于资料回答。
> 它解决了 LLM 知识过时、无法访问私有数据两大问题，能显著抑制幻觉，是企业落地 LLM 的主要方式。

**Q2：RAG 的两个阶段分别是什么？**
> A：离线建库阶段（文档切分 → 向量化 → 存入向量库）和在线问答阶段
> （问题向量化 → 相似度检索 → 拼入 prompt → LLM 生成）。

**Q3：为什么要切分文档？`chunk_overlap` 有什么用？**
> A：文档过长无法直接喂给模型，需要切成小块，且模型输入有长度限制。
> `chunk_overlap` 让相邻块之间有重叠，避免语义在切分边界处被截断，保证检索质量。

**Q4：`Retriever` 是什么？RAG 链的 LCEL 写法是什么？**
> A：`Retriever` 是统一检索接口，`retriever.invoke(问题)` 返回相关文档。
> 标准写法是 `{"context": retriever, "question": RunnablePassthrough()} | prompt | llm | parser`，
> 同时把检索结果和原问题提供给下游。

---

## 9. 练手题

1. 把一段长文档（如一篇新闻）切成块，打印每块内容观察切分效果
2. 调整 `chunk_size` 和 `chunk_overlap`，感受检索结果的变化
3. 给 RAG 加上"如果资料里没有就回答不知道"的约束，测试幻觉是否被抑制
4. 用 `vectorstore.similarity_search` 直接检索 3 个不同问题，观察 Top-K 文档
5. 把向量库保存到本地（`save_local`），下次加载复用（`FAISS.load_local`）

---

👉 下一篇：[05 — 对话记忆与多轮会话](05-对话记忆与多轮.md) · 返回总目录：[00-README](00-README.md)
