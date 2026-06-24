"""
D6: AI 新聞生成（複用 LLM Report 邏輯）
"""
import os
from datetime import date, timedelta

_TONE_INSTRUCTIONS = {
    'lively':  '語調：活潑且資訊豐富，適度加入 Emoji 與口語化措辭，適合輕鬆的 Discord 社群閱讀。',
    'concise': '語調：簡潔精準，以條列為主、少用 Emoji，快速掌握重點，適合資訊分享型伺服器。',
}


def _build_system_prompt(tone: str = 'lively') -> str:
    tone_line = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS['lively'])
    return (
        '你是「馬娘情報站」Discord Bot，負責每日統整《賽馬娘 Pretty Derby》\n'
        '遊戲社群的最新動態與玩家輿情。請以繁體中文撰寫一份結構清晰的「本週馬娘資訊摘要」，\n'
        '格式要求：\n'
        '1. **本週亮點**（3-5 條重要事項）\n'
        '2. **玩家輿情分析**（正/負面情緒趨勢）\n'
        '3. **熱門討論角色**（前 3 名 + 簡評）\n'
        '4. **關鍵詞趨勢**（本週最熱詞彙）\n'
        '5. **下週預測 & 建議**\n'
        f'字數：500–800 字。{tone_line}'
    )


def generate_news(model: str = 'gemini', tone: str = 'lively') -> str:
    """生成本週馬娘資訊摘要（tone：lively 活潑 / concise 簡潔）。"""
    try:
        from app_user_keyword_db.models import NewsData
        since = date.today() - timedelta(days=7)
        news = NewsData.objects.filter(date__gte=since).order_by('-date')[:100]

        if not news.exists():
            return '（本週暫無新資料）'

        context = '\n\n'.join(
            f'[{n.category} | {n.date}] {n.title}\n{n.content[:300]}'
            for n in news
        )
        user_prompt = f'以下是近 7 天的馬娘遊戲相關資訊（含論壇、Discord 社群）：\n\n{context}'
        system_prompt = _build_system_prompt(tone)

        if model == 'claude':
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            resp = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=1024,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_prompt}],
            )
            return resp.content[0].text
        else:
            from google import genai
            from google.genai import types as genai_types
            client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
            resp = client.models.generate_content(
                model='gemini-3.5-flash',
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1024, temperature=0.7,
                ),
                contents=user_prompt,
            )
            return resp.text
    except Exception as e:
        return f'（新聞生成失敗: {e}）'


def split_for_discord(text: str, limit: int = 1900) -> list:
    """切分長文，確保每段 ≤ Discord 訊息上限 2000 字"""
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    return parts
