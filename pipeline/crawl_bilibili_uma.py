"""
T1: Bilibili 賽馬娘 WIKI 公告爬蟲
輸出: data/raw/bilibili_uma_raw.csv

P1 修復：
- 輸出路徑改為 data/raw/
- 新增 source 欄位
- 日期在爬蟲端解析為 YYYY-MM-DD
- 分類/標題/內容在爬蟲端完成簡→繁體轉換（preprocess.py 不再需要做）
- CSV_COLUMNS 對齊統一規格

Phase 2c 修復：
- item_id 改為 URL slug（穩定化，避免重爬偽新增）
- 爬取後同步寫入 NewsData DB（status='raw'）
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, unquote
from collections import Counter

# ── Django 環境（Phase 2c：直寫 DB）─────────────────────────
_PIPELINE_DIR = Path(__file__).parent
_ROOT_DIR     = _PIPELINE_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(_ROOT_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

try:
    from opencc import OpenCC
    cc = OpenCC('s2t')
    USE_OPENCC = True
except ImportError:
    try:
        from opencc_python_reimplemented import OpenCC
        cc = OpenCC('s2t')
        USE_OPENCC = True
    except ImportError:
        USE_OPENCC = False
        print("[warn] opencc 不可用，跳過簡繁轉換")

BASE_URL = "https://wiki.biligame.com"
LIST_URL = "https://wiki.biligame.com/umamusume/%E5%85%AC%E5%91%8A"


# ── Phase 2c: 穩定 item_id（URL slug）────────────────────────
def _make_item_id(url: str) -> str:
    """
    以頁面 URL 路徑 slug 作為穩定唯一鍵，避免重爬時索引變動導致偽新增。
    例：https://wiki.biligame.com/umamusume/活動公告/2026 → bilibili_活動公告_2026
    """
    raw_slug = unquote(url.rstrip('/').split('/umamusume/')[-1])
    slug = raw_slug.replace('/', '_')
    return f"bilibili_{slug}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
HEADERS["User-Agent"] = os.getenv("CRAWLER_USER_AGENT", HEADERS["User-Agent"])
MAX_PER_CATEGORY = 0   # 0 = 不限制

# P1 修復：輸出路徑改為 data/raw/
ROOT_DIR = Path(__file__).parent.parent
OUT_CSV  = ROOT_DIR / "data" / "raw" / "bilibili_uma_raw.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# P1 修復：欄位順序對齊統一規格
CSV_COLUMNS = ['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']

# 簡→繁分類對應
CATEGORY_MAP_S2T = {
    '活动': '活動', '竞赛': '競賽', '系统': '系統', '卡池': '卡池', '其他': '其他',
}


def to_traditional(text: str) -> str:
    if USE_OPENCC and text:
        return cc.convert(str(text))
    return str(text)


def classify_title(title: str) -> str:
    """分類標題（簡體輸入），輸出簡體分類後再轉繁體"""
    t = title.lower()
    if any(kw in t for kw in ['竞赛', '传奇竞赛', 'league', 'champions', 'champion']):
        return '競賽'
    if any(kw in t for kw in ['平衡', '调整', '通知', '赛道', '维护', '违规', '整顿',
                               '平衡', '調整', '通知', '賽道', '維護', '違規', '整頓']):
        return '系統'
    if any(kw in t for kw in ['卡池', '登场', '限定', '召开', 'pick up', '十连', '免费', '抽',
                               '登場', '限定', '召開', '十連', '免費']):
        return '卡池'
    if any(kw in t for kw in ['活动', 'anniversary', '周年', '情人节', '报酬', '剧本', '战令',
                               '活動', '周年', '情人節', '報酬', '劇本', '戰令']):
        return '活動'
    return '其他'


def parse_date_bilibili(raw: str) -> str:
    """
    P1 修復：在爬蟲端解析日期
    '2025年3月8日 (星期六) 01:09' → '2025-03-08'
    """
    if not raw:
        return '2024-01-01'
    m = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', raw)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m2 = re.search(r'(\d{4})[.\-](\d{2})[.\-](\d{2})', raw)
    if m2:
        return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
    return '2024-01-01'


def test_connection():
    print(f"測試連線: {LIST_URL}")
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        print(f"狀態碼: {r.status_code}, 頁面長度: {len(r.text)}")
        return r.status_code == 200, r
    except Exception as e:
        print(f"連線失敗: {e}")
        return False, None


def collect_links(soup):
    entries = []
    content_area = soup.find("div", id="mw-content-text")
    if not content_area:
        print("找不到 mw-content-text")
        return entries

    seen = set()
    blacklist = ["首页", "圖鑑", "Main_Page", "公告", "首頁", "创建新页面"]
    for a in content_area.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/umamusume/" not in href or ":" in href:
            continue
        if any(w in href or w in title for w in blacklist):
            continue
        if not title or len(title) < 3:
            continue
        full_url = urljoin(BASE_URL, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        entries.append({"title": title, "url": full_url, "category": classify_title(title)})

    print(f"收集到 {len(entries)} 篇公告連結")
    for cat, cnt in Counter(e["category"] for e in entries).most_common():
        print(f"  {cat}: {cnt}")
    return entries


def select_articles(entries):
    if MAX_PER_CATEGORY == 0:
        print(f"選取全部 {len(entries)} 篇文章（無限制）")
        return entries
    selected, counts = [], Counter()
    for e in entries:
        if counts[e["category"]] < MAX_PER_CATEGORY:
            selected.append(e)
            counts[e["category"]] += 1
    print(f"選取 {len(selected)} 篇文章準備爬取")
    return selected


def crawl_article(entry, idx, total):
    sleep_t = random.uniform(0.8, 1.5)
    print(f"[{idx}/{total}] [{entry['category']}] {entry['title'][:40]} (等 {sleep_t:.1f}s)")
    time.sleep(sleep_t)
    try:
        res     = requests.get(entry["url"], headers=HEADERS, timeout=15)
        soup    = BeautifulSoup(res.text, "html.parser")

        title_tag = soup.find("h1", id="firstHeading")
        title     = title_tag.text.strip() if title_tag else entry["title"]

        content_div = soup.find("div", id="mw-content-text")
        if content_div:
            for tag in content_div.find_all(["script", "style", "table"]):
                tag.decompose()
            content = re.sub(r'\n+', '\n', content_div.get_text(separator='\n').strip())
            content = re.sub(r'[ \t]+', ' ', content)
        else:
            content = "找不到內文"

        img_link = ""
        if content_div:
            img_tag = content_div.find("img", src=True)
            if img_tag:
                img_link = img_tag["src"]

        time_text = ""
        time_match = re.search(r"此页面最后编辑于(.+?)。", soup.text)
        if time_match:
            time_text = time_match.group(1).strip()

        # P1 修復：在爬蟲端完成日期解析 + 簡→繁體轉換
        category_tw = to_traditional(entry["category"])
        title_tw    = to_traditional(title)
        content_tw  = to_traditional(content)

        return {
            "item_id":    _make_item_id(entry["url"]),   # Phase 2c: URL slug
            "source":     "bilibili",
            "date":       parse_date_bilibili(time_text),
            "category":   category_tw,
            "title":      title_tw,
            "content":    content_tw,
            "link":       entry["url"],
            "photo_link": img_link,
        }
    except Exception as e:
        print(f"  爬取失敗: {e}")
        return None


def _upsert_to_db(rows: list) -> None:
    """將爬取結果 update_or_create 至 NewsData DB（status='raw'）。"""
    try:
        from app_user_keyword_db.models import NewsData
        created = updated = 0
        for row in rows:
            _, is_new = NewsData.objects.update_or_create(
                item_id=row['item_id'],
                defaults={
                    'source':     row.get('source', 'bilibili'),
                    'date':       row.get('date') or None,
                    'category':   row.get('category', '其他'),
                    'title':      row.get('title', ''),
                    'content':    row.get('content', ''),
                    'link':       row.get('link', '') or None,
                    'photo_link': row.get('photo_link', '') or None,
                    'status':     'raw',
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1
        print(f"[bilibili DB] 新增 {created} 筆，更新 {updated} 筆")
    except Exception as exc:
        print(f"[bilibili DB] 寫入失敗（CSV 仍已正常寫出）：{exc}")


def main():
    ok, resp = test_connection()
    if not ok:
        print("\n無法連線至 Bilibili Wiki，保留現有資料")
        if OUT_CSV.exists():
            print(f"現有資料：{OUT_CSV}")
        return

    soup    = BeautifulSoup(resp.text, "html.parser")
    entries = collect_links(soup)
    if not entries:
        print("沒有收集到連結，終止")
        return

    selected = select_articles(entries)
    rows = []
    for i, entry in enumerate(selected):
        row = crawl_article(entry, i + 1, len(selected))
        if row:
            rows.append(row)

    df = pd.DataFrame(rows, columns=CSV_COLUMNS)
    df.to_csv(OUT_CSV, sep="|", index=False)
    print(f"\n爬取完成，共 {len(df)} 筆")
    print(df["category"].value_counts().to_string())
    print(f"已儲存至: {OUT_CSV}")

    # ── Phase 2c：同步寫入 NewsData DB ───────────────────────
    _upsert_to_db(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Bilibili 賽馬娘 WIKI 爬蟲')
    parser.add_argument('--max-pages',    type=int, default=0,
                        help='（保留參數，Bilibili 使用單頁模式，不作用）')
    parser.add_argument('--max-articles', type=int, default=MAX_PER_CATEGORY,
                        help='每個分類最多爬取幾篇（0=不限制）')
    parser.add_argument('--playwright', action='store_true', help='（保留參數，不作用）')
    args = parser.parse_args()
    MAX_PER_CATEGORY = args.max_articles
    main()
