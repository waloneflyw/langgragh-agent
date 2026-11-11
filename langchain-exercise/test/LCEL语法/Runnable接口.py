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
from langchain_core.runnables import RunnableSequence,RunnableParallel,RunnableLambda
from langchain_core.output_parsers import StrOutputParser

prompt=ChatPromptTemplate.from_template("回答这个问题：{question}")

#Runnable接口测试
#RunnablePassthrough

from langchain_core.runnables import RunnablePassthrough
pass_through=RunnablePassthrough()

chain=(
    pass_through|(
        lambda x:{
            'answer':(prompt|llm).invoke(x),
            'original_question':x['question']
        }
    )
)
rs=chain.invoke({'question':'什么是人工智能？'})

print(rs)

#简化写法

chain2=RunnablePassthrough().assign(answer=lambda x:(prompt|llm).invoke(x))




#RunnableLambda  将任意函数包装成LCEL规范的对象

from langchain_core.runnables import RunnableLambda

def add_one(x:int):
    return x+1

add_one_runnable=RunnableLambda(add_one)

prompt1=ChatPromptTemplate.from_template("请帮我写一段广告文案，产品名称是：{product}")


chain3=(
    RunnablePassthrough().assign(product_name=lambda x:x['product'].upper())
    |RunnablePassthrough().assign(ad=prompt1|llm|StrOutputParser())
)

