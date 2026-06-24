"""
巴哈姆特 賽馬娘哈啦板 (bsn=34421) 文章爬蟲
輸出: bahamut_uma_raw.csv

升級功能:
  - 斷點續爬: 已爬過的 sna 自動跳過，可隨時中斷再繼續
  - 即時寫入: 每篇爬完立刻 append 至 CSV，不怕中途中斷遺失
  - 自動重試: 單篇失敗最多重試 3 次，失敗清單另存 bahamut_uma_failed.csv
  - 進度顯示: 顯示已爬/總篇數與預估剩餘時間
  - 全頁爬取: MAX_PAGES=293 預設爬完所有看板頁

Phase 2c 新增：爬取後同步寫入 NewsData DB（status='raw'）。

爬蟲流程:
  1. 爬取看板列表頁 (B.php?bsn=34421&page=N) 收集文章連結
  2. 逐篇進入文章頁面 (C.php?bsn=34421&snA=XXXX) 擷取內文
  3. 儲存為 pipe-separated CSV (與其他爬蟲格式一致)
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
import os
import sys
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timedelta

# ── Django 環境（Phase 2c）──────────────────────────────────
_ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(_ROOT_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

BASE_URL  = "https://forum.gamer.com.tw"
BOARD_URL = "https://forum.gamer.com.tw/B.php?bsn=34421"
BSN       = "34421"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://forum.gamer.com.tw/",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}
HEADERS["User-Agent"] = os.getenv("CRAWLER_USER_AGENT", HEADERS["User-Agent"])

MAX_PAGES    = 293  # 看板總頁數；0 = 不限制
MAX_ARTICLES = 0    # 最多爬取幾篇文章；0 = 不限制
MAX_RETRIES  = 3    # 單篇文章最多重試次數
DELAY_MIN    = _env_float("CRAWLER_DELAY_MIN", 0.8)  # 請求間最小延遲 (秒)
DELAY_MAX    = _env_float("CRAWLER_DELAY_MAX", 1.5)  # 請求間最大延遲 (秒)

OUT_DIR     = Path(__file__).parent
OUT_CSV     = OUT_DIR / "bahamut_uma_raw.csv"
# P2 修復：輸出路徑改為 data/raw/
ROOT_DIR    = Path(__file__).parent.parent
OUT_CSV     = ROOT_DIR / "data" / "raw" / "bahamut_uma_raw.csv"
FAILED_CSV  = ROOT_DIR / "data" / "raw" / "bahamut_uma_failed.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# P2 修復：CSV_COLUMNS 對齊統一規格（標準欄位在前，Bahamut 獨有欄位在後）
CSV_COLUMNS = [
    "item_id", "source", "date", "category", "title", "content",
    "link", "photo_link",
    "raw_category", "author", "gp", "reply_count", "view_count",
]

# P2 修復：論壇標籤 → 標準分類對應表
CATEGORY_MAP = {
    "公告": "其他", "情報": "其他", "活動": "活動", "系統": "系統",
    "討論": "其他", "閒聊": "其他", "問題": "其他", "心得": "其他",
    "攻略": "系統", "整理": "其他", "史實": "其他",
    "繪圖": "其他", "繪畫": "其他", "小說": "其他",
    "非洲集中串": "其他", "新馬娘串": "其他", "歐洲集中串": "其他",
}


def normalize_category(raw_cat: str) -> str:
    """論壇原始標籤 → 標準分類（活動/卡池/競賽/系統/其他）"""
    return CATEGORY_MAP.get(str(raw_cat).strip(), "其他")


# ──────────────────────────────────────────────
# 斷點續爬：讀取已爬 sna 集合
# ──────────────────────────────────────────────

def load_crawled_snas() -> set[str]:
    """從現有 CSV 讀取已爬過的 sna，用於跳過。"""
    if not OUT_CSV.exists():
        return set()
    try:
        df = pd.read_csv(OUT_CSV, sep="|", encoding="utf-8-sig", usecols=["item_id"])
        snas = set(
            row.replace("bahamut_", "")
            for row in df["item_id"].dropna().astype(str)
        )
        print(f"  [斷點續爬] 發現現有資料 {len(snas)} 筆，將跳過已爬文章")
        return snas
    except Exception as e:
        print(f"  [斷點續爬] 讀取現有 CSV 失敗: {e}，從頭開始")
        return set()


def append_row(row: dict) -> None:
    """將單筆資料即時 append 至 CSV（不需要載入整個檔案）。"""
    df = pd.DataFrame([row], columns=CSV_COLUMNS)
    write_header = not OUT_CSV.exists()
    df.to_csv(
        OUT_CSV, sep="|", index=False, encoding="utf-8-sig",
        mode="a", header=write_header,
    )
    # Phase 2c: 同步寫 DB
    _upsert_to_db(row)


def _upsert_to_db(row: dict) -> None:
    """將單筆資料 update_or_create 至 NewsData DB（status='raw'）。"""
    try:
        from app_user_keyword_db.models import NewsData
        NewsData.objects.update_or_create(
            item_id=row['item_id'],
            defaults={
                'source':     row.get('source', 'bahamut'),
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


def append_failed(entry: dict, reason: str) -> None:
    """記錄爬取失敗的文章。"""
    df = pd.DataFrame([{
        "sna":    entry["sna"],
        "title":  entry["title"],
        "url":    entry["url"],
        "reason": reason,
        "ts":     datetime.now().isoformat(timespec="seconds"),
    }])
    write_header = not FAILED_CSV.exists()
    df.to_csv(FAILED_CSV, index=False, encoding="utf-8-sig", mode="a", header=write_header)


# ──────────────────────────────────────────────
# 分類標籤
# ──────────────────────────────────────────────

def classify_title(title: str) -> str:
    """依文章標題中的 【】 標籤取得原始論壇分類（raw_category）。"""
    m = re.search(r'【(.+?)】', title)
    if m:
        return m.group(1)
    return "其他"


def parse_date_bahamut(raw: str) -> str:
    """
    P2 修復：清理巴哈日期格式
    '2022-03-23 00:04:57 編輯' → '2022-03-23'
    '2022/03/23' → '2022-03-23'
    """
    raw = re.sub(r'\s*編輯\s*$', '', str(raw)).strip()
    m = re.match(r'(\d{4})[-/](\d{2})[-/](\d{2})', raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return '2024-01-01'


# ──────────────────────────────────────────────
# Step 1: 收集看板文章連結
# ──────────────────────────────────────────────

def get_board_page(page: int) -> BeautifulSoup | None:
    """取得看板列表頁的 BeautifulSoup 物件，失敗時重試一次。"""
    url = f"{BOARD_URL}&page={page}"
    for attempt in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt == 0:
                print(f"  [重試] 第 {page} 頁列表取得失敗: {e}，等 3s 後重試")
                time.sleep(3)
            else:
                print(f"  [錯誤] 第 {page} 頁列表取得失敗: {e}")
    return None


def collect_article_links(
    max_pages: int = MAX_PAGES,
    crawled_snas: set[str] | None = None,
) -> list[dict]:
    """
    爬取看板列表頁，回傳「尚未爬過」的文章資訊清單。
    每筆包含: title, url, sna, reply_count, view_count, category
    """
    if crawled_snas is None:
        crawled_snas = set()

    entries   = []
    seen_sna  = set()
    pages     = range(1, max_pages + 1) if max_pages > 0 else range(1, 9999)

    for page in pages:
        print(f"  爬取看板第 {page} 頁...")
        soup = get_board_page(page)
        if not soup:
            break

        article_links = soup.find_all(
            "a",
            href=re.compile(r'C\.php\?bsn=' + BSN + r'&snA=\d+')
        )

        page_new = 0
        for a in article_links:
            href = a.get("href", "")
            qs   = parse_qs(urlparse(href).query)
            sna  = qs.get("snA", [""])[0]
            if not sna or sna in seen_sna:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 2:
                continue
            if "廣告" in title:
                continue

            seen_sna.add(sna)

            if sna in crawled_snas:
                continue  # 已爬過，跳過

            full_url = urljoin(BASE_URL, f"C.php?bsn={BSN}&snA={sna}")

            reply_count = ""
            view_count  = ""
            tr = a.find_parent("tr")
            if tr:
                for td in tr.find_all("td"):
                    cls = " ".join(td.get("class", []))
                    txt = td.get_text(strip=True)
                    if "reply" in cls.lower():
                        reply_count = txt
                    elif "visit" in cls.lower() or "count" in cls.lower():
                        view_count = txt

            entries.append({
                "title":       title,
                "url":         full_url,
                "sna":         sna,
                "reply_count": reply_count,
                "view_count":  view_count,
                "category":    classify_title(title),
            })
            page_new += 1

        total_on_page = len([
            a for a in article_links
            if parse_qs(urlparse(a.get("href","")).query).get("snA",[""])[0]
        ])
        print(f"    本頁 {total_on_page} 篇，新增 {page_new} 筆，待爬累計 {len(entries)} 筆")

        if total_on_page == 0:
            print("    本頁無文章，停止翻頁")
            break

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"\n共收集到 {len(entries)} 篇待爬文章")
    return entries


# ──────────────────────────────────────────────
# Step 2: 爬取單篇文章內容（含重試）
# ──────────────────────────────────────────────

def fetch_article_html(url: str) -> BeautifulSoup | None:
    """帶重試機制的 HTTP 請求，回傳 BeautifulSoup 或 None。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            wait = attempt * 3
            if attempt < MAX_RETRIES:
                print(f"  [重試 {attempt}/{MAX_RETRIES}] {e}，等 {wait}s")
                time.sleep(wait)
            else:
                print(f"  [失敗] {MAX_RETRIES} 次重試均失敗: {e}")
    return None


def parse_article(soup: BeautifulSoup, entry: dict) -> dict:
    """從 BeautifulSoup 解析文章欄位，回傳 dict。"""

    # ── 標題 ──
    title = entry["title"]
    tag = soup.select_one(".c-post__header__title")
    if tag:
        title = tag.get_text(strip=True)

    # ── 作者 ──
    author = ""
    name_tag = soup.select_one(".username")
    id_tag   = soup.select_one(".userid")
    if name_tag:
        author = name_tag.get_text(strip=True)
        if id_tag:
            author += f" ({id_tag.get_text(strip=True)})"
    else:
        tag = soup.select_one(".c-post__header__author")
        if tag:
            author = tag.get_text(strip=True)

    # ── 日期 ──
    date = ""
    tag = soup.select_one(".c-post__header__info")
    if tag:
        date = tag.get_text(strip=True)
    if not date:
        tag = soup.select_one(".edittime")
        if tag:
            date = tag.get_text(strip=True)

    # ── 內文 ──
    content = ""
    tag = soup.select_one(".c-article__content")
    if not tag:
        tag = soup.select_one(".c-post__body")
    if tag:
        for noise in tag.find_all(["script", "style"]):
            noise.decompose()
        content = re.sub(r'\n{3,}', '\n\n', tag.get_text(separator='\n').strip())
        content = re.sub(r'[ \t]+', ' ', content)
    if not content:
        content = "找不到內文"

    # ── GP 數 ──
    gp = ""
    tag = soup.select_one(".postgp")
    if tag:
        m = re.search(r'(\d+)', tag.get_text(strip=True))
        if m:
            gp = m.group(1)

    # ── 代表圖 ──
    photo_link = ""
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        photo_link = og_img["content"]

    raw_category = entry.get("category", "其他")  # 原始論壇標籤（如「討論」「情報」）

    return {
        "item_id":      f"bahamut_{entry['sna']}",
        "source":       "bahamut",
        "date":         parse_date_bahamut(date),
        "category":     normalize_category(raw_category),
        "title":        title,
        "content":      content,
        "link":         entry["url"],
        "photo_link":   photo_link,
        "raw_category": raw_category,
        "author":       author,
        "gp":           gp,
        "reply_count":  entry.get("reply_count", ""),
        "view_count":   entry.get("view_count", ""),
    }


def crawl_article(entry: dict, idx: int, total: int, elapsed_times: list[float]) -> bool:
    """
    爬取並即時寫入單篇文章。
    回傳 True 表示成功，False 表示失敗。
    elapsed_times 用於計算平均速度與預估剩餘時間。
    """
    sleep_t = random.uniform(DELAY_MIN, DELAY_MAX)

    # ── 預估剩餘時間 ──
    remaining = total - idx
    if elapsed_times:
        avg_sec = sum(elapsed_times[-50:]) / len(elapsed_times[-50:])  # 用最近50筆
        eta = timedelta(seconds=int(avg_sec * remaining))
        eta_str = f"  ETA {eta}"
    else:
        eta_str = ""

    print(f"[{idx}/{total}] [{entry['category']}] {entry['title'][:40]}"
          f"  (等 {sleep_t:.1f}s{eta_str})")
    time.sleep(sleep_t)

    t0   = time.time()
    soup = fetch_article_html(entry["url"])

    if soup is None:
        append_failed(entry, "請求失敗 (重試耗盡)")
        return False

    row = parse_article(soup, entry)
    append_row(row)
    elapsed_times.append(time.time() - t0 + sleep_t)
    return True


# ──────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  巴哈姆特 賽馬娘哈啦板 全站爬蟲 (斷點續爬版)")
    print("=" * 55)
    print(f"  目標 : {BOARD_URL}")
    print(f"  頁數 : {MAX_PAGES if MAX_PAGES > 0 else '無限'} 頁")
    print(f"  輸出 : {OUT_CSV}")
    print(f"  失敗 : {FAILED_CSV}")
    print("=" * 55 + "\n")

    # 測試連線
    try:
        r = requests.get(BOARD_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        print(f"連線成功 (狀態碼: {r.status_code})\n")
    except Exception as e:
        print(f"無法連線至巴哈姆特: {e}")
        return

    # 斷點：讀取已爬 sna
    crawled_snas = load_crawled_snas()

    # Step 1: 收集待爬清單
    entries = collect_article_links(max_pages=MAX_PAGES, crawled_snas=crawled_snas)
    if not entries:
        print("所有文章均已爬取完畢，或沒有收集到連結")
        return

    if MAX_ARTICLES > 0:
        entries = entries[:MAX_ARTICLES]
        print(f"限制最多 {MAX_ARTICLES} 篇，本次爬取 {len(entries)} 篇\n")

    # Step 2: 逐篇爬取（即時寫入）
    success = 0
    failed  = 0
    elapsed_times: list[float] = []
    start_time = time.time()

    for i, entry in enumerate(entries):
        ok = crawl_article(entry, i + 1, len(entries), elapsed_times)
        if ok:
            success += 1
        else:
            failed += 1

    # 最終統計
    total_sec = time.time() - start_time
    print("\n" + "=" * 55)
    print(f"  爬取完成！")
    print(f"  成功: {success} 篇  失敗: {failed} 篇")
    print(f"  總耗時: {timedelta(seconds=int(total_sec))}")
    print(f"  輸出: {OUT_CSV}")
    if failed:
        print(f"  失敗清單: {FAILED_CSV}")

    # 印出分類統計
    if OUT_CSV.exists():
        try:
            df_all = pd.read_csv(OUT_CSV, sep="|", encoding="utf-8-sig")
            print(f"\n  資料庫現有 {len(df_all)} 筆，各分類統計:")
            print(df_all["category"].value_counts().to_string())
        except Exception:
            pass
    print("=" * 55)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='巴哈姆特賽馬娘爬蟲')
    parser.add_argument('--max-pages',    type=int, default=MAX_PAGES,
                        help='最多爬取幾頁看板列表（0=不限制）')
    parser.add_argument('--max-articles', type=int, default=MAX_ARTICLES,
                        help='最多爬取幾篇文章（0=不限制）')
    parser.add_argument('--playwright', action='store_true', help='（保留參數，不作用）')
    args = parser.parse_args()
    MAX_PAGES    = args.max_pages
    MAX_ARTICLES = args.max_articles
    main()
