"""
賽馬娘角色頁面 Bilibili 評論聲量爬蟲
============================================================
原理:
  Bilibili BWIKI 的每個角色頁面底部嵌入了 Bilibili 評論系統。
  評論是透過 Bilibili Reply API 載入的：
    https://api.bilibili.com/x/v2/reply?oid={oid}&type=17&...

  其中 oid 藏在角色頁面的 HTML 裡，可用 Selenium 取出。

  取得評論後，可用 SnowNLP 做情緒分析，
  輸出格式與 pk_taipei_mayor_election.csv 相同，
  供 Django 網站直接讀取顯示。

使用方式:
  python crawl_uma_comments.py

輸出:
  uma_comments_raw.csv     → 每條評論的原始資料 + 情緒分數
  pk_uma_characters.csv    → 仿 pk_taipei_mayor_election.csv 格式
                             (供 Django 網站直接使用)
============================================================
"""

import re
import os
import time
import json
import requests
import pandas as pd
from pathlib import Path
from collections import defaultdict

DIR     = Path(__file__).parent
RAW_CSV = DIR / "uma_comments_raw.csv"
PK_CSV  = DIR / "pk_uma_characters.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/",
}

# ── 目標角色 (从 uma_characters_bilingual.csv 或手動設定) ──
# char_id, 简体名, detail_url (繁中服角色頁)
TARGET_CHARS = [
    ("1001", "特别周",   "https://wiki.biligame.com/umamusume/%E3%80%90%E7%89%B9%E5%88%A5%E5%A4%A2%E6%83%B3%E5%AE%B6%E3%80%91%E7%89%B9%E5%88%A5%E9%80%B1"),
    ("1002", "无声铃鹿", "https://wiki.biligame.com/umamusume/%E3%80%90%E6%97%A0%E5%A3%B0%E6%97%A0%E7%91%95%E3%80%91%E6%97%A0%E5%A3%B0%E9%93%83%E9%B9%BF"),
    ("1006", "小栗帽",   "https://wiki.biligame.com/umamusume/%E3%80%90%E6%98%9F%E5%85%89%E8%B7%83%E5%8A%A8%E3%80%91%E5%B0%8F%E6%A0%97%E5%B8%BD"),
    ("1017", "鲁道夫象征","https://wiki.biligame.com/umamusume/%E3%80%90%E7%9A%87%E5%B8%9D%E3%80%91%E9%B2%81%E9%81%93%E5%A4%AB%E8%B1%A1%E5%BE%81"),
    ("1008", "伏特加",   "https://wiki.biligame.com/umamusume/%E3%80%90%E4%B8%8D%E4%BC%9A%E7%BB%93%E5%86%B0%E7%9A%84%E7%94%9F%E5%91%BD%E4%B9%8B%E6%B0%B4%E3%80%91%E4%BC%8F%E7%89%B9%E5%8A%A0"),
]


# ══════════════════════════════════════════════
# Step 1: 用 Selenium 取得角色頁面的 Bilibili oid
# ══════════════════════════════════════════════

def get_bilibili_oid(detail_url: str) -> str:
    """
    從角色 Wiki 頁面取得嵌入的 Bilibili 評論 oid。
    oid 通常存在於:
      - <div data-oid="...">
      - window.__INITIAL_STATE__ = {..., "oid": "..."}
      - 或 <script> 標籤內的 JS 變數
    """
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = ctx.new_page()
            try:
                page.goto(detail_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"  [goto 警告] {e}")
            time.sleep(6)
            try:
                page_src = page.content()
            except Exception:
                page_src = ""
            browser.close()

        # 方式1: 找 data-oid 屬性
        m = re.search(r'data-oid=["\'](\d+)["\']', page_src)
        if m:
            return m.group(1)

        # 方式2: 找 JS 變數中的 oid
        m = re.search(r'"oid"\s*:\s*"?(\d+)"?', page_src)
        if m:
            return m.group(1)

        # 方式3: 找 bwiki comment iframe src
        m = re.search(r'comment[^\'"]*["\']([^\'"]*bilibili[^\'"]*)["\']', page_src, re.I)
        if m:
            oid_m = re.search(r'oid=(\d+)', m.group(1))
            if oid_m:
                return oid_m.group(1)

        # 方式4: 找頁面 ID (MediaWiki 頁面 ID)
        m = re.search(r'"wgArticleId"\s*:\s*(\d+)', page_src)
        if m:
            print(f"  [注意] 找到 wgArticleId={m.group(1)}，嘗試用作 oid")
            return m.group(1)

        print(f"  [警告] 找不到 oid，頁面可能未載入評論組件")
        return ""

    except Exception as e:
        print(f"  Playwright 取 oid 失敗: {e}")
        return ""


# ══════════════════════════════════════════════
# Step 2: 用 Bilibili API 取得評論
# ══════════════════════════════════════════════

def fetch_comments(oid: str, max_pages: int = 5) -> list[dict]:
    """
    呼叫 Bilibili Reply API 取得評論。
    type=17 表示 Wiki 文章類型。
    """
    comments = []
    for pn in range(1, max_pages + 1):
        url = "https://api.bilibili.com/x/v2/reply"
        params = {
            "oid":  oid,
            "type": 17,     # wiki article
            "pn":   pn,
            "ps":   20,     # 每頁20條
            "sort": 0,
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = r.json()
            if data.get("code") != 0:
                print(f"  API 錯誤: {data.get('message')}")
                break

            replies = data.get("data", {}).get("replies") or []
            if not replies:
                break

            for reply in replies:
                member  = reply.get("member", {})
                content = reply.get("content", {})
                comments.append({
                    "oid":      oid,
                    "rpid":     reply.get("rpid"),
                    "uname":    member.get("uname", ""),
                    "content":  content.get("message", ""),
                    "like":     reply.get("like", 0),
                    "ctime":    reply.get("ctime", 0),
                    "rcount":   reply.get("rcount", 0),  # 子回覆數
                })

            print(f"  第{pn}頁: {len(replies)} 條評論")
            time.sleep(1.0)

        except Exception as e:
            print(f"  第{pn}頁抓取失敗: {e}")
            break

    return comments


# ══════════════════════════════════════════════
# Step 3: 情緒分析
# ══════════════════════════════════════════════

def analyze_sentiment(text: str) -> float:
    """
    用 SnowNLP 對評論做情緒分析。
    回傳 0~1 的情緒分數 (越大越正面)。
    """
    try:
        from snownlp import SnowNLP
        return SnowNLP(text).sentiments
    except Exception:
        return 0.5  # 無法分析時回傳中性


def classify_sentiment(score: float) -> str:
    """將情緒分數轉為 正/中/負 標籤。"""
    if score >= 0.75:
        return "正"
    elif score <= 0.40:
        return "負"
    else:
        return "中"


# ══════════════════════════════════════════════
# Step 4: 產生 PK 格式資料 (仿 pk_taipei_mayor_election.csv)
# ══════════════════════════════════════════════

def build_pk_data(df_comments: pd.DataFrame,
                  char_info: list[tuple]) -> dict:
    """
    從評論資料製作 PK 格式，
    格式與 pk_taipei_mayor_election.csv 相同。
    """
    import datetime

    list_pkNames          = []
    list_photos           = []
    list_colors           = []
    list_sentiInfo        = []
    list_total_comments   = []
    list_total_likes      = []
    list_freq_daily       = []

    # 顏色池
    color_pool = [
        "rgba(255,99,132,0.3)",
        "rgba(54,162,235,0.3)",
        "rgba(255,206,86,0.3)",
        "rgba(75,192,192,0.3)",
        "rgba(153,102,255,0.3)",
    ]

    for i, (char_id, char_name, detail_url) in enumerate(char_info):
        df_char = df_comments[df_comments["char_id"] == char_id]
        if df_char.empty:
            continue

        total_comments = len(df_char)
        total_likes    = int(df_char["like"].sum())

        # 情緒統計
        pos = int((df_char["sentiment_label"] == "正").sum())
        neu = int((df_char["sentiment_label"] == "中").sum())
        neg = int((df_char["sentiment_label"] == "負").sum())
        pos_pct = round(pos / total_comments * 100)
        neu_pct = round(neu / total_comments * 100)
        neg_pct = round(neg / total_comments * 100)

        # 每日評論數折線圖資料
        df_char = df_char.copy()
        df_char["date"] = pd.to_datetime(df_char["ctime"], unit="s").dt.strftime("%Y-%m-%d")
        daily = df_char.groupby("date").size().reset_index(name="y")
        line_data = [{"x": row["date"], "y": int(row["y"])} for _, row in daily.iterrows()]

        # 照片 URL (從 uma_characters_bilingual.csv 取)
        photo_url = ""
        bilingual_csv = DIR / "uma_characters_bilingual.csv"
        if bilingual_csv.exists():
            df_chars = pd.read_csv(bilingual_csv, dtype=str)
            row = df_chars[df_chars["char_id"] == char_id]
            if not row.empty:
                photo_url = row.iloc[0].get("icon_url", "")

        list_pkNames.append(char_name)
        list_photos.append(photo_url)
        list_colors.append(color_pool[i % len(color_pool)])
        list_sentiInfo.append([pos_pct, neu_pct, neg_pct])
        list_total_comments.append(total_comments)
        list_total_likes.append(total_likes)
        list_freq_daily.append(line_data)

    pk_data = {
        "list_pkNames":        list_pkNames,
        "list_photos":         list_photos,
        "list_colors":         list_colors,
        "list_sentiInfo":      list_sentiInfo,
        "list_total_comments": list_total_comments,
        "list_total_likes":    list_total_likes,
        "list_freq_daily":     list_freq_daily,
    }
    return pk_data


# ══════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════

def main():
    all_comments = []

    for char_id, char_name, detail_url in TARGET_CHARS:
        print(f"\n── {char_name} (char_id={char_id}) ──")

        # 1. 取 oid
        print("  取得 Bilibili oid...")
        oid = get_bilibili_oid(detail_url)
        if not oid:
            print(f"  跳過 {char_name}（找不到 oid）")
            continue
        print(f"  oid = {oid}")

        # 2. 取評論
        print("  抓取 Bilibili 評論...")
        comments = fetch_comments(oid, max_pages=5)
        print(f"  共取得 {len(comments)} 條評論")

        # 3. 加情緒分析
        for c in comments:
            c["char_id"]   = char_id
            c["char_name"] = char_name
            c["sentiment"] = analyze_sentiment(c["content"])
            c["sentiment_label"] = classify_sentiment(c["sentiment"])

        all_comments.extend(comments)
        time.sleep(2)

    if not all_comments:
        print("\n沒有取得任何評論，請確認 Selenium 與 oid 設定")
        return

    # 儲存原始評論
    df = pd.DataFrame(all_comments)
    df.to_csv(RAW_CSV, index=False, encoding="utf-8-sig")
    print(f"\n原始評論已儲存: {RAW_CSV} ({len(df)} 筆)")

    # 產生 PK 格式
    pk_data = build_pk_data(df, TARGET_CHARS)
    df_pk = pd.DataFrame(
        list(pk_data.items()),
        columns=["name", "value"]
    )
    df_pk.to_csv(PK_CSV, index=False, encoding="utf-8-sig")
    print(f"PK 格式已儲存: {PK_CSV}")

    # 印出情緒統計
    print("\n=== 角色評論情緒統計 ===")
    summary = (
        df.groupby("char_name")["sentiment_label"]
        .value_counts()
        .unstack(fill_value=0)
        .assign(total=lambda x: x.sum(axis=1))
    )
    print(summary)


if __name__ == "__main__":
    main()
