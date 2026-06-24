"""
scripts/import_multisource_raw.py
將 w12 參考專案的多來源原始 CSV 匯入 SQLite（最小處理）。

用法：
    python scripts/import_multisource_raw.py
"""
import os, sys, re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django; django.setup()

import pandas as pd
from app_user_keyword_db.models import NewsData

# ── 參考專案路徑 ──────────────────────────────────────────────
W12_RAW = (
    ROOT / '參考專案' / 'w12'
    / 'w12-5-HW@w12-呼叫線上GeminiOpenAI-AI生成你自己的分析報告'
    / 'umamusume-llm-report' / 'data' / 'raw'
)

SOURCES = {
    'ettoday': W12_RAW / 'ettoday_uma_raw.csv',
    'bahamut': W12_RAW / 'bahamut_uma_raw.csv',
    'gamme':   W12_RAW / 'gamme_uma_raw.csv',
    'udn':     W12_RAW / 'udn_uma_raw.csv',
}


def clean_date(val: str) -> str | None:
    """統一日期格式為 YYYY-MM-DD；Bahamut 的格式是 '2022-03-23 00:04:57 新增'"""
    if not val or pd.isna(val):
        return None
    val = str(val).strip()
    # 去除中文與時間部分
    val = re.sub(r'[^\d\-/ :]', '', val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(val[:19], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def import_source(source: str, path: Path) -> tuple[int, int]:
    if not path.exists():
        print(f'[SKIP] {source}: 檔案不存在 {path}')
        return 0, 0

    df = pd.read_csv(path, sep='|', on_bad_lines='skip')
    print(f'[INFO] {source}: {len(df)} rows loaded, cols={list(df.columns)}')

    created = updated = 0
    for _, row in df.iterrows():
        item_id = str(row.get('item_id', '')).strip()
        if not item_id:
            continue

        # 加上來源前綴避免與 bilibili item_id 衝突
        full_id = f'{source}_{item_id}'

        date_val = clean_date(row.get('date'))
        content  = str(row.get('content', '') or '')
        title    = str(row.get('title', '') or '')

        if not content and not title:
            continue

        _, created_flag = NewsData.objects.update_or_create(
            item_id=full_id,
            defaults={
                'date':            date_val,
                'category':        str(row.get('category', '其他') or '其他'),
                'title':           title[:500],
                'content':         content,
                'link':            str(row.get('link', '') or '') or None,
                'photo_link':      str(row.get('photo_link', '') or '') or None,
                'tokens_filtered': None,
                'token_pos':       None,
                'top_key_freq':    None,
                'sentiment':       float(row['sentiment']) if pd.notna(row.get('sentiment')) else None,
                'source':          source,
            }
        )
        if created_flag:
            created += 1
        else:
            updated += 1

    return created, updated


def main():
    print('=' * 50)
    total_created = total_updated = 0
    for source, path in SOURCES.items():
        c, u = import_source(source, path)
        print(f'  {source}: created={c}, updated={u}')
        total_created += c
        total_updated += u

    print()
    print(f'匯入完成 — 新增:{total_created}  更新:{total_updated}')
    print()

    # 各來源統計
    from django.db.models import Count
    stats = NewsData.objects.values('source').annotate(n=Count('item_id')).order_by('-n')
    print('各來源統計：')
    for s in stats:
        print(f"  {s['source']:12s}: {s['n']} 筆")
    print(f'  Total: {NewsData.objects.count()} 筆')


if __name__ == '__main__':
    main()
