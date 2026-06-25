"""
手動觸發 YouTube 影片情感分析（供後台管理介面使用）。

執行方式：python manage.py analyze_youtube_sentiment [--limit 50]
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gemini 批次標記未分析 YouTube 影片的情感分數'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='每次最多分析幾部影片（預設 50）',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        self.stdout.write(f'[analyze_youtube_sentiment] 開始，limit={limit}')

        import os
        from app_youtube_uma.models import YouTubeVideo

        api_key = os.getenv('GEMINI_API_KEY', '').strip()
        if not api_key:
            self.stderr.write('[analyze_youtube_sentiment] GEMINI_API_KEY 未設定，跳過')
            return

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
        except Exception as exc:
            self.stderr.write(f'[analyze_youtube_sentiment] 初始化 Gemini 失敗：{exc}')
            return

        unanalyzed = list(YouTubeVideo.objects.filter(sentiment__isnull=True)[:limit])
        if not unanalyzed:
            self.stdout.write('[analyze_youtube_sentiment] 無待分析影片，結束')
            return

        self.stdout.write(f'[analyze_youtube_sentiment] 待分析影片數：{len(unanalyzed)}')
        success = 0
        skipped = 0
        errors = 0

        for video in unanalyzed:
            comments = list(video.comments.values_list('text', flat=True)[:20])
            if not comments:
                skipped += 1
                self.stdout.write(f'  skip  {video.video_id} — 無留言')
                continue

            prompt = (
                f'影片標題：{video.title}\n'
                f'留言樣本（{len(comments)} 則）：\n'
                + '\n'.join(f'- {c[:120]}' for c in comments)
                + '\n\n請根據留言整體情感，回傳 0.0（非常負面）到 1.0（非常正面）之間的浮點數，'
                  '只回傳數字，不要其他說明。'
            )

            try:
                resp = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                )
                score = float(resp.text.strip())
                video.sentiment = max(0.0, min(1.0, score))
                video.save(update_fields=['sentiment'])
                success += 1
                self.stdout.write(f'  ok    {video.video_id}  score={video.sentiment:.3f}')
            except Exception as exc:
                errors += 1
                self.stderr.write(f'  err   {video.video_id}: {exc}')

        self.stdout.write(
            f'[analyze_youtube_sentiment] 完成 — 成功:{success} 跳過:{skipped} 失敗:{errors}'
        )
