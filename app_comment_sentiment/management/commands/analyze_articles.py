import re
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from app_comment_sentiment.models import Article, ArticleEmotion
from app_comment_sentiment.llm_client import client, MODEL_NAME

SYSTEM_PROMPT = (
    '你是一位專精於手機遊戲《賽馬娘 Pretty Derby》的玩家社群情緒分析師。'
    '你必須嚴格輸出合法的 JSON 格式，'
    '不要加上 ```json 程式碼區塊標記，也不要有任何其他說明文字。'
)


def build_prompt(article, comments_text, num_comments):
    return f"""請針對以下「文章內容」與「玩家留言」進行綜合情緒分析。

【任務一：文章內容基調分析】
請從文章內容判斷這篇文章的整體基調，分別給出「正面(positive)」、「負面(negative)」、
「中立(neutral)」的三個面向機率分數，分數在 0.0 到 1.0 之間，且三者加總必須等於 1.0。

【任務二：留言情緒分析】
請將這些留言的整體情緒歸類到六種標籤中，並計算其佔比（總和需為100%）。
若「無留言」，請全部給 0。
標籤為：
- excited（興奮）：玩家對文章感到期待、興奮
- happy（開心）：玩家感到滿足、正面肯定
- mixed（五味雜陳）：玩家情緒複雜，有好有壞
- disappointed（失望）：玩家對文章感到不滿或期望落空
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

【文章內容】
{article.content[:1000]}

【玩家留言（前 {num_comments} 則，依讚數排序）】
{comments_text}"""


def analyze_one(article):
    comments = article.comments.order_by('-upvotes')[:30]
    num_comments = comments.count()
    comments_text = (
        '\n'.join([f'{i+1}. {c.content}' for i, c in enumerate(comments)])
        if num_comments > 0 else '無留言'
    )

    prompt = build_prompt(article, comments_text, num_comments)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'```\s*$', '', raw)
    data = json.loads(raw)

    art = data.get('article_sentiment', {})
    article.positive_score = float(art.get('positive_score', 0.0))
    article.negative_score = float(art.get('negative_score', 0.0))
    article.neutral_score  = float(art.get('neutral_score', 0.0))
    article.analyzed_at    = timezone.now()
    article.save(update_fields=['positive_score', 'negative_score', 'neutral_score', 'analyzed_at'])

    emo = data.get('comments_emotion', {})
    emotion, _ = ArticleEmotion.objects.get_or_create(article=article)
    emotion.cheer_up    = float(emo.get('excited', 0))
    emotion.happy       = float(emo.get('happy', 0))
    emotion.mixed       = float(emo.get('mixed', 0))
    emotion.dumbfounded = float(emo.get('disappointed', 0))
    emotion.angry       = float(emo.get('angry', 0))
    emotion.sad         = float(emo.get('sad', 0))
    emotion.save()

    return article


class Command(BaseCommand):
    help = '使用 Gemini API 分析尚未處理的巴哈姆特哈啦板文章情緒'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='最多處理幾篇（0=全部）')

    def handle(self, *args, **options):
        limit = options['limit']

        pending = Article.objects.filter(analyzed_at__isnull=True).order_by('-published_date', '-created_at')
        if limit > 0:
            pending = pending[:limit]

        total = pending.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('目前沒有需要分析的文章！'))
            return

        self.stdout.write(f'找到 {total} 篇文章等待分析...')
        success, failed = 0, 0

        for i, article in enumerate(pending, 1):
            self.stdout.write(f'[{i}/{total}] 分析中：{article.title[:40]}...')
            try:
                analyze_one(article)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ 完成 | 正:{article.positive_score:.2f} '
                    f'負:{article.negative_score:.2f} 中:{article.neutral_score:.2f}'
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
