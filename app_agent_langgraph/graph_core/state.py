"""
app_agent_langgraph/graph_core/state.py

O3: LangGraph 狀態定義
"""
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """LangGraph Agent 的狀態結構"""
    messages: Annotated[list[BaseMessage], operator.add]
    tool_calls_count: int
