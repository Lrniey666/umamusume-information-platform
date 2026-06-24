"""
pipeline/generate_mock_multisource.py
生成多來源假資料 CSV，用於 Track B（DB）與 Track C（前端）在爬蟲完成前進行測試。

輸出：data/processed/uma_news_mock_multisource.csv
      每個 source 各 10 筆，共 50 筆，欄位符合凍結 Schema（含 source 欄位）

用法（在專案根目錄執行）：
    python pipeline/generate_mock_multisource.py
"""
import os
import random
import csv
from datetime import date, timedelta
from pathlib import Path

# ── 常數設定 ──────────────────────────────────────────────────
SOURCES = ['bilibili', 'bahamut', 'udn', 'ettoday', 'gamme']
ROWS_PER_SOURCE = 10

ROOT_DIR    = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / 'data' / 'processed' / 'uma_news_mock_multisource.csv'

CATEGORIES   = ['活動', '卡池', '競賽', '系統', '其他']
CATEGORY_KW  = {
    '活動': ['活動', '限定', '周年', '獎勵', '報酬'],
    '卡池': ['卡池', '限定', '育成', '抽卡', 'SR'],
    '競賽': ['競賽', '排名', '決賽', '排行', '冠軍'],
    '系統': ['系統', '更新', '維護', '修復', 'BUG'],
    '其他': ['情報', '公告', '預告', '活動'],
}
SOURCE_NAMES = {
    'bilibili': 'Bilibili BWIKI',
    'bahamut':  '巴哈姆特',
    'udn':      '聯合新聞網',
    'ettoday':  'ETtoday',
    'gamme':    '宅宅新聞',
}
SOURCE_URLS = {
    'bilibili': 'https://wiki.biligame.com/umamusume/{}',
    'bahamut':  'https://forum.gamer.com.tw/C.php?bsn=34421&snA={}',
    'udn':      'https://game.udn.com/game/story/{}',
    'ettoday':  'https://game.ettoday.net/news/{}',
    'gamme':    'https://news.gamme.com.tw/{}/',
}
PHOTO_BASE = 'https://via.placeholder.com/400x225?text={}'

COLUMNS = [
    'item_id', 'title', 'date', 'category', 'content',
    'link', 'photo_link', 'source',
    'tokens_filtered', 'top_key_freq', 'sentiment',
]


def _random_date() -> str:
    """回傳過去 52 週內的隨機日期（YYYY-MM-DD）。"""
    today   = date.today()
    offset  = random.randint(0, 364)
    return (today - timedelta(days=offset)).strftime('%Y-%m-%d')


def _make_content(category: str, source_name: str) -> str:
    kws = CATEGORY_KW[category]
    kw1, kw2 = random.sample(kws, 2)
    return (
        f"【{source_name}報導】本次{category}情報如下。\n"
        f"本次活動與「{kw1}」及「{kw2}」密切相關，"
        f"玩家可於活動期間獲得豐富獎勵，詳情請見官方公告。\n"
        f"此為 Mock 測試資料，供開發期間驗證多來源篩選功能使用。"
    )


def _make_tokens(category: str) -> str:
    kws = CATEGORY_KW[category]
    return ' '.join(random.sample(kws, min(3, len(kws))))


def _make_top_key_freq(category: str) -> str:
    kws = CATEGORY_KW[category]
    pairs = [(kw, random.randint(1, 20)) for kw in kws]
    return str(pairs)


def generate():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for source in SOURCES:
        source_name = SOURCE_NAMES[source]
        url_tmpl    = SOURCE_URLS[source]
        for i in range(1, ROWS_PER_SOURCE + 1):
            category    = CATEGORIES[(i - 1) % len(CATEGORIES)]
            item_id     = f'{source}_{i}'
            title       = f'【Mock】{source_name} {category}情報 #{i:02d}'
            dt          = _random_date()
            content     = _make_content(category, source_name)
            link        = url_tmpl.format(random.randint(10000, 99999))
            photo_link  = PHOTO_BASE.format(f'{source}+{i}')
            tokens      = _make_tokens(category)
            top_key_freq = _make_top_key_freq(category)
            sentiment   = round(random.uniform(0.0, 1.0), 2)

            rows.append({
                'item_id':       item_id,
                'title':         title,
                'date':          dt,
                'category':      category,
                'content':       content,
                'link':          link,
                'photo_link':    photo_link,
                'source':        source,
                'tokens_filtered': tokens,
                'top_key_freq':  top_key_freq,
                'sentiment':     sentiment,
            })

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter='|')
        writer.writeheader()
        writer.writerows(rows)

    print(f'[OK] 生成 {len(rows)} 筆 Mock 資料 → {OUTPUT_PATH}')
    for source in SOURCES:
        count = sum(1 for r in rows if r['source'] == source)
        print(f'     {source:12s}: {count} 筆')


if __name__ == '__main__':
    generate()
