"""
pipeline/crawl_udn_uma.py
聯合新聞網遊戲角落 — 賽馬娘相關文章爬蟲
目標：https://game.udn.com/game/search/馬娘
輸出：data/raw/udn_uma_raw.csv（pipe 分隔，UTF-8 BOM）

欄位：item_id | title | date | category | content | link | photo_link | source
source 固定為 'udn'

Phase 2c 新增：爬取後同步寫入 NewsData DB（status='raw'）。

用法（在專案根目錄執行）：
    python pipeline/crawl_udn_uma.py
    python pipeline/crawl_udn_uma.py --max-pages 5   # 只爬前 5 頁
    python pipeline/crawl_udn_uma.py --max-articles 30
"""
import re
import time
import random
import argparse
import os
import sys
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from urllib.parse import urljoin

# ── Django 環境（Phase 2c）──────────────────────────────────
_ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(_ROOT_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

# ── 常數 ─────────────────────────────────────────────────────
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


SOURCE       = 'udn'
SEARCH_URL   = 'https://game.udn.com/game/search/%E9%A6%AC%E5%A8%98'
BASE_URL     = 'https://game.udn.com'
MAX_PAGES    = 50
MAX_ARTICLES = 0       # 0 = 不限
MAX_RETRIES  = 3
DELAY_MIN    = _env_float('CRAWLER_DELAY_MIN', 1.0)
DELAY_MAX    = _env_float('CRAWLER_DELAY_MAX', 2.0)

ROOT_DIR  = Path(__file__).parent.parent
OUT_CSV   = ROOT_DIR / 'data' / 'raw' / 'udn_uma_raw.csv'
FAIL_CSV  = ROOT_DIR / 'data' / 'raw' / 'udn_uma_failed.csv'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer':         'https://game.udn.com/',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8',
}
HEADERS['User-Agent'] = os.getenv('CRAWLER_USER_AGENT', HEADERS['User-Agent'])

CSV_COLUMNS = ['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']  # P3 修復

# ── 分類 ──────────────────────────────────────────────────────
def classify_title(title: str) -> str:
    t = title
    if any(k in t for k in ['活動', '周年', '慶典', '獎勵', '節慶']):
        return '活動'
    if any(k in t for k in ['卡池', '限定', 'Gacha', '扭蛋', 'SR', 'SSR']):
        return '卡池'
    if any(k in t for k in ['賽事', '競技', '錦標', '排名', '決賽']):
        return '競賽'
    if any(k in t for k in ['更新', '維護', '系統', 'BUG', '修復']):
        return '系統'
    return '其他'

# ── 斷點續爬 ──────────────────────────────────────────────────
def load_crawled_ids() -> set:
    if not OUT_CSV.exists():
        return set()
    try:
        df = pd.read_csv(OUT_CSV, sep='|', encoding='utf-8-sig', usecols=['item_id'])
        ids = set(df['item_id'].dropna().astype(str))
        print(f'  [斷點續爬] 已有 {len(ids)} 筆，將跳過')
        return ids
    except Exception as e:
        print(f'  [斷點續爬] 讀取失敗: {e}，從頭開始')
        return set()

def append_row(row: dict):
    df = pd.DataFrame([row], columns=CSV_COLUMNS)
    write_header = not OUT_CSV.exists()
    df.to_csv(OUT_CSV, sep='|', index=False, encoding='utf-8-sig', mode='a', header=write_header)
    # Phase 2c: 同步寫 DB
    _upsert_to_db(row)


def _upsert_to_db(row: dict) -> None:
    """將單筆資料 update_or_create 至 NewsData DB（status='raw'）。"""
    try:
        from app_user_keyword_db.models import NewsData
        NewsData.objects.update_or_create(
            item_id=row['item_id'],
            defaults={
                'source':     row.get('source', SOURCE),
                'date':       row.get('date') or None,
                'category':   row.get('category', '其他'),
                'title':      row.get('title', ''),
                'content':    row.get('content', ''),
                'link':       row.get('link', '') or None,
                'photo_link': row.get('photo_link', '') or None,
                'status':     'raw',
            },
        )
    except Exception as exc:
        print(f"  [DB warn] {row.get('item_id','?')} 寫入失敗：{exc}")


def append_failed(item_id: str, url: str, reason: str):
    df = pd.DataFrame([{'item_id': item_id, 'url': url, 'reason': reason,
                         'ts': datetime.now().isoformat(timespec='seconds')}])
    write_header = not FAIL_CSV.exists()
    df.to_csv(FAIL_CSV, index=False, encoding='utf-8-sig', mode='a', header=write_header)

# ── HTTP ──────────────────────────────────────────────────────
def fetch(url: str) -> BeautifulSoup | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, 'html.parser')
        except Exception as e:
            wait = attempt * 3
            if attempt < MAX_RETRIES:
                print(f'    [重試 {attempt}/{MAX_RETRIES}] {e}，等 {wait}s')
                time.sleep(wait)
            else:
                print(f'    [失敗] {url}: {e}')
    return None

# ── 列表頁 ────────────────────────────────────────────────────
def collect_links(max_pages: int, crawled_ids: set) -> list[dict]:
    entries = []
    seen    = set()

    for page in range(1, max_pages + 1):
        url  = f'{SEARCH_URL}?page={page}' if page > 1 else SEARCH_URL
        print(f'  搜尋第 {page} 頁：{url}')
        soup = fetch(url)
        if not soup:
            break

        # 文章連結：.story-list 下的 a（2026 年實際結構）
        links = soup.select('.story-list a[href]')

        page_new = 0
        for a in links:
            href  = a.get('href', '')
            if not href or href in seen:
                continue
            # 只要站內遊戲文章（含 story 路徑）
            if '/game/' not in href and '/story/' not in href:
                continue
            seen.add(href)
            full_url = href if href.startswith('http') else urljoin(BASE_URL, href)
            # 從 URL 取 item_id
            m = re.search(r'/(\d+)', href)
            item_id = f'udn_{m.group(1)}' if m else f'udn_{abs(hash(href)) % 10**8}'
            if item_id in crawled_ids:
                continue
            title = a.get_text(strip=True) or ''
            entries.append({'item_id': item_id, 'url': full_url, 'title': title})
            page_new += 1

        print(f'    本頁新增 {page_new} 筆，累計 {len(entries)} 筆')
        if not page_new:
            print('    無新文章，停止翻頁')
            break
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return entries

# ── 文章頁 ────────────────────────────────────────────────────
def parse_article(soup: BeautifulSoup, entry: dict) -> dict:
    # 標題
    title = entry['title']
    for sel in ['h1.article-content__title', 'h1', '.story-headline h2']:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get_text(strip=True)
            break

    # 日期
    date = ''
    for sel in ['.article-content__time', 'time', '.story-date']:
        tag = soup.select_one(sel)
        if tag:
            raw = tag.get('datetime') or tag.get_text(strip=True)
            try:
                date = pd.to_datetime(raw).strftime('%Y-%m-%d')
            except Exception:
                date = re.sub(r'\s+', ' ', raw)[:20]
            break

    # 內文
    content = ''
    for sel in ['.article-content__editor', '.story-body', '.post-content']:
        tag = soup.select_one(sel)
        if tag:
            for noise in tag.find_all(['script', 'style', 'aside']):
                noise.decompose()
            content = re.sub(r'\n{3,}', '\n\n', tag.get_text(separator='\n').strip())
            break
    if not content:
        content = '找不到內文'

    # 代表圖
    photo_link = ''
    og = soup.find('meta', property='og:image')
    if og and og.get('content'):
        photo_link = og['content']

    return {
        'item_id':    entry['item_id'],
        'title':      title,
        'date':       date,
        'category':   classify_title(title),
        'content':    content,
        'link':       entry['url'],
        'photo_link': photo_link,
        'source':     SOURCE,
    }

# ── 主程式 ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-pages',    type=int, default=MAX_PAGES)
    parser.add_argument('--max-articles', type=int, default=MAX_ARTICLES)
    parser.add_argument('--playwright', action='store_true', help='（保留參數，不作用）')
    args = parser.parse_args()

    print('=' * 55)
    print('  聯合新聞網遊戲角落 賽馬娘爬蟲')
    print('=' * 55)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        print(f'連線成功（{r.status_code}）\n')
    except Exception as e:
        print(f'無法連線：{e}')
        return

    crawled_ids = load_crawled_ids()
    entries     = collect_links(args.max_pages, crawled_ids)
    if args.max_articles > 0:
        entries = entries[:args.max_articles]

    if not entries:
        print('沒有新文章可爬')
        return

    success = failed = 0
    elapsed = []
    for i, entry in enumerate(entries, 1):
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        eta_str = ''
        if elapsed:
            avg = sum(elapsed[-30:]) / len(elapsed[-30:])
            eta_str = f'  ETA {timedelta(seconds=int(avg * (len(entries) - i)))}'
        print(f'[{i}/{len(entries)}] {entry["title"][:40]}  (等 {delay:.1f}s{eta_str})')
        time.sleep(delay)

        t0   = time.time()
        soup = fetch(entry['url'])
        if soup is None:
            append_failed(entry['item_id'], entry['url'], '請求失敗')
            failed += 1
            continue
        row = parse_article(soup, entry)
        append_row(row)
        elapsed.append(time.time() - t0 + delay)
        success += 1

    print(f'\n完成：成功 {success} 篇，失敗 {failed} 篇，輸出 → {OUT_CSV}')

if __name__ == '__main__':
    main()
