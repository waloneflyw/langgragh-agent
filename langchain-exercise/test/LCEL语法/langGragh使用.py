from dotenv import load_dotenv
import os
import sys
from typing import TypedDict, Annotated
from operator import add

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START

sys.stdout.reconfigure(encoding="utf-8")  # 让 Windows 控制台正确显示中文

load_dotenv()
llm = ChatOpenAI(model="deepseek-v4-pro",
                 base_url="https://api.deepseek.com",
                 api_key=os.getenv("DEEPSEEK_API_KEY"),
                 temperature=0.7)


# ============================================================
# 一、基础图：两个节点串联
# ============================================================
# 节点函数返回的是"部分更新"：只写要改的字段，框架自动合并回 State。
class MyState(TypedDict):
    question: str
    answer: str
    output: str


def process_node(state: MyState) -> dict:
    # 处理节点：调用 LLM 回答问题
    question = state["question"]
    answer = llm.invoke(question)
    return {"answer": answer.content}      # 只更新 answer


def format_node(state: MyState) -> dict:
    # 格式化节点：把 answer 加工成最终 output（注意这里是 \n 不是 /n）
    output = f'处理的结果：\n{state.get("answer")}'
    return {"output": output}              # 只更新 output


graph = StateGraph(MyState)
graph.add_node("process", process_node)
graph.add_node("format", format_node)

graph.add_edge(START, "process")   # 入口（旧写法是 set_entry_point("process")）
graph.add_edge("process", "format")
graph.add_edge("format", END)

app = graph.compile()

print("【一、基础串联图】")
rs = app.invoke({"question": "用一句话说说人工智能的发展趋势"})
print(rs["output"])


# ============================================================
# 二、State Reducer 状态规约器
# ============================================================
# 每个 State 字段都带一个"合并规则"（reducer）：
#   普通字段 str/int     → 覆盖（最后一个节点写的值生效）
#   Annotated[list, add] → 累加（每次返回的列表自动拼到旧列表后面）
class ReduceState(TypedDict):
    text: str
    logs: Annotated[list, add]   # add reducer：列表自动累加


def node_a(state: ReduceState) -> dict:
    return {"text": "A", "logs": ["进入A"]}

def node_b(state: ReduceState) -> dict:
    return {"text": "B", "logs": ["进入B"]}

def node_c(state: ReduceState) -> dict:
    return {"text": "C", "logs": ["进入C"]}


g2 = StateGraph(ReduceState)
g2.add_node("a", node_a)
g2.add_node("b", node_b)
g2.add_node("c", node_c)
g2.add_edge(START, "a")
g2.add_edge("a", "b")
g2.add_edge("b", "c")
g2.add_edge("c", END)

app2 = g2.compile()

print("\n【二、State Reducer 状态规约器】")
result = app2.invoke({"text": "初始", "logs": []})
print("text（普通字段，被覆盖）:", result["text"])   # 结果是 C，最后一个节点说了算
print("logs（add reducer，累加）:", result["logs"])  # 三条都保留下来了


# ============================================================
# 三、条件路由（add_conditional_edges）
# ============================================================
# 核心思路：先用一个节点判断"分类"，再根据分类值走不同的分支节点。
class RouterState(TypedDict):
    input: str
    category: str
    response: str


def classify_node(state: RouterState) -> dict:
    """分类节点：用 LLM 判断输入属于 math / code / general"""
    prompt = f"""请判断以下用户输入属于哪个类别，只回复类别名（math/code/general）：
用户输入：{state['input']}"""
    response = llm.invoke(prompt)
    category = response.content.strip().lower()
    # 兜底：模型万一回了多余文字（如"数学"、"math。"），统一归为 general
    if category not in ("math", "code", "general"):
        category = "general"
    return {"category": category}


def math_handler(state: RouterState) -> dict:
    response = llm.invoke(f"请解答这道数学题：{state['input']}")
    return {"response": response.content}

def code_handler(state: RouterState) -> dict:
    response = llm.invoke(f"请编写代码实现：{state['input']}")
    return {"response": response.content}

def general_handler(state: RouterState) -> dict:
    response = llm.invoke(f"请回答这个问题：{state['input']}")
    return {"response": response.content}


# 路由函数：返回"分类值"（math/code/general），而不是节点名
def route_function(state: RouterState) -> str:
    return state["category"]


g3 = StateGraph(RouterState)
g3.add_node("classify", classify_node)
g3.add_node("math_handler", math_handler)
g3.add_node("code_handler", code_handler)
g3.add_node("general_handler", general_handler)

g3.add_edge(START, "classify")

# 条件边：路由函数返回什么值，就映射到哪个节点
g3.add_conditional_edges(
    "classify",        # 从哪个节点出发
    route_function,    # 路由函数，返回一个"分类值"
    {
        "math": "math_handler",        # 分类值 → 目标节点名
        "code": "code_handler",
        "general": "general_handler",
    },
)

# 所有分支最后都汇到 END
g3.add_edge("math_handler", END)
g3.add_edge("code_handler", END)
g3.add_edge("general_handler", END)

app3 = g3.compile()

print("\n【三、条件路由】")
test_inputs = ["帮我计算 1+1 等于几", "用Python写一个冒泡排序", "今天天气怎么样"]
for test_input in test_inputs:
    result = app3.invoke({"input": test_input})
    print(f"输入：{test_input}")
    print(f"分类：{result['category']}")
    print(f"输出：{result['response'][:50]}...")
    print()
