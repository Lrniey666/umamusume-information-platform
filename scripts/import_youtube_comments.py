"""
scripts/import_youtube_comments.py

將 YouTube 留言（app_youtube_uma.YouTubeComment）匯入 app_comment_sentiment.Comment，
並在 app_comment_sentiment.Article 中建立對應的 YouTube 影片記錄。

用法：
    python scripts/import_youtube_comments.py
"""
import os, sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_youtube_uma.models import YouTubeVideo, YouTubeComment
from app_comment_sentiment.models import Article, Comment
from django.db import transaction


def main():
    videos = YouTubeVideo.objects.all()
    print(f"[INFO] YouTubeVideo: {videos.count()} 筆")
    print(f"[INFO] YouTubeComment: {YouTubeComment.objects.count()} 筆")

    created_articles = 0
    created_comments = 0
    skipped = 0

    for video in videos.iterator():
        url = f"https://www.youtube.com/watch?v={video.video_id}"

        article, art_created = Article.objects.get_or_create(
            url=url,
            defaults={
                'title':          video.title or '（無標題）',
                'content':        video.description or '',
                'category':       '其他',
                'published_date': video.published_at.date() if video.published_at else None,
                'source':         'youtube',
            },
        )
        if art_created:
            created_articles += 1

        # 匯入該影片留言
        yt_comments = YouTubeComment.objects.filter(video=video)
        for c in yt_comments.iterator():
            obj, c_created = Comment.objects.get_or_create(
                article=article,
                content=c.text[:2000] if c.text else '',
                defaults={
                    'author':    c.author or '',
                    'upvotes':   c.like_count or 0,
                    'downvotes': 0,
                },
            )
            if c_created:
                created_comments += 1
            else:
                skipped += 1

    print(f"[OK] 新增 {created_articles} 筆 YouTube Article")
    print(f"[OK] 新增 {created_comments} 筆 Comment，跳過重複 {skipped} 筆")
    print(f"[OK] Article 總計：{Article.objects.count()}")
    print(f"[OK] Comment 總計：{Comment.objects.count()}")


if __name__ == '__main__':
    main()
