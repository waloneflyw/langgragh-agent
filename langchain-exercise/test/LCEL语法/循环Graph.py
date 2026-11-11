import random
from typing import TypedDict
from langgraph.graph import StateGraph, END



class loopState(TypedDict):
    input: str
    attemptes:int
    count: int
    output: str
    success: bool


