"""
scripts/generate_top_character_csv.py
計算各分類熱門角色出現次數，雙輸出：
  1. CSV: data/processed/uma_top_character_with_category.csv（向下相容）
  2. DB:  TopCharacter（app_uma_top_character），含 window_days, computed_date

讀取來源優先順序：
  1. NewsData(status='labeled') from DB（Phase 2b 後）
  2. fallback: data/processed/uma_news_preprocessed.csv
角色名稱來源：
  1. UmaCharacter DB（Phase 2d 後）
  2. fallback: data/processed/uma_characters_bilingual.csv

用法：在專案根目錄執行
    python scripts/generate_top_character_csv.py
"""
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
from app_uma_top_character.models import TopCharacter

# ── 路徑設定 ──────────────────────────────────────────────────
import pandas as pd

PROCESSED     = os.path.join(_ROOT, 'data', 'processed')
CSV_CHARS     = os.path.join(PROCESSED, 'uma_characters_bilingual.csv')
CSV_NEWS      = os.path.join(PROCESSED, 'uma_news_preprocessed.csv')
CSV_OUT       = os.path.join(PROCESSED, 'uma_top_character_with_category.csv')

CATEGORIES    = ['活動', '卡池', '競賽', '系統', '其他']
WINDOW_DAYS   = 0


# ── 角色名稱對照表 ────────────────────────────────────────────
def _load_name_map() -> dict:
    """優先從 UmaCharacter DB 讀取；fallback 至 bilingual CSV。"""
    try:
        from app_user_keyword_db.models import UmaCharacter
        qs = UmaCharacter.objects.filter(is_active=True).values('name_tw', 'name_jp')
        if qs.exists():
            name_map = {}
            for row in qs:
                trad = row['name_tw']
                jp   = row['name_jp']
                if trad:
                    name_map[trad] = trad
                if jp and jp != trad:
                    name_map[jp] = trad
            print(f"[generate_top_character] 從 UmaCharacter DB 載入 {len(name_map)} 個別名")
            return name_map
    except Exception as exc:
        print(f"[generate_top_character] UmaCharacter DB 不可用，改讀 CSV：{exc}")
    # fallback: bilingual CSV
    if not os.path.exists(CSV_CHARS):
        print(f"[generate_top_character] 角色 CSV 不存在：{CSV_CHARS}")
        return {}
    df_chars = pd.read_csv(CSV_CHARS)
    name_map = {}
    for _, r in df_chars.iterrows():
        trad = str(r['name_trad']).strip() if pd.notna(r.get('name_trad')) else None
        simp = str(r['name_simp']).strip() if pd.notna(r.get('name_simp')) else None
        if trad:
            name_map[trad] = trad
        if simp and simp != trad:
            name_map[simp] = trad
    print(f"[generate_top_character] fallback: 從 bilingual CSV 載入 {len(name_map)} 個別名")
    return name_map


# ── 新聞資料讀取 ──────────────────────────────────────────────
def _load_news() -> pd.DataFrame:
    """優先從 NewsData DB 讀取，fallback 至 CSV。"""
    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(status='labeled').values(
            'item_id', 'category', 'title', 'content',
        )
        df_db = pd.DataFrame.from_records(list(qs))
        if not df_db.empty:
            print(f"[generate_top_character] 從 DB 讀取 {len(df_db)} 筆（status=labeled）")
            return df_db
    except Exception as exc:
        print(f"[generate_top_character] DB 讀取失敗，改讀 CSV：{exc}")
    if not os.path.exists(CSV_NEWS):
        print(f"[generate_top_character] CSV 亦不存在：{CSV_NEWS}")
        return pd.DataFrame(columns=['category', 'content', 'title'])
    df = pd.read_csv(CSV_NEWS, sep='|')
    print(f"[generate_top_character] fallback: 從 CSV 讀取 {len(df)} 筆")
    return df


def main():
    name_map = _load_name_map()
    if not name_map:
        print("[generate_top_character] 無角色名稱資料，終止")
        return

    df_news = _load_news()
    print(f"[INFO] 角色別名數（繁體＋簡體）：{len(name_map)}")

    cate_char_count: dict = defaultdict(lambda: defaultdict(int))

    for _, row in df_news.iterrows():
        cate = row.get('category', '其他')
        text = str(row.get('content', '')) + ' ' + str(row.get('title', ''))
        for alias, canonical in name_map.items():
            cnt = text.count(alias)
            if cnt > 0:
                cate_char_count[cate][canonical] += cnt

    rows = []
    today = date.today()

    for cate in CATEGORIES:
        counts = cate_char_count.get(cate, {})
        sorted_pairs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        rows.append({'category': cate, 'top_keys': str(sorted_pairs)})

    # ── 1. 寫 CSV（向下相容）─────────────────────────────────
    os.makedirs(PROCESSED, exist_ok=True)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(CSV_OUT, index=False)
    print(f"[OK] CSV 寫入 {CSV_OUT}，共 {len(rows)} 列")

    # ── 2. 寫 TopCharacter DB ─────────────────────────────────
    db_objs = []
    for cate in CATEGORIES:
        counts = cate_char_count.get(cate, {})
        for char_name, cnt in counts.items():
            db_objs.append(TopCharacter(
                character=char_name,
                category=cate,
                mention_count=cnt,
                source='',
                window_days=WINDOW_DAYS,
                computed_date=today,
            ))

    if db_objs:
        TopCharacter.objects.bulk_create(
            db_objs,
            update_conflicts=True,
            unique_fields=['character', 'category', 'source', 'window_days', 'computed_date'],
            update_fields=['mention_count'],
        )
        print(f"[OK] DB 寫入 TopCharacter {len(db_objs)} 筆（computed_date={today}）")
    else:
        print("[WARN] 無任何角色資料可寫入 DB")

    for r in rows:
        import ast
        pairs = ast.literal_eval(r['top_keys'])
        print(f"  {r['category']}: {len(pairs)} 個角色，top3 = {pairs[:3]}")


if __name__ == '__main__':
    main()
