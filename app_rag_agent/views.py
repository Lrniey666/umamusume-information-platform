import os
import json
import pickle
import numpy as np
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.conf import settings
from google import genai
from google.genai import types as genai_types

from app_uma_news.models import GameAnnouncement

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / 'app_rag_uma' / 'index'

EMBED_MODEL = 'gemini-embedding-001'

_faiss_index = None
_texts = None

def _load_index():
    global _faiss_index, _texts
    if _faiss_index is not None:
        return True
    faiss_path = INDEX_DIR / 'uma_knowledge.faiss'
    texts_path = INDEX_DIR / 'uma_knowledge_texts.pkl'
    if not faiss_path.exists() or not texts_path.exists():
        return False
    try:
        import faiss
        _faiss_index = faiss.read_index(str(faiss_path))
        with open(texts_path, 'rb') as f:
            _texts = pickle.load(f)
        return True
    except Exception:
        return False

def _search_rag(query: str, client, k: int = 5) -> list:
    """語意搜尋 FAISS 索引"""
    if not _load_index():
        return []
    try:
        resp = client.models.embed_content(model=EMBED_MODEL, contents=[query])
        vec = np.array([resp.embeddings[0].values], dtype=np.float32)
        scores, indices = _faiss_index.search(vec, k)
        return [_texts[i] for i in indices[0] if i < len(_texts)]
    except Exception:
        return []

def _define_tools():
    """定義 Agentic 工具"""
    search_announcements_decl = genai_types.FunctionDeclaration(
        name='search_uma_announcements',
        description='以語意搜尋方式查詢賽馬娘公告與知識庫文件，適合模糊問題或內容查詢',
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                'query': genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description='搜尋關鍵字或問題'
                )
            },
            required=['query']
        )
    )
    list_by_category_decl = genai_types.FunctionDeclaration(
        name='list_announcements_by_category',
        description='精確列出指定分類的最新公告（活動/卡池/競賽/系統/其他）',
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                'category': genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description='分類名稱，可選：活動、卡池、競賽、系統、其他'
                ),
                'limit': genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description='最多返回幾筆，預設 5'
                )
            },
            required=['category']
        )
    )
    return [genai_types.Tool(function_declarations=[search_announcements_decl, list_by_category_decl])]

def _call_tool(name: str, args: dict, client) -> str:
    """執行工具呼叫"""
    if name == 'search_uma_announcements':
        query = args.get('query', '')
        chunks = _search_rag(query, client)
        db_results = GameAnnouncement.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-published_date')[:3]
        result = '【語意搜尋結果】\n'
        if chunks:
            result += '\n'.join(f'- {c[:300]}' for c in chunks[:3])
        if db_results:
            result += '\n\n【資料庫公告】\n'
            for ann in db_results:
                result += f'- [ID:{ann.id}] {ann.title} ({ann.published_date}) {ann.source_url or ""}\n'
        return result or '（無相關資料）'

    elif name == 'list_announcements_by_category':
        category = args.get('category', '')
        limit = min(int(args.get('limit', 5)), 10)
        anns = GameAnnouncement.objects.filter(category=category).order_by('-published_date')[:limit]
        if not anns:
            return f'（找不到分類「{category}」的公告）'
        lines = [f'【{category}】最新 {anns.count()} 筆公告：']
        for ann in anns:
            lines.append(f'- [ID:{ann.id}] {ann.title} | {ann.published_date} | {ann.source_url or "無連結"}')
        return '\n'.join(lines)

    return '（工具不存在）'

def chat_view(request):
    return render(request, 'app_rag_agent/chat.html', {
        'model_name': settings.UMA_CHAT_MODEL,
    })

@csrf_exempt
@require_http_methods(['POST'])
def api_chat(request):
    body = json.loads(request.body or '{}')
    user_msg = body.get('message', '').strip()
    if not user_msg:
        return JsonResponse({'error': '訊息不得為空'}, status=400)

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return JsonResponse({'error': 'GEMINI_API_KEY 未設定'}, status=500)

    client = genai.Client(api_key=api_key)
    _load_index()

    history = request.session.get('rag_agent_history', [])

    system_prompt = (
        '你是「馬娘情報站 Agentic RAG 助理」，專門回答賽馬娘 Pretty Derby 相關問題。'
        '你有兩個工具：search_uma_announcements（語意搜尋）和 list_announcements_by_category（精確分類查詢）。'
        '回答時必須引用來源，格式：（來源：[ID:xxx] 標題）。'
        '回答使用繁體中文。'
    )

    messages = list(history) + [{'role': 'user', 'parts': [{'text': user_msg}]}]
    tools = _define_tools()

    for _ in range(5):
        try:
            resp = client.models.generate_content(
                model=settings.UMA_CHAT_MODEL,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tools,
                    temperature=0.3,
                ),
                contents=messages,
            )
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        candidate = resp.candidates[0] if resp.candidates else None
        if not candidate:
            break

        part = candidate.content.parts[0] if candidate.content.parts else None
        if not part:
            break

        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            tool_result = _call_tool(fc.name, dict(fc.args), client)
            messages.append({'role': 'model', 'parts': [{'function_call': {'name': fc.name, 'args': dict(fc.args)}}]})
            messages.append({'role': 'user', 'parts': [{'function_response': {'name': fc.name, 'response': {'result': tool_result}}}]})
            continue

        answer = part.text if hasattr(part, 'text') else str(part)
        history.append({'role': 'user', 'parts': [{'text': user_msg}]})
        history.append({'role': 'model', 'parts': [{'text': answer}]})
        request.session['rag_agent_history'] = history[-20:]

        return JsonResponse({'reply': answer, 'history_len': len(history) // 2})

    return JsonResponse({'reply': '（Agent 未能完成回答）', 'history_len': 0})

@csrf_exempt
@require_http_methods(['POST'])
def api_clear_history(request):
    request.session.pop('rag_agent_history', None)
    return JsonResponse({'status': 'ok', 'message': '對話歷史已清除'})
