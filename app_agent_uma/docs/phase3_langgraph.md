# 第三階段：LangGraph（有狀態圖形 Agent）

## 概述

第三階段使用 **LangGraph** 建立有狀態（stateful）的 Agent 工作流程圖，相較於第二階段的線性 ReAct，LangGraph 支援條件分支、平行節點與持久化狀態。

---

## 核心概念

```
LangGraph 工作流程 = StateGraph + Nodes + Edges

StateGraph：定義全局狀態（如 messages、tool_outputs）
Node：處理節點（如 agent 節點、工具節點）
Edge：有條件或無條件的節點間連接
```

---

## 與前兩階段的比較

| 面向 | 第一階段 | 第二階段 | 第三階段 |
|---|---|---|---|
| 框架 | 原生 Gemini | LangChain | LangGraph |
| 流程模式 | 迴圈 | ReAct 線性 | 有向圖（DAG） |
| 狀態管理 | 手動 Session | AgentExecutor | StateGraph |
| 平行工具 | 不支援 | 不支援 | 支援 |
| 條件分支 | 不支援 | 不支援 | 支援 |
| 複雜度 | 低 | 中 | 高 |

---

## 程式架構

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 定義狀態
class AgentState(TypedDict):
    messages: list

# 建立工作流程圖
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END}
)
workflow.add_edge("tools", "agent")
workflow.set_entry_point("agent")
app = workflow.compile()
```

---

## 應用場景

LangGraph 特別適合以下情境：

1. **多步驟研究任務**：先搜尋多個來源，整合後分析
2. **平行資料收集**：同時查詢多個 API，再彙整結果
3. **條件決策**：根據工具回傳的結果，選擇不同的後續路徑
4. **人機協作**（Human-in-the-Loop）：在特定步驟等待使用者確認

---

## 本專案中的狀態

目前第三階段為**選用功能（Optional O2）**，若需啟用需安裝：

```bash
pip install langchain==1.3.1 langchain-core==1.4.0 \
            langchain-google-genai==4.2.2 \
            langgraph==1.2.0 langgraph-prebuilt==1.1.0
```

> 注意：LangGraph 版本組合較為敏感，建議使用上述固定版本。
