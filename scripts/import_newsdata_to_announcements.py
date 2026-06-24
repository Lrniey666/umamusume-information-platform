"""
scripts/import_newsdata_to_announcements.py

將 NewsData（共 2597 筆）批量同步至 app_uma_news.GameAnnouncement，
讓 /dashboard/ 及 /comment_sentiment/ 的文章列表有資料可顯示。

用法：
    python scripts/import_newsdata_to_announcements.py
"""
import os, sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_user_keyword_db.models import NewsData
from app_uma_news.models import GameAnnouncement
from django.db import transaction

# category mapping: NewsData 使用繁體中文，GameAnnouncement 的 choices 同樣是繁體
VALID_CATEGORIES = {'活動', '卡池', '競賽', '系統', '其他'}


def main():
    existing_urls = set(
        GameAnnouncement.objects.values_list('source_url', flat=True).exclude(source_url__isnull=True)
    )
    print(f"[INFO] GameAnnouncement 現有 {GameAnnouncement.objects.count()} 筆，"
          f"其中有 URL 的 {len(existing_urls)} 筆")

    qs = NewsData.objects.all()
    print(f"[INFO] NewsData 共 {qs.count()} 筆，開始匯入…")

    created = 0
    skipped = 0
    batch   = []

    for nd in qs.iterator():
        # 去重：以 link 為唯一鍵（link 為 None 的也允許匯入）
        if nd.link and nd.link in existing_urls:
            skipped += 1
            continue

        cate = nd.category if nd.category in VALID_CATEGORIES else '其他'

        ann = GameAnnouncement(
            title          = nd.title or '（無標題）',
            content        = nd.content or '',
            category       = cate,
            source_url     = nd.link or None,
            published_date = nd.date,
            source         = nd.source or 'unknown',
        )
        batch.append(ann)
        if nd.link:
            existing_urls.add(nd.link)
        created += 1

        if len(batch) >= 500:
            with transaction.atomic():
                GameAnnouncement.objects.bulk_create(batch, ignore_conflicts=True)
            batch.clear()

    if batch:
        with transaction.atomic():
            GameAnnouncement.objects.bulk_create(batch, ignore_conflicts=True)

    print(f"[OK] 新增 {created} 筆，略過重複 {skipped} 筆")
    print(f"[OK] GameAnnouncement 現共 {GameAnnouncement.objects.count()} 筆")


if __name__ == '__main__':
    main()
