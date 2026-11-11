from dotenv import load_dotenv
import os
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence,RunnableParallel,RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                  base_url="https://api.deepseek.com", 
                 api_key=os.getenv("DEEPSEEK_API_KEY"), 
                 temperature=0.7)

写标题 = ChatPromptTemplate.from_messages([("human", "为「{项目}」本周工作写一个8字以内的标题，只输出标题")]) | llm | StrOutputParser()
写内容 = ChatPromptTemplate.from_messages([("human", "为「{项目}」本周工作写3条进展要点，每条一行")]) | llm | StrOutputParser()

# 并行生成标题和内容，再合并成周报
周报 = (
    RunnableParallel(标题=写标题, 内容=写内容)
    | RunnableLambda(lambda d: f"## {d['标题']}\n{d['内容']}")
)

print(周报.invoke({"项目": "智能客服系统"}))