from dotenv import load_dotenv
import os
import sys

from langchain_openai import ChatOpenAI

sys.stdout.reconfigure(encoding="utf-8")  # 让 Windows 控制台正确显示中文，避免乱码
load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                  base_url="https://api.deepseek.com",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 temperature=0.7)


from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence, RunnableMap, RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("回答这个问题：{question}")


# ============================================================
# 先记住三者的核心区别：
#   RunnableSequence —— 顺序串行：A → B → C，前一个的输出是后一个的输入
#   RunnableParallel —— 并行扇出：同一个输入，同时喂给多个分支，结果合并成【字典 dict】
#   RunnableMap      —— 就是 RunnableParallel 的别名，两者是同一个类（is 判断为 True）
#                       注意：合并出来是 dict，不是 list！
# ============================================================

# ------------------------------------------------------------
# 一、RunnableSequence：顺序执行
# ------------------------------------------------------------
# 显式写法
seq1 = RunnableSequence(prompt, llm, StrOutputParser())
# 等价写法（管道符，更直观，推荐）
seq2 = prompt | llm | StrOutputParser()

print("【一、RunnableSequence】")
print(seq1.invoke({"question": "1+1 等于几？"}))


# ------------------------------------------------------------
# 二、RunnableParallel：并行执行，结果合并成 dict
# ------------------------------------------------------------
# 同一个 {question} 输入，同时走 3 个分支（2 个分支各调一次模型，同时发出）
prompt_zh = ChatPromptTemplate.from_template("用中文一句话回答：{question}")
prompt_en = ChatPromptTemplate.from_template("Answer in English in one sentence: {question}")

parallel_chain = RunnableParallel(
    中文=prompt_zh | llm | StrOutputParser(),
    英文=prompt_en | llm | StrOutputParser(),
    原问题=RunnableLambda(lambda x: x["question"]),   # 纯函数分支，不调模型
)

print("\n【二、RunnableParallel】")
result = parallel_chain.invoke({"question": "杭州有什么好玩的？"})
print("中文:", result["中文"])
print("英文:", result["英文"])
print("原问题:", result["原问题"])

# 也有 dict 简写：右边直接写字典，会自动转成 RunnableParallel
# from operator import itemgetter
# parallel_chain2 = prompt | {"回答": llm | StrOutputParser(), "原问题": itemgetter("question")}


# ------------------------------------------------------------
# 三、RunnableMap：就是 RunnableParallel 的别名
# ------------------------------------------------------------
print("\n【三、RunnableMap】")
print("RunnableMap is RunnableParallel ->", RunnableMap is RunnableParallel)

map_chain = RunnableMap(
    回答=prompt | llm | StrOutputParser(),
    原问题=RunnableLambda(lambda x: x["question"]),
)
print(map_chain.invoke({"question": "今天星期几？"}))


# ------------------------------------------------------------
# 补充：RunnableBranch（按条件走不同分支，和上面三个是另一类，后续展开）
# ------------------------------------------------------------
