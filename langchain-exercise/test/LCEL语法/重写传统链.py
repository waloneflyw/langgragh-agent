from dotenv import load_dotenv
import os

from langchain_openai import ChatOpenAI

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                  base_url="https://api.deepseek.com", 
                 api_key=os.getenv("DEEPSEEK_API_KEY"), 
                 temperature=0.7)


from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_core.output_parsers import StrOutputParser

prompt1=ChatPromptTemplate.from_template("为一部关于{topic}的电影起一个响亮的标题")
prompt2=ChatPromptTemplate.from_template("为一部标题为{title}的电影写一个简短的剧情简介")

chain=(
    {'title':prompt1|llm|StrOutputParser()}|
    prompt2|llm|StrOutputParser()
)

#调用

# rs=chain.invoke({'topic':'人工智能觉醒'})
# print(rs)

#Runnacle模块重写
from langchain_core.runnables import RunnableSequence,RunnableParallel,RunnableLambda,RunnablePassthrough

chain1=(
    prompt1|llm|StrOutputParser()
)

chain2=(
    RunnablePassthrough().assign(title=chain1)|
    prompt2|llm|StrOutputParser()
    |RunnableLambda(lambda summary:{"summary":summary})
)

print(RunnablePassthrough().assign(title=chain1).invoke({'topic':'人工智能觉醒'}))

