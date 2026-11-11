

from pydantic import BaseModel, Field
from langchain_core.tools import tool
@tool
def add(a: int, b: int)->int:
    '''两数和'''
    return a+b

from dotenv import load_dotenv
import os   
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage,ToolMessage,AIMessage

load_dotenv()  # Load environment variables from .env file
llm=ChatOpenAI(model="deepseek-v4-pro",
                  base_url="https://api.deepseek.com", 
                 api_key=os.getenv("DEEPSEEK_API_KEY"), 
                 temperature=0.7
                 )
llm_with_tools=llm.bind_tools([add])
response=llm_with_tools.invoke([HumanMessage(content="请帮我计算一下 1+2")])
print(response.tool_calls)

tool_call=response.tool_calls[0]
result=add.invoke(tool_call["args"])
print(result)

final=llm_with_tools.invoke([
    HumanMessage(content="请帮我计算一下 1+2"),
    response,
     ToolMessage(content=str(result), tool_call_id=tool_call["id"])
    ])

print(final)
