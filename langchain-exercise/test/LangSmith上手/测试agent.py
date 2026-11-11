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

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt=ChatPromptTemplate.from_template("回答这个问题：{question}")
chain=prompt|llm|StrOutputParser()
result=chain.invoke({"question":"1+1 等于几？"})
print(result)