from pydantic import BaseModel,Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

class stock(BaseModel):
    name:str=Field(description="股票名称")
    code:str=Field(description="股票代码")
    price:float=Field(description="股票价格")
    date:str=Field(description="日期")

parser=PydanticOutputParser(pydantic_object=stock)

template=ChatPromptTemplate(
    messages=[
        ("system","你是金融行业资深从业者，现作为金融顾问，帮助老板工作"),
        ("human","分析近日的金融市场{commerce}走势，给出投资建议，并以json格式输出股票名称、股票代码、股票价格、日期\n{format_instructions}"),
    ]
)

prompt=template.partial(format_instructions=parser.get_format_instructions())

llm=ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),# type: ignore
    temperature=0.1
)

chain=prompt|llm|parser
result=chain.invoke({"commerce":"沪深300"})

import json
print(result)
#print(json.dumps(result, ensure_ascii=False)) #中文乱码/转义 加 ensure_ascii=False
print(result.model_dump_json(indent=2))

class Person(BaseModel):
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")
# 一步到位：绑定结构化输出
structured_llm = llm.with_structured_output(Person, method="function_calling")

result = structured_llm.invoke("张三今年30岁")
print(type(result))   # <class '__main__.Person'>
print(result.name, result.age)

