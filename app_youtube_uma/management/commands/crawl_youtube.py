"""
app_youtube_uma/management/commands/crawl_youtube.py

使用方式：
    python manage.py crawl_youtube
    python manage.py crawl_youtube --max-videos 30 --max-comments 100
"""
import os
import json
from datetime import datetime
from pathlib import Path

import requests
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3'
SEARCH_QUERIES = ['ウマ娘', '賽馬娘', 'Uma Musume Pretty Derby']


def search_videos(api_key: str, query: str, max_results: int = 20) -> list:
    resp = requests.get(f'{YOUTUBE_API_BASE}/search', params={
        'part': 'snippet', 'q': query, 'type': 'video',
        'maxResults': max_results, 'order': 'date',
        'key': api_key,
    }, timeout=15)
    resp.raise_for_status()
    return [item['id']['videoId'] for item in resp.json().get('items', [])]


def get_video_details(api_key: str, video_ids: list) -> list:
    results = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        resp = requests.get(f'{YOUTUBE_API_BASE}/videos', params={
            'part': 'snippet,statistics',
            'id': ','.join(batch),
            'key': api_key,
        }, timeout=15)
        resp.raise_for_status()
        results.extend(resp.json().get('items', []))
    return results


def get_video_comments(api_key: str, video_id: str, max_results: int = 100) -> list:
    comments = []
    params = {
        'part': 'snippet', 'videoId': video_id,
        'maxResults': 100, 'order': 'relevance',
        'key': api_key,
    }
    while len(comments) < max_results:
        try:
            resp = requests.get(
                f'{YOUTUBE_API_BASE}/commentThreads',
                params=params, timeout=15
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                break
            raise
        data = resp.json()
        for item in data.get('items', []):
            s = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'comment_id': item['id'],
                'text': s.get('textOriginal', ''),
                'author': s.get('authorDisplayName', ''),
                'like_count': s.get('likeCount', 0),
                'published_at': s.get('publishedAt'),
            })
        next_page = data.get('nextPageToken')
        if not next_page:
            break
        params['pageToken'] = next_page
    return comments


class Command(BaseCommand):
    help = '爬取 YouTube 賽馬娘相關影片與留言，存入 DB'

    def add_arguments(self, parser):
        parser.add_argument('--max-videos', type=int, default=20,
                            help='每個關鍵字最多爬取影片數（預設 20）')
        parser.add_argument('--max-comments', type=int, default=50,
                            help='每部影片最多抓取留言數（預設 50）')

    def handle(self, *args, **options):
        from app_youtube_uma.models import YouTubeVideo, YouTubeComment

        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            self.stderr.write('ERROR: YOUTUBE_API_KEY 未設定，跳過爬取')
            return

        max_v = options['max_videos']
        max_c = options['max_comments']

        all_ids = set()
        for q in SEARCH_QUERIES:
            try:
                ids = search_videos(api_key, q, max_results=max_v)
                all_ids.update(ids)
                self.stdout.write(f'  [{q}] +{len(ids)} 部影片')
            except Exception as e:
                self.stderr.write(f'  [{q}] 搜尋失敗: {e}')

        if not all_ids:
            self.stdout.write('未取得任何影片 ID，結束')
            return

        try:
            videos = get_video_details(api_key, list(all_ids))
        except Exception as e:
            self.stderr.write(f'取得影片詳情失敗: {e}')
            return

        video_count, comment_count = 0, 0

        for v in videos:
            snip = v['snippet']
            stats = v.get('statistics', {})
            pub = snip.get('publishedAt')
            try:
                obj, created = YouTubeVideo.objects.update_or_create(
                    video_id=v['id'],
                    defaults={
                        'title': snip.get('title', ''),
                        'channel_name': snip.get('channelTitle', ''),
                        'channel_id': snip.get('channelId', ''),
                        'published_at': datetime.fromisoformat(
                            pub.replace('Z', '+00:00')) if pub else None,
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'comment_count': int(stats.get('commentCount', 0)),
                        'thumbnail_url': snip.get('thumbnails', {}).get(
                            'medium', {}).get('url', ''),
                        'description': snip.get('description', '')[:800],
                        'tags': json.dumps(snip.get('tags', []), ensure_ascii=False),
                    }
                )
                if created:
                    video_count += 1

                for c in get_video_comments(api_key, v['id'], max_results=max_c):
                    pub_c = c.get('published_at')
                    _, c_created = YouTubeComment.objects.update_or_create(
                        comment_id=c['comment_id'],
                        defaults={
                            'video': obj,
                            'text': c['text'],
                            'author': c['author'],
                            'like_count': c['like_count'],
                            'published_at': datetime.fromisoformat(
                                pub_c.replace('Z', '+00:00')) if pub_c else None,
                        }
                    )
                    if c_created:
                        comment_count += 1
            except Exception as e:
                self.stderr.write(f'  影片 {v["id"]} 處理失敗: {e}')

        self.stdout.write(self.style.SUCCESS(
            f'完成！新增影片 {video_count} 部，留言 {comment_count} 則'))
