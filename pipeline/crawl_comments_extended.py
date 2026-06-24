"""
T1b: 擴充版賽馬娘評論爬蟲
──────────────────────────────────────────────────────────────────
輸入:  uma_characters_bilingual.csv (所有角色)
輸出:
  uma_comments_raw.csv        → 原始評論 + SnowNLP 情緒分數
  pk_uma_characters.csv       → PK 站格式（覆蓋 mock 資料）
  uma_comments_as_news.csv    → 評論轉換為新聞文章格式
                                 (供 T2/T3 pipeline 合併使用)

說明:
  - 用 Playwright 從每個角色的 BWIKI 頁面取 Bilibili oid
  - 用 Bilibili Reply API 爬取多頁評論
  - 用 SnowNLP 做情緒分析
  - 每個評論會被轉換成一筆「新聞文章」(category = 角色繁體名)
"""

import re
import os
import time
import json
import requests
import pandas as pd
from pathlib import Path
from collections import defaultdict

DIR         = Path(__file__).parent
RAW_CSV     = DIR / "uma_comments_raw.csv"
PK_CSV      = DIR / "pk_uma_characters.csv"
NEWS_CSV    = DIR / "uma_comments_as_news.csv"
CHARS_CSV   = DIR / "uma_characters_bilingual.csv"

MAX_PAGES_PER_CHAR = 10    # 每角色最多爬取頁數，每頁 20 條
SLEEP_BETWEEN_CHARS = 2.0  # 角色之間等待秒數

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/",
}

color_pool = [
    "rgba(255,99,132,0.3)", "rgba(54,162,235,0.3)",  "rgba(255,206,86,0.3)",
    "rgba(75,192,192,0.3)", "rgba(153,102,255,0.3)", "rgba(255,159,64,0.3)",
    "rgba(231,76,60,0.3)",  "rgba(52,152,219,0.3)",  "rgba(46,204,113,0.3)",
    "rgba(155,89,182,0.3)",
]


# ══════════════════════════════════════════════
# 讀取目標角色 (從 CSV，每個 char_id 只取一筆)
# ══════════════════════════════════════════════

def load_target_chars() -> list[tuple]:
    """
    回傳 [(char_id, name_simp, name_trad, detail_url, icon_url), ...]
    每個 char_id 只取第一筆 (避免同一角色多個皮膚重複爬取)
    """
    if not CHARS_CSV.exists():
        print(f"找不到 {CHARS_CSV}，使用預設 5 角色")
        return [
            ("1001", "特别周",   "特別週",   "https://wiki.biligame.com/umamusume/%E7%AE%80/%E3%80%90%E7%89%B9%E5%88%AB%E8%BF%BD%E6%A2%A6%E8%80%85%E3%80%91%E7%89%B9%E5%88%AB%E5%91%A8", ""),
            ("1002", "无声铃鹿", "無聲鈴鹿", "https://wiki.biligame.com/umamusume/%E7%AE%80/%E3%80%90%E6%97%A0%E5%A3%B0%E6%97%A0%E7%91%95%E3%80%91%E6%97%A0%E5%A3%B0%E9%93%83%E9%B9%BF", ""),
        ]

    df = pd.read_csv(CHARS_CSV, dtype=str)
    seen, result = set(), []
    for _, row in df.iterrows():
        cid = str(row.get("char_id", "")).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        result.append((
            cid,
            str(row.get("name_simp", "")).strip(),
            str(row.get("name_trad", "")).strip(),
            str(row.get("detail_url", "")).strip(),
            str(row.get("icon_url", "")).strip(),
        ))
    print(f"載入 {len(result)} 個角色（已去重）")
    return result


# ══════════════════════════════════════════════
# Step 1: 用 Playwright 取得角色頁面的 Bilibili oid
# ══════════════════════════════════════════════

def get_bilibili_oid(detail_url: str, char_name: str = "") -> str:
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx  = browser.new_context(user_agent=HEADERS["User-Agent"])
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

        for pat in [
            r'data-oid=["\'](\d+)["\']',
            r'"oid"\s*:\s*"?(\d+)"?',
            r'oid=(\d+)',
            r'"wgArticleId"\s*:\s*(\d+)',
        ]:
            m = re.search(pat, page_src)
            if m:
                oid = m.group(1)
                print(f"  oid={oid} (pattern: {pat[:30]})")
                return oid

        print(f"  [警告] 找不到 oid（{char_name}），頁面可能未載入評論組件")
        return ""
    except Exception as e:
        print(f"  Playwright 取 oid 失敗: {e}")
        return ""


# ══════════════════════════════════════════════
# Step 2: 用 Bilibili API 取得評論
# ══════════════════════════════════════════════

def fetch_comments(oid: str, max_pages: int = 10) -> list[dict]:
    comments = []
    for pn in range(1, max_pages + 1):
        try:
            r = requests.get(
                "https://api.bilibili.com/x/v2/reply",
                params={"oid": oid, "type": 17, "pn": pn, "ps": 20, "sort": 0},
                headers=HEADERS, timeout=10
            )
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
                    "rcount":   reply.get("rcount", 0),
                })
            print(f"  第{pn}頁: {len(replies)} 條評論（累計 {len(comments)} 條）")
            time.sleep(1.0)
        except Exception as e:
            print(f"  第{pn}頁抓取失敗: {e}")
            break
    return comments


# ══════════════════════════════════════════════
# Step 3: 情緒分析 (SnowNLP)
# ══════════════════════════════════════════════

def analyze_sentiment(text: str) -> float:
    try:
        from snownlp import SnowNLP
        return SnowNLP(str(text)[:200]).sentiments
    except Exception:
        return 0.5


def classify_sentiment(score: float) -> str:
    if score >= 0.75:
        return "正"
    elif score <= 0.40:
        return "負"
    return "中"


# ══════════════════════════════════════════════
# Step 4: 評論轉換為新聞文章格式
# ══════════════════════════════════════════════

def comments_to_news(df_comments: pd.DataFrame) -> pd.DataFrame:
    """
    把每條評論轉換成一筆「新聞文章」資料列，
    供 app_user_keyword / app_user_keyword_sentiment 的 CSV pipeline 使用。
    """
    import jieba
    import jieba.posseg as pseg
    from collections import Counter
    from opencc import OpenCC
    cc = OpenCC('s2t')
    jieba.setLogLevel('ERROR')

    STOP_WORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
        '一', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
        '没有', '看', '好', '自己', '这', '那', '等', '从', '将', '为',
        '以', '对', '由', '可以', '并', '其', '而', '如', '来', '它',
        '他', '她', '啊', '哦', '嗯', '吧', '呢', '啦', '喔',
    }
    KEEP_POS = {'n', 'nr', 'ns', 'nt', 'nz', 'ng', 'vn', 'an'}

    def tokenize(text):
        words_pos = list(pseg.cut(str(text)))
        tokens_filtered = [
            w.word for w in words_pos
            if len(w.word) >= 2 and w.word not in STOP_WORDS
            and (w.flag[:1] == 'n' or w.flag in ('vn', 'an'))
        ]
        freq = Counter(tokens_filtered)
        return tokens_filtered, [(w.word, w.flag) for w in words_pos], freq.most_common(10)

    rows = []
    for i, row in df_comments.iterrows():
        raw_content = str(row.get("content", "")).strip()
        if not raw_content or len(raw_content) < 3:
            continue
        content_tc  = cc.convert(raw_content)
        char_trad   = str(row.get("char_name_trad", row.get("char_name", "其他"))).strip()
        ctime       = int(row.get("ctime", 0))
        try:
            import datetime
            date_str = datetime.datetime.fromtimestamp(ctime).strftime("%Y-%m-%d")
        except Exception:
            date_str = "2024-01-01"
        title       = content_tc[:30] + ("…" if len(content_tc) > 30 else "")
        tokens_f, token_pos, top_kf = tokenize(content_tc)

        rows.append({
            "item_id":         f"comment_{row.get('rpid', i)}",
            "date":            date_str,
            "category":        char_trad,
            "title":           title,
            "content":         content_tc,
            "link":            "",
            "photo_link":      "",
            "tokens":          str(tokens_f),
            "tokens_filtered": str(tokens_f),
            "token_pos":       str(token_pos),
            "top_key_freq":    str(top_kf),
            "tokens_v2":       str(tokens_f),
            "sentiment":       round(float(row.get("sentiment", 0.5)), 4),
            "summary":         content_tc[:10],
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════
# Step 5: 產生 PK 格式
# ══════════════════════════════════════════════

def build_pk_data(df_comments: pd.DataFrame,
                  target_chars: list[tuple]) -> dict:
    import datetime

    list_pkNames          = []
    list_photos           = []
    list_colors           = []
    list_sentiInfo        = []
    list_total_comments   = []
    list_total_likes      = []
    list_freq_daily       = []

    for ci, (char_id, name_simp, name_trad, detail_url, icon_url) in enumerate(target_chars):
        df_char = df_comments[df_comments["char_id"] == char_id]
        if df_char.empty:
            continue

        total_comments = len(df_char)
        total_likes    = int(df_char["like"].sum())

        pos = int((df_char["sentiment_label"] == "正").sum())
        neu = int((df_char["sentiment_label"] == "中").sum())
        neg = int((df_char["sentiment_label"] == "負").sum())
        pos_pct = round(pos / total_comments * 100) if total_comments else 0
        neu_pct = round(neu / total_comments * 100) if total_comments else 0
        neg_pct = round(neg / total_comments * 100) if total_comments else 0

        df_char = df_char.copy()
        df_char["date"] = pd.to_datetime(df_char["ctime"], unit="s").dt.strftime("%Y-%m-%d")
        daily    = df_char.groupby("date").size().reset_index(name="y")
        line_data = [{"x": r["date"], "y": int(r["y"])} for _, r in daily.iterrows()]

        list_pkNames.append(name_trad)
        list_photos.append(icon_url)
        list_colors.append(color_pool[ci % len(color_pool)])
        list_sentiInfo.append([pos_pct, neu_pct, neg_pct])
        list_total_comments.append(total_comments)
        list_total_likes.append(total_likes)
        list_freq_daily.append(line_data)

    return {
        "list_pkNames":        list_pkNames,
        "list_photos":         list_photos,
        "list_colors":         list_colors,
        "list_sentiInfo":      list_sentiInfo,
        "list_total_comments": list_total_comments,
        "list_total_likes":    list_total_likes,
        "list_freq_daily":     list_freq_daily,
    }


# ══════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════

def main():
    target_chars = load_target_chars()
    all_comments = []

    for char_id, name_simp, name_trad, detail_url, icon_url in target_chars:
        print(f"\n── {name_trad} / {name_simp} (id={char_id}) ──")
        if not detail_url or detail_url == "nan":
            print(f"  跳過（無 detail_url）")
            continue

        print("  取得 Bilibili oid (Playwright)...")
        oid = get_bilibili_oid(detail_url, name_trad)
        if not oid:
            print(f"  跳過 {name_trad}（找不到 oid）")
            continue

        print(f"  oid={oid}  抓取最多 {MAX_PAGES_PER_CHAR} 頁評論...")
        comments = fetch_comments(oid, max_pages=MAX_PAGES_PER_CHAR)
        print(f"  共取得 {len(comments)} 條評論")

        for c in comments:
            c["char_id"]         = char_id
            c["char_name"]       = name_simp
            c["char_name_trad"]  = name_trad
            c["sentiment"]       = analyze_sentiment(c["content"])
            c["sentiment_label"] = classify_sentiment(c["sentiment"])

        all_comments.extend(comments)
        time.sleep(SLEEP_BETWEEN_CHARS)

    if not all_comments:
        print("\n沒有取得任何評論，終止")
        return

    # 1. 儲存原始評論
    df = pd.DataFrame(all_comments)
    df.to_csv(RAW_CSV, index=False, encoding="utf-8-sig")
    print(f"\n原始評論已儲存: {RAW_CSV}  ({len(df)} 筆)")

    # 2. 儲存 PK 格式
    pk_data = build_pk_data(df, target_chars)
    df_pk = pd.DataFrame(list(pk_data.items()), columns=["name", "value"])
    df_pk.to_csv(PK_CSV, index=False, encoding="utf-8-sig")
    print(f"PK 格式已儲存:   {PK_CSV}")

    # 3. 評論轉新聞格式
    print("\n評論轉換為新聞格式（jieba + SnowNLP）中...")
    df_news = comments_to_news(df)
    df_news.to_csv(NEWS_CSV, sep="|", index=False)
    print(f"新聞格式已儲存:  {NEWS_CSV}  ({len(df_news)} 筆)")

    # 驗收
    print("\n=== 驗收 ===")
    print(f"原始評論:   {len(df)} 筆")
    print(f"新聞格式:   {len(df_news)} 筆")
    print("各角色評論數:")
    print(df.groupby("char_name_trad")["rpid"].count().to_string())
    print("\n角色 PK 站情緒摘要:")
    for i, name in enumerate(pk_data["list_pkNames"]):
        s = pk_data["list_sentiInfo"][i]
        c = pk_data["list_total_comments"][i]
        print(f"  {name}: {c} 條  正{s[0]}% 中{s[1]}% 負{s[2]}%")


if __name__ == "__main__":
    main()
