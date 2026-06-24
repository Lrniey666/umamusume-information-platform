import os
from django.core.management import call_command
from .models import YouTubeVideo


def crawl_youtube_job():
    """APScheduler 排程用 — 增量爬取 YouTube 影片與留言"""
    try:
        call_command('crawl_youtube', max_videos=15, max_comments=30)
    except Exception as e:
        print(f'[crawl_youtube_job] 失敗: {e}')


def analyze_youtube_sentiment_job():
    """APScheduler 排程用 — 批次標記未分析影片的情感分數"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        unanalyzed = YouTubeVideo.objects.filter(sentiment__isnull=True)[:50]
        for video in unanalyzed:
            comments = list(video.comments.values_list('text', flat=True)[:20])
            if not comments:
                continue
            prompt = (
                f'影片標題：{video.title}\n'
                f'留言樣本（{len(comments)} 則）：\n'
                + '\n'.join(f'- {c[:120]}' for c in comments)
                + '\n\n請根據留言整體情感，回傳 0.0（非常負面）到 1.0（非常正面）之間的浮點數，'
                  '只回傳數字，不要其他說明。'
            )
            resp = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
            )
            score = float(resp.text.strip())
            video.sentiment = max(0.0, min(1.0, score))
            video.save(update_fields=['sentiment'])
        print(f'[analyze_youtube] 完成標記 {len(unanalyzed)} 部影片')
    except Exception as e:
        print(f'[analyze_youtube_sentiment_job] 失敗: {e}')
