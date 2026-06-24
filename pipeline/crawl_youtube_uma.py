"""
pipeline/crawl_youtube_uma.py

O5: YouTube Data API v3 爬蟲腳本（獨立執行版）
輸出: pipeline/youtube_uma_videos.csv, pipeline/youtube_uma_comments.csv

使用方式：
    python pipeline/crawl_youtube_uma.py
"""
import os
import csv
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
YT_API_KEY = os.getenv('YOUTUBE_API_KEY')
BASE = 'https://www.googleapis.com/youtube/v3'
SEARCH_QUERIES = ['ウマ娘', '賽馬娘', 'Uma Musume Pretty Derby']


def search_videos(query: str, max_results: int = 20) -> list:
    resp = requests.get(f'{BASE}/search', params={
        'part': 'snippet', 'q': query, 'type': 'video',
        'maxResults': max_results, 'order': 'date',
        'relevanceLanguage': 'zh-TW,ja',
        'key': YT_API_KEY,
    }, timeout=15)
    resp.raise_for_status()
    return [item['id']['videoId'] for item in resp.json().get('items', [])]


def get_video_details(video_ids: list) -> list:
    results = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        resp = requests.get(f'{BASE}/videos', params={
            'part': 'snippet,statistics',
            'id': ','.join(batch),
            'key': YT_API_KEY,
        }, timeout=15)
        resp.raise_for_status()
        results.extend(resp.json().get('items', []))
    return results


def get_video_comments(video_id: str, max_results: int = 100) -> list:
    comments = []
    params = {
        'part': 'snippet', 'videoId': video_id,
        'maxResults': 100, 'order': 'relevance',
        'key': YT_API_KEY,
    }
    while len(comments) < max_results:
        try:
            resp = requests.get(f'{BASE}/commentThreads', params=params, timeout=15)
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


def run():
    if not YT_API_KEY:
        print('ERROR: YOUTUBE_API_KEY 未設定')
        return

    all_video_ids = set()
    for q in SEARCH_QUERIES:
        ids = search_videos(q, max_results=20)
        all_video_ids.update(ids)
        print(f'[{q}] 搜尋到 {len(ids)} 部影片')

    videos = get_video_details(list(all_video_ids))
    out_dir = Path(__file__).parent
    video_rows, comment_rows = [], []

    for v in videos:
        snip = v['snippet']
        stats = v.get('statistics', {})
        video_rows.append({
            'video_id': v['id'],
            'title': snip.get('title', ''),
            'channel_name': snip.get('channelTitle', ''),
            'channel_id': snip.get('channelId', ''),
            'published_at': snip.get('publishedAt', ''),
            'view_count': stats.get('viewCount', 0),
            'like_count': stats.get('likeCount', 0),
            'comment_count': stats.get('commentCount', 0),
            'thumbnail_url': snip.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'description': snip.get('description', '')[:800],
            'tags': json.dumps(snip.get('tags', []), ensure_ascii=False),
        })
        comments = get_video_comments(v['id'], max_results=50)
        for c in comments:
            c['video_id'] = v['id']
            comment_rows.append(c)

    video_csv = out_dir / 'youtube_uma_videos.csv'
    comment_csv = out_dir / 'youtube_uma_comments.csv'
    if video_rows:
        with open(video_csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=video_rows[0].keys())
            w.writeheader()
            w.writerows(video_rows)
        print(f'影片 CSV: {video_csv}')
    if comment_rows:
        with open(comment_csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=comment_rows[0].keys())
            w.writeheader()
            w.writerows(comment_rows)
        print(f'留言 CSV: {comment_csv}')

    print(f'Done. Videos: {len(video_rows)}, Comments: {len(comment_rows)}')


if __name__ == '__main__':
    run()
