"""
app_agent_langgraph/views.py

O3: LangGraph 狀態圖 Agent 視圖
Phase 3 — 顯式狀態機架構，多輪對話支援。
"""
import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from langchain_core.messages import HumanMessage

_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        from .graph_core.graph_agent import build_graph
        _compiled_graph = build_graph()
    return _compiled_graph


def chat_view(request):
    return render(request, 'app_agent_langgraph/chat.html', {
        'model_name': settings.UMA_CHAT_MODEL,
    })


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
        graph = _get_graph()
        result = graph.invoke({
            'messages': [HumanMessage(content=user_msg)],
            'tool_calls_count': 0,
        })
        # 取最後一個 AI 訊息作為回覆
        reply = ''
        for msg in reversed(result['messages']):
            if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_call_id'):
                reply = msg.content
                break
        return JsonResponse({'reply': reply or '（Agent 未能生成回覆）'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_clear_history(request):
    global _compiled_graph
    _compiled_graph = None
    return JsonResponse({'status': 'ok', 'message': 'Graph 已重置'})
