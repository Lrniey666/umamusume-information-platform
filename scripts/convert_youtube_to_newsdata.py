"""
scripts/convert_youtube_to_newsdata.py

將 YouTubeVideo（尚未轉換）增量寫入 NewsData。
只轉換影片本體（title + description），不轉換個別留言。
可獨立執行，也可由 Pipeline Step 7 呼叫。

用法：
    python scripts/convert_youtube_to_newsdata.py
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_youtube_uma.models import YouTubeVideo
from app_user_keyword_db.models import NewsData


def classify_youtube_category(title: str, tags: str) -> str:
    """簡易分類：根據標題與 tags 對應標準分類"""
    text = (title + ' ' + tags).lower()
    if any(k in text for k in ['活動', '慶典', '周年', '獎勵', 'event']):
        return '活動'
    if any(k in text for k in ['卡池', '限定', '抽卡', 'gacha', 'sr', 'ssr']):
        return '卡池'
    if any(k in text for k in ['賽事', '競技', '錦標', '排名', '決賽', 'race']):
        return '競賽'
    if any(k in text for k in ['更新', '維護', '系統', 'bug', '修復', 'update']):
        return '系統'
    return '其他'


def convert_youtube_to_newsdata() -> int:
    """
    將 YouTubeVideo 增量寫入 NewsData（source='youtube'）。
    以 youtube_{video_id} 為 item_id，已存在的跳過。
    回傳新增筆數。
    """
    existing_ids = set(
        NewsData.objects.filter(source='youtube')
        .values_list('item_id', flat=True)
    )

    videos = YouTubeVideo.objects.all()
    created = 0
    skipped = 0

    for video in videos:
        item_id = f'youtube_{video.video_id}'
        if item_id in existing_ids:
            skipped += 1
            continue

        pub_date = video.published_at.date() if video.published_at else None
        content = video.description.strip() if video.description else video.title
        category = classify_youtube_category(video.title, video.tags or '')

        NewsData.objects.create(
            item_id=item_id,
            source='youtube',
            date=pub_date,
            category=category,
            title=video.title,
            content=content,
            link=f'https://www.youtube.com/watch?v={video.video_id}',
            photo_link=video.thumbnail_url or '',
            sentiment=video.sentiment,
            tokens_filtered='',
            token_pos='',
            top_key_freq='',
        )
        created += 1

    return created


def main():
    total_videos = YouTubeVideo.objects.count()
    if total_videos == 0:
        print('[INFO] YouTubeVideo 資料表尚無資料，跳過轉換。')
        print('Done.')
        return

    before = NewsData.objects.filter(source='youtube').count()
    created = convert_youtube_to_newsdata()
    after = NewsData.objects.filter(source='youtube').count()
    print(f'[INFO] YouTubeVideo 共 {total_videos} 部')
    print(f'[INFO] YouTube 來源：匯入前 {before} 筆 → 匯入後 {after} 筆（新增 {created} 筆）')
    print('Done.')


if __name__ == '__main__':
    main()
