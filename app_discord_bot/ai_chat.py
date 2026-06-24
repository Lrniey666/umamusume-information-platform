"""
@UMA Info AI 問答（含圖片讀取與 Gemini 視覺分析）
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

logger = logging.getLogger(__name__)

# 單張上限 4MB、最多 4 張（控制 token 與 API 成本）
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGES = 4
ALLOWED_IMAGE_MIMES = frozenset({
    'image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif',
})

DEFAULT_IMAGE_PROMPT = '請分析使用者附上的圖片；若與賽馬娘 Pretty Derby 相關，請說明內容並提供實用資訊。'


def _build_system_prompt(context: str) -> str:
    lines = [
        '- 你是「 UMA Info Bot」，活動於賽馬娘文化圈、網路及 Discort 的機器人也是社群的一份子。',
        '- 請用繁體中文回答(除非用戶使用或要求用其他語言)，語氣親切有趣、資訊精準、且具有於社群的親和力及活力，不要太有機器或 ai 感覺像是社群成員正常聊天即可。',
        '- 回答長度控制在 300 字以內，除非有必要。',
        '- 禁止生成涉及敏感現實政治、色情、暴力等不當內容，請婉拒回應並轉移話題。',
        '- 你具備**讀取與分析圖片**的能力：使用者可能附上遊戲截圖、活動公告、角色立繪、育成面板、梗圖、藝術圖、同人圖、漫畫圖、小說插圖等，請依可見文字與畫面內容作答。',
        '- 你會輿情分析並簡單直白的說明；文字問答時可參考情報資料庫，圖片分析時以視覺內容為主。',
        "- 查詢相關趨勢或議題時，依據指定的類別取3個關鍵詞，若沒有指定類別，預設使用全部類別，呼叫 `get_top_keywords`。\n"
        "- 查詢熱門關鍵人物時，呼叫 `get_top_persons`。\n"
        "- 比較兩個關鍵字是否經常相伴出現、或查詢議題關聯度時，呼叫 `get_keyword_correlation`。\n"
        "- 當需要查詢資料庫中關於某關鍵字的『最新一篇文章』全文、連結或發布日期時，務必呼叫 `get_latest_article_by_keyword`。\n"
        "- 當用戶說上網搜尋時，呼叫 `search_and_read_web` 上網查資料。\n"
        "- 當需要查詢最新的外部資料、即時新聞或不在資料庫裡的資訊時，呼叫 `search_and_read_web` 上網查資料。\n"
        "- 當需要讀取知識庫文件時，直接傳入檔名給 `read_local_document`（系統會自動去 knowledge_base/ 尋找）。\n"
        "- 當使用者要求「存檔」、「生成報告檔案」或「存到文件」時，呼叫 `save_report_to_file`。\n\n"
        "- 當沒有任何工具可用時，你就用自己的專業知識去回答。\n"
        "- 將工具數據融會貫通，給出一份簡單、直白、易懂且有數據佐證的回答。"
    ]
    if context:
        lines.append(f'\n以下是相關的最新情報資料（優先參考）：\n{context}')
    return '\n'.join(lines)


def _build_ai_context(question: str) -> str:
    """從 NewsData 撈取相關情報作為 RAG context"""
    try:
        from app_user_keyword_db.models import NewsData
        news = list(NewsData.objects.order_by('-date')[:10])
        if not news:
            return ''
        lines = []
        for n in news[:5]:
            title   = getattr(n, 'title', '') or ''
            content = getattr(n, 'content', '') or ''
            date    = getattr(n, 'date', '') or ''
            if title:
                lines.append(f'[{date}] {title}：{content[:150]}')
        return '\n'.join(lines)
    except Exception:
        return ''


async def collect_message_images(message: 'discord.Message') -> list[tuple[bytes, str]]:
    """
    下載訊息中的圖片附件，回傳 [(bytes, mime_type), ...]。
    略過過大或非圖片格式。
    """
    images: list[tuple[bytes, str]] = []
    for attachment in message.attachments:
        if len(images) >= MAX_IMAGES:
            break
        mime = (attachment.content_type or '').lower()
        if mime not in ALLOWED_IMAGE_MIMES:
            continue
        if attachment.size and attachment.size > MAX_IMAGE_BYTES:
            logger.info(
                '[UMAInfo] 略過過大圖片 %s (%s bytes)', attachment.filename, attachment.size,
            )
            continue
        try:
            data = await attachment.read()
            if not data or len(data) > MAX_IMAGE_BYTES:
                continue
            images.append((data, mime))
        except Exception as exc:
            logger.warning('[UMAInfo] 讀取附件失敗 %s：%s', attachment.filename, exc)
    return images


def generate_ai_answer(
    question: str,
    guild_id: str | None,
    images: list[tuple[bytes, str]] | None = None,
) -> str:
    """生成 AI 回答（同步；含可選圖片多模態輸入）。"""
    try:
        from google import genai as _genai
        from google.genai import types as _genai_types

        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            return '⚠️ GEMINI_API_KEY 未設定，無法使用 AI 問答功能。'

        client = _genai.Client(api_key=api_key)
        context = _build_ai_context(question)
        model_id = os.getenv('UMA_CHAT_MODEL', 'gemini-3.1-flash-lite')
        system_prompt = _build_system_prompt(context)

        parts: list = [_genai_types.Part.from_text(text=question or DEFAULT_IMAGE_PROMPT)]
        for data, mime in (images or []):
            parts.append(_genai_types.Part.from_bytes(data=data, mime_type=mime))

        contents = _genai_types.Content(role='user', parts=parts)

        response = client.models.generate_content(
            model=model_id,
            config=_genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=1024,
                temperature=0.7,
            ),
            contents=contents,
        )
        return response.text or '（AI 無回應）'
    except Exception as exc:
        logger.error('[UMAInfo] AI 問答失敗：%s', exc)
        return '😅 AI 目前無法回應，請稍後再試。'


def split_text(text: str, max_len: int) -> list[str]:
    """將長文本分割成不超過 max_len 的段落"""
    chunks: list[str] = []
    while len(text) > max_len:
        split_at = text.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    if text:
        chunks.append(text)
    return chunks
