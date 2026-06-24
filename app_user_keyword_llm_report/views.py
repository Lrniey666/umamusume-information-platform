from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from app_user_keyword.views import filter_dataFrame, api_get_top_userkey
from app_user_keyword_sentiment.views import api_get_userkey_sentiment
import json
import os
import jieba
import jieba.posseg as pseg
from dotenv import load_dotenv
from pathlib import Path

# 明確指定專案根目錄的 .env
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

# ── google-genai 2.9.0（取代已棄用的 google-generativeai）──
from google import genai as google_genai
from google.genai import types as genai_types

# ── Anthropic Claude（雙模型選擇）──
import anthropic
from .models import GeneratedNewsArticle
from .services_ai_news import (
    NewsGenerationInput,
    generate_ai_news_article,
    get_ai_news_default_model_id,
    get_ai_news_text_model_catalog,
)

jieba.setLogLevel('ERROR')

GEMINI_MODEL    = "gemini-3.5-flash"
CLAUDE_MODEL    = "claude-sonnet-4-6"

# ── 自然語言問句處理 ──────────────────────────────────────────

# 問句停用詞（問句語氣詞、功能詞）
_NLQ_STOP = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '都', '很',
    '為', '以', '與', '及', '或', '等', '從', '將', '對', '由', '可以',
    '什麼', '為什麼', '怎麼', '哪個', '哪些', '幾個', '幾隻', '幾位',
    '最近', '請問', '告訴', '分析', '介紹', '說明', '解釋',
    '最', '更', '比較', '相關', '有關', '是否', '會不會', '能不能',
    '嗎', '呢', '吧', '啊', '喔', '哦', '那', '這', '它', '他', '她',
    '公告', '遊戲', '賽馬娘',
}

_NLQ_SIGNALS = ['？', '?', '嗎', '呢', '如何', '怎麼', '為什麼',
                '哪個', '哪些', '請問', '什麼', '介紹', '分析', '告訴']

def _is_natural_language_query(text: str) -> bool:
    """判斷輸入是否為自然語言問句（而非純關鍵詞）"""
    if any(sig in text for sig in _NLQ_SIGNALS):
        return True
    # 無空格且超過 5 字，視為問句
    if ' ' not in text and len(text) > 5:
        return True
    return False

def _extract_keywords(text: str) -> list[str]:
    """用 jieba 從自然語言問句中抽取名詞/動名詞關鍵詞"""
    keep_pos = {'n', 'nr', 'ns', 'nt', 'nz', 'ng', 'vn', 'an'}
    words = []
    seen = set()
    for w in pseg.cut(text):
        word = w.word.strip()
        if (len(word) >= 2
                and word not in _NLQ_STOP
                and (w.flag[:1] in ('n', 'v') or w.flag in keep_pos)):
            if word not in seen:
                seen.add(word)
                words.append(word)
    return words if words else [t for t in text.split() if len(t) >= 2]


def home(request):
    return render(request, 'app_user_keyword_llm_report/home.html')


def get_userkey_data(request):
    original_query = request.POST.get('userkey', '').strip()
    cate  = request.POST.get('cate', '全部')
    cond  = request.POST.get('cond', 'or')
    weeks = int(request.POST.get('weeks', 52))

    # ── 自動問句處理 ──────────────────────────────────────────
    is_nlq = _is_natural_language_query(original_query)
    if is_nlq:
        key  = _extract_keywords(original_query)
        cond = 'or'   # 問句一律用 OR 確保有結果
        print(f"[NLQ] 原始問句: {original_query!r}  →  抽詞: {key}")
    else:
        key = original_query.split()

    df_query = filter_dataFrame(key, cond, cate, weeks)

    if len(df_query) == 0:
        # 若 NLQ 仍無結果，放寬到全部類別再試一次
        if is_nlq and cate != '全部':
            df_query = filter_dataFrame(key, cond, '全部', weeks)
        if len(df_query) == 0:
            return {'error': f'查無相關公告（搜尋詞：{"、".join(key)}），請嘗試其他關鍵字或放寬篩選條件。'}
    
   
    # (1) 情緒分析資料
    try:
        response_from_sentiment = api_get_userkey_sentiment(request)
        response_from_sentiment = json.loads(response_from_sentiment.content.decode('utf-8'))
    except Exception as e:
        print(f"Error calling api_get_userkey_sentiment: {e}")
        return {'error': '無法取得情緒分析資料，請稍後再試。'}

    if 'error' in response_from_sentiment:
        return {'error': f"情緒分析：{response_from_sentiment['error']}"}

    # (2) 關鍵詞聲量資料
    try:
        response_from_userkeyword = api_get_top_userkey(request)
        response_from_userkeyword = json.loads(response_from_userkeyword.content.decode('utf-8'))
    except Exception as e:
        print(f"Error calling api_get_top_userkey: {e}")
        return {'error': '無法取得關鍵詞頻率資料，請稍後再試。'}

    if 'error' in response_from_userkeyword:
        return {'error': f"聲量查詢：{response_from_userkeyword['error']}"}

    return response_from_userkeyword, response_from_sentiment, original_query, key


# API endpoint for getting userkey data including occurrence, time frequency, sentiment analysis, etc. from internal modules, and return the combined data as a dictionary
# 取得使用者輸入的關鍵字，並從內部模組取得相關的分析資料，最後將資料合併成一個字典返回
@csrf_exempt
def api_get_userkey_data(request):
    
    result = get_userkey_data(request)

    if isinstance(result, dict) and 'error' in result:
        return JsonResponse(result)

    response_from_userkeyword, response_from_sentiment, _orig_q, _keys = result
    combined_response = {**response_from_userkeyword, **response_from_sentiment}
    return JsonResponse(combined_response)

# API endpoint for getting LLM report
# 取得使用者輸入的關鍵字，從內部模組取得相關的分析資料，然後將資料整理成提示詞，最後呼叫AI大型模型的API來生成分析報告，並將報告內容返回
@csrf_exempt
def api_get_userkey_llm_report(request):
    
    result = get_userkey_data(request)

    if isinstance(result, dict) and 'error' in result:
        return JsonResponse(result)

    response_from_userkeyword, response_from_sentiment, original_query, search_keys = result

    key_occurrence_cat = response_from_userkeyword['key_occurrence_cat']
    key_time_freq      = response_from_userkeyword['key_time_freq']
    key_freq_cat       = response_from_userkeyword['key_freq_cat']

    sentiCount    = response_from_sentiment['sentiCount']
    line_data_pos = response_from_sentiment['data_pos']
    line_data_neg = response_from_sentiment['data_neg']

    # ── 判斷是否為問句，調整 prompt 語氣 ─────────────────────
    is_question = _is_natural_language_query(original_query)
    keys_str    = '、'.join(search_keys)

    if is_question:
        task_instruction = (
            f"使用者提出了以下問題：「{original_query}」\n"
            f"請根據下方從遊戲公告資料庫中檢索到的數據（搜尋詞：{keys_str}），"
            f"直接回答這個問題，並補充相關的聲量與情緒分析，使用繁體中文、Markdown 排版。"
        )
        system_prompt = (
            "你是一位熟悉多媒體企劃《賽馬娘 Pretty Derby》的數據分析師，"
            "擅長根據官方公告資料回答玩家提問並提供深度分析。"
            "請以問答形式直接回應使用者的問題，並附上數據佐證，字數不少於 400 字。"
        )
    else:
        task_instruction = (
            f"使用者想了解關鍵詞「{original_query}」在遊戲公告中的表現。\n"
            f"請根據下方數據，撰寫一份至少 500 字的專業分析報告，使用繁體中文、Markdown 排版。"
        )
        system_prompt = (
            "你是一位資深的遊戲社群數據分析專家，專精於手機遊戲《賽馬娘 Pretty Derby》。"
            "請根據提供的公告聲量與情緒數據，產出詳細的分析報告。"
        )

    prompt = f'''{task_instruction}

### (1) 聲量分析
關鍵詞在公告中的出現次數（篇數）：
{key_occurrence_cat}

關鍵詞出現頻率的時間趨勢：
{key_time_freq}

### (2) 情緒分析
情緒分布（正面 / 中立 / 負面篇數）：
{sentiCount}

情緒隨時間的變化趨勢：
- 正面情緒趨勢：{line_data_pos}
- 負面情緒趨勢：{line_data_neg}

### (3) 輸出格式要求
請包含以下段落：
1. 標題
2. 摘要（直接回答問題或說明主題）
3. 關鍵詞
4. 詳細分析內容
5. 建議
6. 總結
'''
    print(prompt)
    
    
    # ── 雙模型路由：Gemini 3.5 Flash 或 Claude Sonnet 4.6 ──────────
    provider = request.POST.get('model_provider', 'gemini').lower()

    try:
        if provider == 'claude':
            anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
            if not anthropic_key:
                return JsonResponse({'error': 'Claude API 金鑰未設定，請在 .env 加入 ANTHROPIC_API_KEY。'})
            claude_client = anthropic.Anthropic(api_key=anthropic_key)
            msg = claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            report_content = msg.content[0].text
        else:
            gemini_key = os.getenv('GEMINI_API_KEY', '')
            if not gemini_key:
                return JsonResponse({'error': 'Gemini API 金鑰未設定，請在 .env 加入 GEMINI_API_KEY。'})
            gemini_client = google_genai.Client(api_key=gemini_key)
            gemini_resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=2048,
                    temperature=0.7,
                ),
                contents=prompt,
            )
            report_content = gemini_resp.text
        print(report_content)
    except Exception as e:
        print("Error:", str(e))
        return JsonResponse({'error': f'AI 報告生成失敗，請稍後再試。（{type(e).__name__}）'})
    
    # 取得AI生成的報告
    response_report = {
        'report': report_content
        #'report': markdown.markdown(report_content)
    }
    
    # Combine dictionaries correctly
    return JsonResponse(response_report)
    
print("app_user_keyword_llm_report was loaded!")


def _safe_int(value, default, min_value=None, max_value=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None:
        parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def _safe_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return default


@csrf_exempt
@require_http_methods(['POST'])
def api_generate_ai_news(request):
    payload = request.POST.dict() if request.POST else {}
    if not payload and request.body:
        try:
            payload = json.loads(request.body)
        except Exception:
            payload = {}

    query = str(payload.get('query', '')).strip()
    if len(query) < 2:
        return JsonResponse({'error': 'query 至少需 2 個字元。'}, status=400)

    category = str(payload.get('category', '全部')).strip() or '全部'
    source = str(payload.get('source', 'all')).strip() or 'all'
    provider = str(payload.get('provider', 'gemini')).strip().lower()
    model_id = str(payload.get('model_id', '')).strip()
    status = 'published' if _safe_bool(payload.get('auto_publish', True), True) else 'draft'

    params = NewsGenerationInput(
        query=query,
        category=category,
        source=source,
        weeks=_safe_int(payload.get('weeks', 4), default=4, min_value=1, max_value=52),
        topk=_safe_int(payload.get('topk', 8), default=8, min_value=3, max_value=20),
        provider=provider if provider in {'gemini', 'claude'} else 'gemini',
        model_id=model_id,
        status=status,
        request_user=request.user,
    )
    result = generate_ai_news_article(params)
    if 'error' in result:
        return JsonResponse(result, status=422)
    return JsonResponse({'ok': True, 'news': result})


@require_http_methods(['GET'])
def api_latest_ai_news(request):
    try:
        limit = _safe_int(request.GET.get('limit', 3), default=3, min_value=1, max_value=12)
        status = str(request.GET.get('status', 'published')).strip()

        qs = GeneratedNewsArticle.objects.all()
        if status in {GeneratedNewsArticle.STATUS_DRAFT, GeneratedNewsArticle.STATUS_PUBLISHED}:
            qs = qs.filter(status=status)

        news_list = []
        for item in qs[:limit]:
            news_list.append(
                {
                    'id': item.pk,
                    'title': item.title,
                    'subtitle': item.subtitle,
                    'summary': item.summary,
                    'content': item.content,
                    'cover_image_url': item.cover_image_url,
                    'source_links': item.source_links if isinstance(item.source_links, list) else [],
                    'status': item.status,
                    'query': item.query,
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
                }
            )

        return JsonResponse({'has_news': bool(news_list), 'news': news_list})
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('api_latest_ai_news 發生錯誤')
        return JsonResponse({'has_news': False, 'news': [], 'error': str(exc)}, status=200)


@require_http_methods(['GET'])
def api_ai_news_admin_list(request):
    try:
        limit = _safe_int(request.GET.get('limit', 20), default=20, min_value=1, max_value=100)
        news_list = []
        for item in GeneratedNewsArticle.objects.all()[:limit]:
            news_list.append(
                {
                    'id': item.pk,
                    'title': item.title,
                    'query': item.query,
                    'status': item.status,
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
                    'source_count': len(item.source_links or []),
                }
            )
        return JsonResponse({'items': news_list})
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('api_ai_news_admin_list 發生錯誤')
        return JsonResponse({'items': [], 'error': str(exc)}, status=200)


@require_http_methods(['GET'])
def api_ai_news_model_options(request):
    catalog = get_ai_news_text_model_catalog()
    default_id = get_ai_news_default_model_id(catalog)
    return JsonResponse(
        {
            'items': catalog,
            'default_model_id': default_id,
            'image_generation': {
                'provider': 'gemini',
                'note': '封面圖生成固定使用 Gemini 圖像模型（與文字模型解耦）',
            },
        }
    )


@csrf_exempt
@require_http_methods(['POST'])
def api_ai_news_toggle_status(request, news_id):
    try:
        item = GeneratedNewsArticle.objects.get(pk=news_id)
    except GeneratedNewsArticle.DoesNotExist:
        return JsonResponse({'error': '找不到新聞'}, status=404)

    item.status = (
        GeneratedNewsArticle.STATUS_DRAFT
        if item.status == GeneratedNewsArticle.STATUS_PUBLISHED
        else GeneratedNewsArticle.STATUS_PUBLISHED
    )
    item.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'ok': True, 'status': item.status})


@csrf_exempt
@require_http_methods(['POST'])
def api_ai_news_delete(request, news_id):
    try:
        item = GeneratedNewsArticle.objects.get(pk=news_id)
    except GeneratedNewsArticle.DoesNotExist:
        return JsonResponse({'error': '找不到新聞'}, status=404)
    item.delete()
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def api_ai_news_detail(request, news_id):
    try:
        item = GeneratedNewsArticle.objects.get(pk=news_id)
    except GeneratedNewsArticle.DoesNotExist:
        return JsonResponse({'error': '找不到新聞'}, status=404)

    return JsonResponse({
        'id': item.pk,
        'title': item.title,
        'subtitle': item.subtitle,
        'summary': item.summary,
        'content': item.content,
        'cover_image_url': item.cover_image_url,
        'source_links': item.source_links if isinstance(item.source_links, list) else [],
        'source_chunks': item.source_chunks if isinstance(item.source_chunks, list) else [],
        'status': item.status,
        'query': item.query,
        'category': item.category,
        'source': item.source,
        'weeks': item.weeks,
        'topk': item.topk,
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': item.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        'created_by': str(item.created_by) if item.created_by else '系統',
    })
