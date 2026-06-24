"""
scripts/import_uma_data.py
將 CSV 匯入 SQLite（Django ORM）。

用法：在專案根目錄執行
    python scripts/import_uma_data.py
    python scripts/import_uma_data.py --csv data/processed/uma_news_mock_multisource.csv
    python scripts/import_uma_data.py --clear   # 清空 DB 後重新匯入
"""
import os
import sys
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_user_keyword_db.models import NewsData
from services.news_service import NEWS_CSV


def main():
    parser = argparse.ArgumentParser(description='匯入新聞 CSV 到 SQLite')
    parser.add_argument('--csv',   default=None, help='指定 CSV 路徑（預設使用 NEWS_CSV）')
    parser.add_argument('--clear', action='store_true',
                        help='匯入前清除網路爬蟲來源（bilibili/bahamut/ettoday/gamme/udn），'
                             'Discord 與 YouTube 來源不受影響')
    args = parser.parse_args()

    csv_path = args.csv or NEWS_CSV

    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV not found: {csv_path}")
        sys.exit(1)

    if args.clear:
        # 只清除網路爬蟲來源，保留 discord / youtube 來源
        WEB_SOURCES = ['bilibili', 'bahamut', 'ettoday', 'gamme', 'udn']
        deleted, _ = NewsData.objects.filter(source__in=WEB_SOURCES).delete()
        print(f"[INFO] 清除網路來源資料 {deleted} 筆（discord / youtube 保留）")

    df = pd.read_csv(csv_path, sep='|', encoding='utf-8-sig')
    print(f"[INFO] CSV loaded: {len(df)} rows, columns: {list(df.columns)}")

    created_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        _, created = NewsData.objects.update_or_create(
            item_id=str(row['item_id']),
            defaults={
                'date':            row['date'] if pd.notna(row.get('date')) else None,
                'category':        str(row['category']),
                'title':           str(row['title']),
                'content':         str(row['content']),
                'link':            str(row.get('link', '')) or None,
                'photo_link':      str(row.get('photo_link', '')) or None,
                'tokens_filtered': str(row.get('tokens_filtered', '')) if pd.notna(row.get('tokens_filtered')) else None,
                'token_pos':       str(row.get('token_pos', '')) if pd.notna(row.get('token_pos')) else None,
                'top_key_freq':    str(row.get('top_key_freq', '')) if pd.notna(row.get('top_key_freq')) else None,
                'sentiment':       float(row['sentiment']) if pd.notna(row.get('sentiment')) else None,
                'source':          str(row['source']) if pd.notna(row.get('source')) else 'bilibili',
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    total = NewsData.objects.count()
    print(f"[INFO] Created: {created_count}, Updated: {updated_count}")
    print(f"Done. Total: {total} rows")

    # 各 source 統計
    from django.db.models import Count
    stats = NewsData.objects.values('source').annotate(n=Count('source')).order_by('-n')
    if stats:
        print("\n各來源統計：")
        for s in stats:
            print(f"  {s['source']:12s}: {s['n']} 筆")


if __name__ == '__main__':
    main()
