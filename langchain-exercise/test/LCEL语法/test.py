import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate




load_dotenv()  # Load environment variables from .env file

llm = ChatOpenAI(
    model="deepseek-v4-pro",                         # DeepSeek 的模型名  deepseek-v4-pro deepseek-v4-flash-vision-exp
    base_url="https://api.deepseek.com",           # 兼容接口地址
    api_key=os.getenv("DEEPSEEK_API_KEY"),# type: ignore 
    temperature=0,
)

reply=llm.invoke("介绍一下你自己。另外告诉我你流式输出的语法")

#print(reply)

# 骨架：{name} 和 {product} 是"占位符"，像 Vue 模板里的 {{ name }}
template = ChatPromptTemplate.from_messages([
    ("system", "你是销售，向客户推荐产品，语气热情专业。"),
    ("human", "客户叫{name}，请向他推荐{product}，写一段推销话术。"),
])

# 填入数据
prompt_value = template.invoke({"name": "张三", "product": "洗衣机"})
print(prompt_value)   # 变成了一串完整的消息

template1=ChatPromptTemplate.from_messages(
    [
    ("system","你是金融行业资深从业者，现作为金融顾问，帮助老板工作"),
    ("human","分析近日的金融市场{commerce}走势，给出投资建议"),
    ]
)
prompt_value1=template1.invoke({"commerce":"沪深300"})

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

template2=ChatPromptTemplate(
    
    messages=[
        ("system","你是金融行业资深从业者，现作为金融顾问，帮助老板工作"),
        MessagesPlaceholder(variable_name="history"),
        ("human","分析近日的金融市场{commerce}走势，给出投资建议"),
    ]
)

