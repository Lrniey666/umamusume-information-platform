import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from app_user_keyword_db.models import NewsData
from google import genai as google_genai
from google.genai import types as genai_types
import anthropic
import jieba
import jieba.posseg as pseg


logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-3.5-flash'
CLAUDE_MODEL = 'claude-sonnet-4-6'
GEMINI_IMAGE_MODEL = getattr(settings, 'GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image')
DEFAULT_TEXT_MODEL_CATALOG = [
    {
        'id': 'gemini_35_flash',
        'provider': 'gemini',
        'model': GEMINI_MODEL,
        'label': 'Gemini 3.5 Flash',
        'attrs': ['低延遲', '通用', '最新 GA'],
        'cost_label': '$',
    },
    {
        'id': 'gemini_35_pro',
        'provider': 'gemini',
        'model': 'gemini-3.5-pro',
        'label': 'Gemini 3.5 Pro',
        'attrs': ['高品質', '長文推理'],
        'cost_label': '$$$',
    },
    {
        'id': 'gemini_31_flash_lite',
        'provider': 'gemini',
        'model': 'gemini-3.1-flash-lite',
        'label': 'Gemini 3.1 Flash Lite',
        'attrs': ['超低成本', '快速'],
        'cost_label': '$',
    },
    {
        'id': 'claude_opus_48',
        'provider': 'claude',
        'model': 'claude-opus-4-8',
        'label': 'Claude Opus 4.8',
        'attrs': ['高品質', '深度推理', '最新 GA'],
        'cost_label': '$$$$',
    },
    {
        'id': 'claude_sonnet_46',
        'provider': 'claude',
        'model': CLAUDE_MODEL,
        'label': 'Claude Sonnet 4.6',
        'attrs': ['平衡', '主力'],
        'cost_label': '$$$',
    },
    {
        'id': 'claude_haiku_45',
        'provider': 'claude',
        'model': 'claude-haiku-4-5',
        'label': 'Claude Haiku 4.5',
        'attrs': ['低延遲', '低成本'],
        'cost_label': '$$',
    },
]

jieba.setLogLevel('ERROR')

NLQ_STOP_WORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '都', '很', '為', '以', '與', '及',
    '或', '等', '從', '將', '對', '由', '可以', '什麼', '為什麼', '怎麼', '哪個', '哪些',
    '幾個', '幾隻', '幾位', '最近', '請問', '告訴', '分析', '介紹', '說明', '解釋', '最',
    '更', '比較', '相關', '有關', '是否', '會不會', '能不能', '嗎', '呢', '吧', '啊', '喔',
    '哦', '那', '這', '它', '他', '她', '公告', '新聞', '賽馬娘',
}
NLQ_SIGNAL_WORDS = ['？', '?', '如何', '為何', '為什麼', '怎麼', '請問', '可以幫我', '想知道', '分析']


@dataclass
class NewsGenerationInput:
    query: str
    category: str = '全部'
    source: str = 'all'
    weeks: int = 4
    topk: int = 8
    provider: str = 'gemini'
    model_id: str = ''
    status: str = 'published'
    request_user: Any = None


def get_ai_news_text_model_catalog() -> list[dict]:
    raw_catalog = getattr(settings, 'AI_NEWS_TEXT_MODELS', None)
    source = raw_catalog if isinstance(raw_catalog, list) and raw_catalog else DEFAULT_TEXT_MODEL_CATALOG

    normalized = []
    for item in source:
        if not isinstance(item, dict):
            continue
        provider = str(item.get('provider', '')).strip().lower()
        model = str(item.get('model', '')).strip()
        model_id = str(item.get('id', '')).strip()
        label = str(item.get('label', model)).strip() or model
        if provider not in {'gemini', 'claude'} or not model or not model_id:
            continue
        attrs = item.get('attrs', [])
        if not isinstance(attrs, list):
            attrs = []
        normalized.append(
            {
                'id': model_id,
                'provider': provider,
                'model': model,
                'label': label,
                'attrs': [str(a).strip() for a in attrs if str(a).strip()],
                'cost_label': str(item.get('cost_label', '')).strip() or '$$',
            }
        )

    return normalized or DEFAULT_TEXT_MODEL_CATALOG


def get_ai_news_default_model_id(model_catalog: list[dict] | None = None) -> str:
    catalog = model_catalog or get_ai_news_text_model_catalog()
    preferred = str(getattr(settings, 'AI_NEWS_DEFAULT_TEXT_MODEL', '')).strip()
    if preferred and any(item['id'] == preferred for item in catalog):
        return preferred
    return catalog[0]['id']


def resolve_ai_news_text_model(model_id: str = '', provider: str = '') -> dict:
    catalog = get_ai_news_text_model_catalog()
    by_id = {item['id']: item for item in catalog}
    if model_id and model_id in by_id:
        return by_id[model_id]

    normalized_provider = (provider or '').strip().lower()
    if normalized_provider in {'gemini', 'claude'}:
        for item in catalog:
            if item['provider'] == normalized_provider:
                return item

    default_id = get_ai_news_default_model_id(catalog)
    return by_id.get(default_id, catalog[0])


def _is_natural_language_query(text: str) -> bool:
    if any(sig in text for sig in NLQ_SIGNAL_WORDS):
        return True
    if len(text) >= 10:
        return True
    return False


def _extract_terms_from_query(text: str, limit: int = 8) -> list[str]:
    keep_pos = {'n', 'nr', 'ns', 'nt', 'nz', 'ng', 'vn', 'an'}
    terms = []
    seen = set()

    for token in pseg.cut(text):
        word = token.word.strip()
        if len(word) < 2:
            continue
        if word in NLQ_STOP_WORDS:
            continue
        if not (token.flag[:1] in ('n', 'v') or token.flag in keep_pos):
            continue
        if word in seen:
            continue
        seen.add(word)
        terms.append(word)
        if len(terms) >= limit:
            break

    if terms:
        return terms

    # fallback：中英數切詞，避免完全無檢索詞
    raw_terms = re.findall(r'[\u4e00-\u9fff]{2,}|[A-Za-z0-9][A-Za-z0-9\-_]{1,}', text)
    for term in raw_terms:
        if term not in seen:
            seen.add(term)
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def _build_query_profile(query_text: str) -> dict:
    normalized = (query_text or '').strip()
    if not normalized:
        return {
            'raw_query': '',
            'query_mode': 'keyword',
            'search_terms': [],
            'intent': '',
        }

    is_nlq = _is_natural_language_query(normalized)
    terms = _extract_terms_from_query(normalized) if is_nlq else [t for t in normalized.split() if len(t.strip()) >= 2]
    if not terms and normalized:
        terms = [normalized]

    return {
        'raw_query': normalized,
        'query_mode': 'natural_language' if is_nlq else 'keyword',
        'search_terms': terms[:8],
        'intent': normalized if is_nlq else '',
    }


def _coerce_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r'\{[\s\S]*\}', text)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}


def _build_news_queryset(params: NewsGenerationInput, query_profile: dict):
    qs = NewsData.objects.exclude(content__isnull=True).exclude(content='')
    max_date = qs.aggregate(max_date=Max('date')).get('max_date')
    if not max_date:
        return qs.none()

    start_date = max_date - timedelta(weeks=params.weeks)
    qs = qs.filter(date__gte=start_date, date__lte=max_date)

    if params.category and params.category != '全部':
        qs = qs.filter(category=params.category)
    if params.source and params.source != 'all':
        qs = qs.filter(source=params.source)

    query_tokens = query_profile.get('search_terms', [])
    if query_tokens:
        search_q = Q()
        for token in query_tokens:
            search_q |= Q(title__icontains=token) | Q(content__icontains=token)
        filtered_qs = qs.filter(search_q)
        # 自然語言模式若檢索詞過嚴導致結果太少，退回時間/類別/來源範圍
        if query_profile.get('query_mode') == 'natural_language' and filtered_qs.count() < 12:
            return qs.order_by('-date')[:120]
        qs = filtered_qs
    return qs.order_by('-date')[:120]


def _summarize_context(news_rows, topk: int) -> tuple[list[str], list[dict]]:
    chunks = []
    references = []
    for row in news_rows[: max(20, topk * 4)]:
        body = (row.content or '').strip().replace('\n', ' ')
        body = re.sub(r'\s+', ' ', body)
        excerpt = body[:260]
        chunk = (
            f"日期: {row.date} | 類別: {row.category} | 來源: {row.source}\n"
            f"標題: {row.title}\n"
            f"摘要: {excerpt}"
        )
        chunks.append(chunk)
        references.append(
            {
                'title': row.title,
                'date': str(row.date) if row.date else '',
                'source': row.source,
                'category': row.category,
                'link': row.link or '',
                'photo_link': row.photo_link or '',
            }
        )
    return chunks[: max(8, topk)], references[:12]


def _prompt_for_news(query: str, chunks: list[str], query_profile: dict) -> str:
    context = '\n\n---\n\n'.join(chunks)
    query_mode = query_profile.get('query_mode', 'keyword')
    search_terms = '、'.join(query_profile.get('search_terms', []))
    intent = query_profile.get('intent', '')
    return (
        "請依據提供的資料片段，生成一則專業新聞稿，輸出必須是 JSON 物件。\n"
        "JSON schema:\n"
        "{\n"
        '  "title": "string",\n'
        '  "subtitle": "string",\n'
        '  "summary": "string",\n'
        '  "content": "string"\n'
        "}\n"
        "規則:\n"
        "1) 使用繁體中文。\n"
        "2) 語氣需像遊戲媒體專欄，避免口語。\n"
        "3) title 18~32 字，subtitle 20~40 字，summary 80~140 字。\n"
        "4) content 使用 3~5 段，含趨勢觀察與玩家影響。\n"
        "5) 不可捏造日期與數字，無法確認時請用『近期』等保守用語。\n"
        f"查詢模式: {query_mode}\n"
        f"查詢主題: {query}\n\n"
        f"檢索詞: {search_terms or '（無）'}\n"
        f"使用者原始意圖: {intent or '（關鍵詞檢索）'}\n\n"
        f"參考資料:\n{context}"
    )


def _generate_with_model(provider: str, prompt: str, model_name: str = '') -> dict:
    provider = (provider or 'gemini').lower()
    if provider == 'claude':
        if not settings.ANTHROPIC_API_KEY:
            return {}
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=model_name or CLAUDE_MODEL,
            max_tokens=1800,
            temperature=0.5,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = msg.content[0].text if msg.content else ''
        return _coerce_json(text)

    if not settings.GEMINI_API_KEY:
        return {}
    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=model_name or GEMINI_MODEL,
        config=genai_types.GenerateContentConfig(
            temperature=0.45,
            max_output_tokens=1800,
            response_mime_type='application/json',
        ),
        contents=prompt,
    )
    return _coerce_json(resp.text or '')


def _build_fallback_article(query: str, references: list[dict]) -> dict:
    top_sources = Counter([item.get('source', 'unknown') for item in references]).most_common(3)
    src_str = '、'.join([f'{src}({count})' for src, count in top_sources]) or '多來源'
    return {
        'title': f'【AI 快訊】{query} 近期動態整理',
        'subtitle': '依據站內已收錄新聞自動彙整，提供快速趨勢閱讀',
        'summary': f'本則內容由系統依據 {src_str} 資料交叉整理，聚焦「{query}」近期聲量與討論脈絡。',
        'content': (
            f'圍繞「{query}」的內容近期仍保持能見度，相關討論分布於多個來源。'
            '整體訊息顯示，社群關注焦點集中在活動節奏、角色養成策略與版本調整帶來的體感差異。\n\n'
            '從整理到的標題與內文片段觀察，官方資訊與玩家回饋之間形成快速互動，'
            '當新活動或卡池資訊釋出時，討論量通常在短期內明顯升溫。\n\n'
            '建議玩家持續關注官方公告更新與社群實測經驗，'
            '可更快掌握版本重點並調整培育與資源配置策略。'
        ),
    }


def _build_cover_prompt(query: str, payload: dict, references: list[dict], query_profile: dict) -> str:
    title = (payload.get('title') or '').strip()
    subtitle = (payload.get('subtitle') or '').strip()
    source_tags = '、'.join(
        sorted({f"{item.get('source', '')}/{item.get('category', '')}" for item in references[:6] if item.get('source')})
    )
    return (
        "請生成一張 16:9 的新聞封面圖，風格為專業遊戲媒體頭版。"
        "主題為賽馬娘（Uma Musume），畫面要符合主題與新聞內容，並採用日本動漫畫風。"
        "請避免血腥暴力。"
        "若有文字元素，以繁體中文優先。"
        f"主題關鍵詞：{query_profile.get('search_terms') or [query]}。"
        f"標題：{title}。"
        f"副標：{subtitle}。"
        f"資料脈絡：{source_tags or '多來源新聞整合'}。"
    )


def _save_generated_image(image_bytes: bytes, mime_type: str, base_name: str) -> str:
    if not image_bytes:
        return ''

    media_root = Path(getattr(settings, 'MEDIA_ROOT', Path(settings.BASE_DIR) / 'media'))
    target_dir = media_root / 'ai_news_covers'
    target_dir.mkdir(parents=True, exist_ok=True)

    ext_map = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
    }
    ext = ext_map.get((mime_type or '').lower(), '.png')
    target_path = target_dir / f'{base_name}{ext}'
    target_path.write_bytes(image_bytes)

    media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
    return f'{media_url}/ai_news_covers/{target_path.name}'


def _generate_cover_image_with_gemini(query: str, payload: dict, references: list[dict], query_profile: dict) -> str:
    """
    封面圖生成固定走 Gemini，與文字 provider 解耦。
    即使文字使用 Claude，圖片仍由 Gemini image model 生成。
    """
    if not settings.GEMINI_API_KEY:
        return ''

    prompt = _build_cover_prompt(query, payload, references, query_profile)
    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=['IMAGE', 'TEXT'],
                temperature=0.7,
            ),
        )
        parts = response.candidates[0].content.parts if response.candidates else []
        for part in parts:
            inline_data = getattr(part, 'inline_data', None)
            if inline_data and getattr(inline_data, 'data', None):
                ts = timezone.localtime().strftime('%Y%m%d_%H%M%S_%f')
                mime = getattr(inline_data, 'mime_type', 'image/png')
                return _save_generated_image(bytes(inline_data.data), mime, f'ai_news_{ts}')
    except Exception:
        logger.exception('Gemini 封面圖生成失敗，將改用來源圖片 fallback')
    return ''


def _cover_fallback_from_references(references: list[dict]) -> str:
    for item in references:
        if item.get('photo_link'):
            return str(item['photo_link'])[:600]
    for item in references:
        if item.get('link'):
            return str(item['link'])[:600]
    return ''


def generate_ai_news_article(params: NewsGenerationInput) -> dict:
    from .models import GeneratedNewsArticle

    query_profile = _build_query_profile(params.query)
    text_model = resolve_ai_news_text_model(params.model_id, params.provider)
    rows = list(_build_news_queryset(params, query_profile))
    if not rows:
        return {'error': '查無可用資料，請調整條件後再試。'}

    chunks, references = _summarize_context(rows, params.topk)
    prompt = _prompt_for_news(params.query, chunks, query_profile)

    payload = {}
    try:
        payload = _generate_with_model(
            text_model['provider'],
            prompt,
            model_name=text_model['model'],
        )
    except Exception:
        logger.exception('AI 新聞生成失敗，將使用 fallback')
    if not payload:
        payload = _build_fallback_article(params.query, references)

    cover_image_url = _generate_cover_image_with_gemini(params.query, payload, references, query_profile)
    if not cover_image_url:
        cover_image_url = _cover_fallback_from_references(references)

    article = GeneratedNewsArticle.objects.create(
        query=params.query,
        category=params.category,
        source=params.source,
        weeks=params.weeks,
        topk=params.topk,
        title=(payload.get('title') or '').strip()[:220] or f'【AI】{params.query} 快訊',
        subtitle=(payload.get('subtitle') or '').strip()[:320],
        summary=(payload.get('summary') or '').strip(),
        content=(payload.get('content') or '').strip(),
        cover_image_url=cover_image_url[:600],
        source_chunks=chunks[:12],
        source_links=references[:8],
        status=params.status,
        created_by=params.request_user if getattr(params.request_user, 'is_authenticated', False) else None,
    )

    return {
        'id': article.pk,
        'title': article.title,
        'subtitle': article.subtitle,
        'summary': article.summary,
        'content': article.content,
        'cover_image_url': article.cover_image_url,
        'status': article.status,
        'created_at': article.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'source_links': article.source_links,
        'source_count': len(rows),
        'query_mode': query_profile.get('query_mode', 'keyword'),
        'search_terms': query_profile.get('search_terms', []),
        'text_model': {
            'id': text_model['id'],
            'provider': text_model['provider'],
            'model': text_model['model'],
            'label': text_model['label'],
        },
        'image_model': {
            'provider': 'gemini',
            'model': GEMINI_IMAGE_MODEL,
        },
    }
