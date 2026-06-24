import re
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from app_uma_news.models import GameAnnouncement
from app_comment_sentiment.models import CommentSentiment
from app_comment_sentiment.llm_client import client, MODEL_NAME

SYSTEM_PROMPT = (
    '你是一位專精於手機遊戲《賽馬娘 Pretty Derby》的玩家社群情緒分析師。'
    '你必須嚴格輸出合法的 JSON 格式，'
    '不要加上 ```json 程式碼區塊標記，也不要有任何其他說明文字。'
)


def build_prompt(announcement, comments_text, num_comments):
    return f"""請針對以下「公告內容」與「玩家留言」進行綜合情緒分析。

【任務一：公告內容基調分析】
請從公告內容判斷這篇公告的整體基調，分別給出「正面(positive)」、「負面(negative)」、
「中立(neutral)」的三個面向機率分數，分數在 0.0 到 1.0 之間，且三者加總必須等於 1.0。

【任務二：留言情緒分析】
請將這些留言的整體情緒歸類到六種標籤中，並計算其佔比（總和需為100%）。
若「無留言」，請全部給 0。
標籤為：
- excited（興奮）：玩家對公告感到期待、興奮
- happy（開心）：玩家感到滿足、正面肯定
- mixed（五味雜陳）：玩家情緒複雜，有好有壞
- disappointed（失望）：玩家對公告感到不滿或期望落空
- angry（生氣）：玩家明顯憤怒、抱怨
- sad（悲傷）：玩家感到難過或遺憾

務必只輸出如下 JSON 格式：
{{
  "article_sentiment": {{
    "positive_score": 0.65,
    "negative_score": 0.10,
    "neutral_score": 0.25
  }},
  "comments_emotion": {{
    "excited": 35,
    "happy": 25,
    "mixed": 20,
    "disappointed": 10,
    "angry": 7,
    "sad": 3
  }}
}}

【公告內容】
{announcement.content[:1000]}

【玩家留言（前 {num_comments} 則，依讚數排序）】
{comments_text}"""


def analyze_one(announcement):
    comments = announcement.comments.order_by('-upvotes')[:30]
    num_comments = comments.count()
    comments_text = (
        '\n'.join([f'{i+1}. {c.content}' for i, c in enumerate(comments)])
        if num_comments > 0 else '無留言'
    )

    prompt = build_prompt(announcement, comments_text, num_comments)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.1,
    )
    result = response.choices[0].message.content.strip()
    result = re.sub(r'^```json\s*', '', result)
    result = re.sub(r'```\s*$', '', result)
    data = json.loads(result)

    sentiment, _ = CommentSentiment.objects.get_or_create(announcement=announcement)

    art = data.get('article_sentiment', {})
    sentiment.positive_score = float(art.get('positive_score', 0.0))
    sentiment.negative_score = float(art.get('negative_score', 0.0))
    sentiment.neutral_score  = float(art.get('neutral_score', 0.0))

    emo = data.get('comments_emotion', {})
    sentiment.excited      = float(emo.get('excited', 0))
    sentiment.happy        = float(emo.get('happy', 0))
    sentiment.mixed        = float(emo.get('mixed', 0))
    sentiment.disappointed = float(emo.get('disappointed', 0))
    sentiment.angry        = float(emo.get('angry', 0))
    sentiment.sad          = float(emo.get('sad', 0))

    sentiment.ai_model    = MODEL_NAME
    sentiment.analyzed_at = timezone.now()
    sentiment.save()

    return sentiment


class Command(BaseCommand):
    help = '使用 Gemini API 分析尚未處理的公告留言情緒'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='最多處理幾篇（0=全部）')

    def handle(self, *args, **options):
        limit = options['limit']

        pending = GameAnnouncement.objects.exclude(
            sentiment__analyzed_at__isnull=False
        )
        if limit > 0:
            pending = pending[:limit]

        total = pending.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('目前沒有需要分析的公告！'))
            return

        self.stdout.write(f'找到 {total} 篇公告等待分析...')
        success, failed = 0, 0

        for i, ann in enumerate(pending, 1):
            self.stdout.write(f'[{i}/{total}] 分析中：{ann.title[:30]}...')
            try:
                sentiment = analyze_one(ann)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ 完成 | 正:{sentiment.positive_score:.2f} '
                    f'負:{sentiment.negative_score:.2f} 中:{sentiment.neutral_score:.2f}'
                ))
                success += 1
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'  ❌ JSON 解析失敗：{e}'))
                failed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ 分析失敗：{e}'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n分析完成！成功 {success} 篇，失敗 {failed} 篇'
        ))
