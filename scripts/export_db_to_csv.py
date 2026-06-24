"""
scripts/export_db_to_csv.py

將 NewsData 資料庫（Django ORM）匯出為 data/processed/uma_news_preprocessed.csv，
使 CSV-based 分析頁（userkeyword / userkeyword_assoc / userkeyword_senti）
能使用完整資料集（含 YouTube、巴哈、bilibili、ettoday、gamme、udn 等所有來源）。

用法：
    python scripts/export_db_to_csv.py
"""
import os
import sys
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_user_keyword_db.models import NewsData

PROCESSED = os.path.join(ROOT_DIR, 'data', 'processed')
CSV_OUT   = os.path.join(PROCESSED, 'uma_news_preprocessed.csv')
CSV_BAK   = CSV_OUT + '.bak'


def main():
    qs = NewsData.objects.all().values(
        'item_id', 'source', 'date', 'category',
        'title', 'content', 'link', 'photo_link',
        'tokens_filtered', 'token_pos', 'top_key_freq',
        'sentiment',
    )
    records = list(qs)
    print(f"[INFO] 共讀取 {len(records)} 筆 NewsData")

    df = pd.DataFrame(records)

    # 日期轉字串，避免 pipe 分隔符號問題
    df['date'] = df['date'].astype(str).replace('None', '').replace('NaT', '')

    # 補全 CSV 欄位（CSv 需要 tokens、tokens_v2、summary，DB 無此欄位時填空字串）
    for col in ('tokens', 'tokens_v2', 'summary'):
        if col not in df.columns:
            df[col] = ''

    # 欄位排序與 CSV 原始格式一致
    columns = [
        'item_id', 'source', 'date', 'category', 'title', 'content',
        'link', 'photo_link', 'tokens', 'tokens_filtered', 'token_pos',
        'top_key_freq', 'tokens_v2', 'sentiment', 'summary',
    ]
    df = df.reindex(columns=columns)

    # 備份舊 CSV
    if os.path.exists(CSV_OUT):
        import shutil
        shutil.copy2(CSV_OUT, CSV_BAK)
        print(f"[INFO] 舊 CSV 已備份至 {CSV_BAK}")

    os.makedirs(PROCESSED, exist_ok=True)
    df.to_csv(CSV_OUT, sep='|', index=False)
    print(f"[OK] 已寫入 {CSV_OUT}，共 {len(df)} 列")

    # 驗證
    by_source = df['source'].value_counts().to_dict()
    print(f"[INFO] 來源分佈：{by_source}")
    by_cate = df['category'].value_counts().to_dict()
    print(f"[INFO] 分類分佈：{by_cate}")


if __name__ == '__main__':
    main()
