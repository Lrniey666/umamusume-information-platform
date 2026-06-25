"""
app_agent_langchain/views.py

O2: LangChain ReAct Agent — 使用 LangChain 1.3.x + langchain-google-genai 4.x
結合本地 DB 工具與線上搜尋，由 ReAct Agent 動態決策工具呼叫順序。
"""
import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings


def chat_view(request):
    return render(request, 'app_agent_langchain/chat.html', {
        'model_name': settings.UMA_CHAT_MODEL,
    })


def _build_agent():
    """建立 LangChain Tool-Calling Agent（惰性初始化）

    注意：原本的 create_react_agent（文字格式 ReAct）與思考型模型（如 gemini-3.1-flash-lite）
    不相容，模型輸出的內部推理會干擾 ReAct 格式解析導致 500。
    改用 create_tool_calling_agent 使用原生 function calling，避免此問題。
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.tools import tool
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate
    from django.db.models import Q

    llm = ChatGoogleGenerativeAI(
        model=settings.UMA_CHAT_MODEL,
        google_api_key=os.getenv('GEMINI_API_KEY'),
        temperature=0.3,
    )

    @tool
    def search_announcements(query: str) -> str:
        """搜尋賽馬娘公告資料庫，輸入關鍵字，回傳相符的公告標題、日期、連結。"""
        from app_uma_news.models import GameAnnouncement
        results = GameAnnouncement.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-published_date')[:5]
        if not results:
            return f'找不到關於「{query}」的公告。'
        lines = [f'找到 {results.count()} 筆公告：']
        for ann in results:
            lines.append(
                f'- [ID:{ann.id}] {ann.title} | {ann.published_date}'
                + (f' | {ann.source_url}' if ann.source_url else '')
            )
        return '\n'.join(lines)

    @tool
    def list_by_category(category: str) -> str:
        """列出指定分類的最新公告。分類可選：活動、卡池、競賽、系統、其他。"""
        from app_uma_news.models import GameAnnouncement
        anns = GameAnnouncement.objects.filter(category=category).order_by('-published_date')[:8]
        if not anns:
            return f'找不到分類「{category}」的公告。'
        lines = [f'【{category}】最新 {anns.count()} 筆：']
        for ann in anns:
            lines.append(f'- {ann.title} ({ann.published_date})')
        return '\n'.join(lines)

    @tool
    def get_announcement_detail(announcement_id: int) -> str:
        """根據公告 ID 取得完整內容。"""
        from app_uma_news.models import GameAnnouncement
        try:
            ann = GameAnnouncement.objects.get(id=announcement_id)
            return (
                f'標題：{ann.title}\n'
                f'日期：{ann.published_date}\n'
                f'分類：{ann.category}\n'
                f'來源：{ann.source}\n'
                f'連結：{ann.source_url or "無"}\n'
                f'內容：{ann.content[:800]}'
            )
        except GameAnnouncement.DoesNotExist:
            return f'找不到 ID={announcement_id} 的公告。'

    tools = [search_announcements, list_by_category, get_announcement_detail]

    # Tool-Calling Agent 提示模板（支援思考型模型，不依賴文字格式解析）
    prompt = ChatPromptTemplate.from_messages([
        (
            'system',
            '你是「馬娘情報站 LangChain 助理」，專門回答賽馬娘 Pretty Derby 相關問題。\n'
            '回答使用繁體中文，引用資料來源時格式：（來源：[ID:xxx] 標題）。',
        ),
        ('placeholder', '{chat_history}'),
        ('human', '{input}'),
        ('placeholder', '{agent_scratchpad}'),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True, max_iterations=6)


_agent_executor = None


def _get_agent():
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = _build_agent()
    return _agent_executor


@csrf_exempt
@require_http_methods(['POST'])
def api_chat(request):
    body = json.loads(request.body or '{}')
    user_msg = body.get('message', '').strip()
    if not user_msg:
        return JsonResponse({'error': '訊息不得為空'}, status=400)

    if not os.getenv('GEMINI_API_KEY'):
        return JsonResponse({'error': 'GEMINI_API_KEY 未設定'}, status=500)

    try:
        agent = _get_agent()
        result = agent.invoke({'input': user_msg, 'chat_history': []})
        reply = result.get('output', '（無回覆）')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'reply': reply})


@csrf_exempt
@require_http_methods(['POST'])
def api_clear_history(request):
    global _agent_executor
    _agent_executor = None
    return JsonResponse({'status': 'ok', 'message': 'Agent 已重置'})
