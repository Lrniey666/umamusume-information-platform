"""
賽馬娘雙語角色資料集爬蟲 (MediaWiki Parse API)
============================================================
功能:
  1. 透過 MediaWiki Parse API 取得简中/繁中兩個角色一覽頁面 HTML
  2. 解析出 char_id / skin_id / 皮膚名 / 角色名 / 圖示 URL / 詳情 URL
  3. 合併繁简雙語，OpenCC 補齊缺漏
  4. 下載角色圖示到 ./images/ 資料夾
  5. 輸出 uma_characters_bilingual.csv

注意:
  MediaWiki API (api.php) 不受 WAF 封鎖，可直接以 requests 呼叫。

安裝需求:
  pip install requests beautifulsoup4 pandas opencc-python-reimplemented

使用:
  python crawl_uma_bilingual.py
============================================================
"""

import re
import time
import hashlib
import requests
import pandas as pd
from pathlib import Path
from urllib.parse import unquote

DIR     = Path(__file__).parent
OUT_CSV = DIR / "uma_characters_bilingual.csv"
IMG_DIR = DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/",
}

# MediaWiki 頁面標題
SIMP_PAGE = "简中赛马娘一览"
TRAD_PAGE = "繁中赛马娘一览"

API_URL = "https://wiki.biligame.com/umamusume/api.php"


# ══════════════════════════════════════════════
# Step 1: 透過 API 取得渲染後 HTML
# ══════════════════════════════════════════════

def fetch_parsed_html(page_title: str) -> str:
    """呼叫 MediaWiki Parse API，回傳完整渲染 HTML。"""
    print(f"  [API] 解析頁面: {page_title}")
    r = requests.get(
        API_URL,
        params={
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
            "formatversion": 2,
        },
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    html = r.json().get("parse", {}).get("text", "")
    print(f"  HTML 長度: {len(html):,} chars")
    return html


# ══════════════════════════════════════════════
# Step 2: 解析 HTML → 角色記錄
# ══════════════════════════════════════════════

def parse_list_page(html: str) -> list[dict]:
    """
    從角色一覽頁面 HTML 解析角色資料。
    回傳: [{"char_id", "skin_id", "skin_name", "char_name", "icon_url", "detail_url"}, ...]
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    entries = []
    seen = set()

    for img in soup.find_all("img", alt=re.compile(r"Chr.icon", re.I)):
        alt = img.get("alt", "")
        m = re.search(r"Chr.icon.(\d+).(\d+).(\d+)", alt)
        if not m:
            continue
        char_id, skin_id = m.group(1), m.group(2)
        key = (char_id, skin_id)
        if key in seen:
            continue
        seen.add(key)

        # 找父層 <a> 取 detail_url
        a_tag = img.find_parent("a")
        if not a_tag:
            for anc in img.parents:
                a_tag = anc.find("a", href=re.compile(r"/umamusume/"))
                if a_tag:
                    break

        detail_url = ""
        skin_name  = ""
        char_name  = ""

        if a_tag and a_tag.get("href"):
            href = a_tag["href"]
            detail_url = "https://wiki.biligame.com" + href if href.startswith("/") else href

            # 從 URL 最後一段解碼出 【皮膚名】角色名
            last_seg = unquote(href.split("/")[-1])
            tm = re.search(r"【(.+?)】(.+)", last_seg)
            if tm:
                skin_name = tm.group(1).strip()
                char_name = tm.group(2).strip()
            else:
                char_name = last_seg.strip()

        # 圖示 URL（從 src 取，含 content hash）
        src = img.get("src", "")
        if src.startswith("//"):
            src = "https:" + src
        if "/thumb/" in src:
            # 移除縮圖修飾 → 取原圖 URL
            icon_url = re.sub(r"/thumb/(.+?\.png)/.*", r"/\1", src)
        else:
            icon_url = src if src.startswith("http") else ""

        entries.append({
            "char_id":    char_id,
            "skin_id":    skin_id,
            "skin_name":  skin_name,
            "char_name":  char_name,
            "icon_url":   icon_url,
            "detail_url": detail_url,
        })

    print(f"  解析到 {len(entries)} 筆皮膚，{len(set(e['char_id'] for e in entries))} 位角色")
    return entries


# ══════════════════════════════════════════════
# Step 3: 合併 简中 + 繁中
# ══════════════════════════════════════════════

def merge_bilingual(simp_entries: list[dict],
                    trad_entries: list[dict]) -> list[dict]:
    """
    以 (char_id, skin_id) 為 key，合併简中與繁中名稱。
    優先採用爬取的簡/繁名，缺漏時以 OpenCC 互轉補足。
    """
    trad_map: dict[tuple, dict] = {
        (e["char_id"], e["skin_id"]): e for e in trad_entries
    }

    try:
        from opencc import OpenCC
        s2t = OpenCC("s2t")
        t2s = OpenCC("t2s")
        has_opencc = True
    except ImportError:
        has_opencc = False
        print("  [注意] opencc 未安裝，跳過自動轉換")

    rows = []
    # 以简中為主，補繁中
    for e in simp_entries:
        key  = (e["char_id"], e["skin_id"])
        trad = trad_map.get(key, {})

        name_trad = trad.get("char_name", "")
        skin_trad = trad.get("skin_name", "")
        if not name_trad and has_opencc:
            name_trad = s2t.convert(e["char_name"])
        if not skin_trad and has_opencc:
            skin_trad = s2t.convert(e["skin_name"])

        # 圖示優先用简中（通常兩邊一樣）
        icon_url   = e["icon_url"] or trad.get("icon_url", "")
        detail_url = e["detail_url"] or trad.get("detail_url", "")

        rows.append({
            "char_id":      e["char_id"],
            "skin_id":      e["skin_id"],
            "name_simp":    e["char_name"],
            "name_trad":    name_trad,
            "skin_simp":    e["skin_name"],
            "skin_trad":    skin_trad,
            "icon_url":     icon_url,
            "detail_url":   detail_url,
            "local_icon":   "",
        })

    # 繁中有但简中沒有的（新角色）
    simp_keys = {(e["char_id"], e["skin_id"]) for e in simp_entries}
    for e in trad_entries:
        key = (e["char_id"], e["skin_id"])
        if key in simp_keys:
            continue
        name_simp = t2s.convert(e["char_name"]) if has_opencc else ""
        skin_simp = t2s.convert(e["skin_name"]) if has_opencc else ""
        rows.append({
            "char_id":      e["char_id"],
            "skin_id":      e["skin_id"],
            "name_simp":    name_simp,
            "name_trad":    e["char_name"],
            "skin_simp":    skin_simp,
            "skin_trad":    e["skin_name"],
            "icon_url":     e["icon_url"],
            "detail_url":   e["detail_url"],
            "local_icon":   "",
        })

    return rows


# ══════════════════════════════════════════════
# Step 4: 下載角色圖示
# ══════════════════════════════════════════════

def download_image(url: str, save_path: Path) -> bool:
    """下載圖片到指定路徑，回傳是否成功。"""
    if save_path.exists():
        return True
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.content) > 500:
            save_path.write_bytes(r.content)
            return True
        return False
    except Exception:
        return False


# ══════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════

def main():
    # ── 1. 抓简中 ──────────────────────────────
    print("\n[Step 1] 简中赛马娘一览")
    simp_html    = fetch_parsed_html(SIMP_PAGE)
    simp_entries = parse_list_page(simp_html)

    # ── 2. 抓繁中 ──────────────────────────────
    print("\n[Step 2] 繁中赛马娘一览")
    trad_html    = fetch_parsed_html(TRAD_PAGE)
    trad_entries = parse_list_page(trad_html)

    # ── 3. 合併双語 ────────────────────────────
    print("\n[Step 3] 合併简/繁")
    rows = merge_bilingual(simp_entries, trad_entries)
    print(f"  合併後共 {len(rows)} 筆皮膚記錄")

    # ── 4. 下載圖示 ─────────────────────────────
    print(f"\n[Step 4] 下載角色圖示 → {IMG_DIR}")
    ok_count = 0
    for row in rows:
        if not row["icon_url"]:
            continue
        fname     = f"chr_{row['char_id']}_{row['skin_id']}.png"
        save_path = IMG_DIR / fname
        ok = download_image(row["icon_url"], save_path)
        if ok:
            row["local_icon"] = f"images/{fname}"
            ok_count += 1
            print(f"  ✓ {row['name_simp']} [{row['skin_simp']}]")
        else:
            print(f"  ✗ {row['name_simp']} [{row['skin_simp']}] ({row['icon_url'][:60]}...)")
        time.sleep(0.15)

    print(f"\n  圖示下載: {ok_count}/{len(rows)} 成功")

    # ── 5. 彙整成以「角色」為單位的資料集 ────────
    df_skins = pd.DataFrame(rows)
    char_df = (
        df_skins
        .groupby(["char_id", "name_simp", "name_trad"], as_index=False)
        .agg(
            skins_simp  = ("skin_simp",   lambda x: "、".join(x)),
            skins_trad  = ("skin_trad",   lambda x: "、".join(x)),
            icon_url    = ("icon_url",    "first"),
            local_icon  = ("local_icon",  "first"),
            detail_url  = ("detail_url",  "first"),
        )
    )
    char_df["name_keyword_simp"] = char_df["name_simp"]
    char_df["name_keyword_trad"] = char_df["name_trad"]

    char_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n已儲存 {len(char_df)} 位角色 → {OUT_CSV}")
    print(char_df[["char_id", "name_simp", "name_trad", "skins_simp"]].to_string(index=False))


if __name__ == "__main__":
    main()
