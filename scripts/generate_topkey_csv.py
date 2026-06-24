"""
scripts/generate_topkey_csv.py
計算各分類熱門關鍵詞，雙輸出：
  1. CSV: data/processed/uma_topkey_with_category.csv（向下相容）
  2. DB:  TopKeyword（app_uma_top_keyword），含 window_days, computed_date

讀取來源優先順序：
  1. NewsData(status='labeled') from DB（Phase 2b 後）
  2. fallback: data/processed/uma_news_preprocessed.csv

用法：在專案根目錄執行
    python scripts/generate_topkey_csv.py
"""
import ast
import os
import sys
from collections import defaultdict
from datetime import date

# ── Django 環境 ────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

# ── Django models（setup 後才可 import）──────────────────────
from app_uma_top_keyword.models import TopKeyword

# ── 路徑設定 ──────────────────────────────────────────────────
import pandas as pd

PROCESSED = os.path.join(_ROOT, 'data', 'processed')
CSV_IN    = os.path.join(PROCESSED, 'uma_news_preprocessed.csv')
CSV_OUT   = os.path.join(PROCESSED, 'uma_topkey_with_category.csv')

CATEGORIES  = ['活動', '卡池', '競賽', '系統', '其他']
WINDOW_DAYS = 0     # 0 = 全部時間


# ── 資料讀取 ──────────────────────────────────────────────────
def _load_news() -> pd.DataFrame:
    """優先從 NewsData DB 讀取，fallback 至 CSV。"""
    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(status='labeled').values(
            'item_id', 'category', 'top_key_freq',
        )
        df_db = pd.DataFrame.from_records(list(qs))
        if not df_db.empty:
            print(f"[generate_topkey] 從 DB 讀取 {len(df_db)} 筆（status=labeled）")
            return df_db
    except Exception as exc:
        print(f"[generate_topkey] DB 讀取失敗，改讀 CSV：{exc}")
    if not os.path.exists(CSV_IN):
        print(f"[generate_topkey] CSV 亦不存在：{CSV_IN}")
        return pd.DataFrame(columns=['category', 'top_key_freq'])
    df = pd.read_csv(CSV_IN, sep='|')
    print(f"[generate_topkey] fallback: 從 CSV 讀取 {len(df)} 筆")
    return df


def main():
    df = _load_news()

    cate_word_freq: dict = defaultdict(lambda: defaultdict(int))

    for _, row in df.iterrows():
        cate = row.get('category', '其他')
        raw  = row.get('top_key_freq', '')
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            pairs = ast.literal_eval(raw)
        except Exception:
            continue
        for word, freq in pairs:
            cate_word_freq[cate][word] += freq

    rows = []
    today = date.today()

    for cate in CATEGORIES:
        wf = cate_word_freq.get(cate, {})
        sorted_pairs = sorted(wf.items(), key=lambda x: x[1], reverse=True)
        rows.append({'category': cate, 'top_keys': str(sorted_pairs)})

    # ── 1. 寫 CSV（向下相容）─────────────────────────────────
    os.makedirs(PROCESSED, exist_ok=True)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(CSV_OUT, index=False)
    print(f"[OK] CSV 寫入 {CSV_OUT}，共 {len(rows)} 列")

    # ── 2. 寫 TopKeyword DB ───────────────────────────────────
    db_objs = []
    for cate in CATEGORIES:
        wf = cate_word_freq.get(cate, {})
        for word, freq in wf.items():
            db_objs.append(TopKeyword(
                keyword=word,
                category=cate,
                freq=freq,
                source='',
                window_days=WINDOW_DAYS,
                computed_date=today,
            ))

    if db_objs:
        TopKeyword.objects.bulk_create(
            db_objs,
            update_conflicts=True,
            unique_fields=['keyword', 'category', 'source', 'window_days', 'computed_date'],
            update_fields=['freq'],
        )
        print(f"[OK] DB 寫入 TopKeyword {len(db_objs)} 筆（computed_date={today}）")
    else:
        print("[WARN] 無任何關鍵詞資料可寫入 DB")

    for r in rows:
        pairs = ast.literal_eval(r['top_keys'])
        print(f"  {r['category']}: {len(pairs)} 個詞，top3 = {pairs[:3]}")


if __name__ == '__main__':
    main()
