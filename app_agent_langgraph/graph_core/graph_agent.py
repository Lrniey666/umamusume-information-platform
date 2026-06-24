"""
app_agent_langgraph/graph_core/graph_agent.py

O3: LangGraph 狀態圖 Agent
Phase 3 — 使用 LangGraph 建構顯式狀態機，更可控的 Agent 流程。
"""
import os
from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.graph import StateGraph, END
from .state import AgentState


SYSTEM_MSG = SystemMessage(content=(
    '你是「馬娘情報站 LangGraph Agent」，使用狀態圖架構提供更穩定的推理流程。'
    '你有工具可搜尋公告、按分類查詢、取得詳情。'
    '回答使用繁體中文，必須引用資料來源。'
))


def _make_tools():
    @tool
    def search_announcements(query: str) -> str:
        """搜尋賽馬娘公告，輸入關鍵字，回傳相符公告。"""
        from django.db.models import Q
        from app_uma_news.models import GameAnnouncement
        results = GameAnnouncement.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-published_date')[:5]
        if not results:
            return f'找不到「{query}」的公告。'
        return '\n'.join(
            f'[ID:{a.id}] {a.title} | {a.published_date} | {a.source_url or "無連結"}'
            for a in results
        )

    @tool
    def list_by_category(category: str) -> str:
        """列出指定分類的公告（活動/卡池/競賽/系統/其他）。"""
        from app_uma_news.models import GameAnnouncement
        anns = GameAnnouncement.objects.filter(category=category).order_by('-published_date')[:6]
        if not anns:
            return f'找不到分類「{category}」的公告。'
        return f'【{category}】\n' + '\n'.join(f'- {a.title} ({a.published_date})' for a in anns)

    @tool
    def get_announcement_detail(announcement_id: int) -> str:
        """根據公告 ID 取得完整內容。"""
        from app_uma_news.models import GameAnnouncement
        try:
            a = GameAnnouncement.objects.get(id=announcement_id)
            return f'標題：{a.title}\n日期：{a.published_date}\n分類：{a.category}\n內容：{a.content[:600]}'
        except GameAnnouncement.DoesNotExist:
            return f'找不到 ID={announcement_id} 的公告。'

    return [search_announcements, list_by_category, get_announcement_detail]


def build_graph():
    """建立 LangGraph 狀態圖"""
    tools = _make_tools()
    tool_map = {t.name: t for t in tools}

    llm = ChatGoogleGenerativeAI(
        model=settings.UMA_CHAT_MODEL,
        google_api_key=os.getenv('GEMINI_API_KEY'),
        temperature=0.3,
    ).bind_tools(tools)

    # ── 節點：模型推理 ──
    def call_model(state: AgentState) -> dict:
        messages = [SYSTEM_MSG] + state['messages']
        response = llm.invoke(messages)
        return {
            'messages': [response],
            'tool_calls_count': state.get('tool_calls_count', 0),
        }

    # ── 節點：工具執行 ──
    def call_tools(state: AgentState) -> dict:
        last = state['messages'][-1]
        tool_results = []
        count = state.get('tool_calls_count', 0)

        for tc in last.tool_calls:
            tool_fn = tool_map.get(tc['name'])
            if tool_fn:
                try:
                    result = tool_fn.invoke(tc['args'])
                except Exception as e:
                    result = f'工具執行失敗: {e}'
            else:
                result = f'找不到工具: {tc["name"]}'

            tool_results.append(
                ToolMessage(content=str(result), tool_call_id=tc['id'])
            )
            count += 1

        return {'messages': tool_results, 'tool_calls_count': count}

    # ── 路由：決定下一步 ──
    def should_continue(state: AgentState) -> str:
        last = state['messages'][-1]
        # 超過工具呼叫上限 → 結束
        if state.get('tool_calls_count', 0) >= 8:
            return END
        # 有工具呼叫 → 執行工具
        if hasattr(last, 'tool_calls') and last.tool_calls:
            return 'call_tools'
        # 純文字回覆 → 結束
        return END

    # ── 建立圖 ──
    graph = StateGraph(AgentState)
    graph.add_node('call_model', call_model)
    graph.add_node('call_tools', call_tools)
    graph.set_entry_point('call_model')
    graph.add_conditional_edges('call_model', should_continue, {
        'call_tools': 'call_tools',
        END: END,
    })
    graph.add_edge('call_tools', 'call_model')

    return graph.compile()
