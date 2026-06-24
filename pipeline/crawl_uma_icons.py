"""
賽馬娘角色圖示 URL 提取與下載
============================================================
原因:
  patchwiki.biligame.com 的圖片用「內容 Hash」命名，
  無法從檔名預測，必須從渲染後的 HTML 取得實際 URL。

  已確認的 URL 格式:
  https://patchwiki.biligame.com/images/umamusume/
    thumb/{a}/{ab}/{content_hash}.png/{size}px-{original_filename}.png

  例:
  Chr_icon_1001_100101_01.png (特別週【特別夢想家】) →
  thumb/3/38/48av6cwfvk6b2c3anpnxlh29410sel3.png/150px-Chr_icon_1001_100101_01.png

方式:
  用 Playwright 載入繁中赛马娘一览頁面，
  找所有 img 標籤 src 含 Chr_icon 的 → 提取 URL + 解析 char_id/skin_id

輸出:
  uma_icon_urls.csv     → char_id, skin_id, thumb_url, full_url
  images/               → 下載的角色圖示 PNG

執行:
  pip install playwright && python -m playwright install chromium
  python crawl_uma_icons.py
============================================================
"""

import re
import os
import time
import requests
import pandas as pd
from pathlib import Path

DIR      = Path(__file__).parent
OUT_CSV  = DIR / "uma_icon_urls.csv"
IMG_DIR  = DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

TRAD_URL = "https://wiki.biligame.com/umamusume/%E7%B9%81%E4%B8%AD%E8%B5%9B%E9%A9%AC%E5%A8%98%E4%B8%80%E8%A7%88"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ── 已知的手動對照表（不夠用 Selenium 補齊）──────────────────
# 格式: "char_id_skin_id": "hash"
KNOWN_HASHES = {
    "1001_100101": "48av6cwfvk6b2c3anpnxlh29410sel3",  # 特別週【特別夢想家】
}


# ══════════════════════════════════════════════
# 方式 1: Playwright 從渲染 HTML 提取
# ══════════════════════════════════════════════

def extract_icon_urls_playwright(url: str = TRAD_URL) -> list[dict]:
    """
    用 Playwright 載入角色一覽頁面，提取所有 Chr_icon 圖示 URL。
    """
    from playwright.sync_api import sync_playwright

    print(f"[Playwright] 載入: {url}")
    results = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1920, "height": 4000},
        )
        page = ctx.new_page()
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  [goto 警告] {e}")

        print("  等待頁面渲染 (8 秒)...")
        time.sleep(8)

        # 捲動觸發懶加載
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
        except Exception:
            pass

        imgs = page.query_selector_all("img")
        print(f"  頁面共 {len(imgs)} 個 img 標籤")

        for img in imgs:
            src = img.get_attribute("src") or ""
            alt = img.get_attribute("alt") or ""

            is_chr_src = "Chr_icon" in src or "chr_icon" in src.lower()
            is_chr_alt = re.search(r"Chr.icon", alt, re.I)

            if not (is_chr_src or is_chr_alt):
                continue

            m_src = re.search(
                r"thumb/([a-f0-9])/([a-f0-9]{2})/([a-z0-9]+)\.png/(\d+)px-(Chr_icon_(\d+)_(\d+)_\d+\.png)",
                src, re.I
            )
            if m_src:
                a, ab, content_hash, size, fname, char_id, skin_id = m_src.groups()
                key = (char_id, skin_id)
                if key in seen:
                    continue
                seen.add(key)

                full_url  = f"https://patchwiki.biligame.com/images/umamusume/{a}/{ab}/{content_hash}.png"
                thumb_url = f"https://patchwiki.biligame.com/images/umamusume/thumb/{a}/{ab}/{content_hash}.png/{size}px-{fname}"

                results.append({
                    "char_id":    char_id,
                    "skin_id":    skin_id,
                    "fname":      fname,
                    "hash":       content_hash,
                    "thumb_url":  thumb_url,
                    "full_url":   full_url,
                })

        browser.close()

    print(f"  提取到 {len(results)} 個 Chr_icon URL")
    return results


# ══════════════════════════════════════════════
# 方式 2: 從已知 Hash 建立部分對照表
# ══════════════════════════════════════════════

def build_from_known_hashes() -> list[dict]:
    """
    用已知的 content hash 建立對照記錄。

    路徑規則 (已驗證):
      path = MD5("Chr icon {char_id} {skin_id} 01.png")  ← 注意: 空格非底線
      → {path[0]}/{path[:2]}/{content_hash}.png
    """
    import hashlib

    results = []
    for key, content_hash in KNOWN_HASHES.items():
        parts = key.split("_")
        char_id, skin_id = parts[0], parts[1]

        # 原始檔名 (含空格，MediaWiki wiki 格式)
        fname_spaces = f"Chr icon {char_id} {skin_id} 01.png"
        fname_under  = f"Chr_icon_{char_id}_{skin_id}_01.png"

        # 路徑來自 MD5(原始檔名含空格)
        path_md5 = hashlib.md5(fname_spaces.encode()).hexdigest()
        a, ab = path_md5[0], path_md5[:2]

        full_url  = f"https://patchwiki.biligame.com/images/umamusume/{a}/{ab}/{content_hash}.png"
        thumb_url = f"https://patchwiki.biligame.com/images/umamusume/thumb/{a}/{ab}/{content_hash}.png/150px-{fname_under}"

        results.append({
            "char_id":   char_id,
            "skin_id":   skin_id,
            "fname":     fname_under,
            "hash":      content_hash,
            "path":      f"{a}/{ab}",
            "thumb_url": thumb_url,
            "full_url":  full_url,
        })
    return results


# ══════════════════════════════════════════════
# 下載圖片
# ══════════════════════════════════════════════

def download_icons(records: list[dict], use_thumb: bool = True) -> list[dict]:
    """
    批量下載圖示，回傳補充了 local_path 的記錄列表。
    use_thumb=True 下載縮圖（較小），False 下載原圖。
    """
    updated = []
    for r in records:
        url = r["thumb_url"] if use_thumb else r["full_url"]
        fname = f"chr_{r['char_id']}_{r['skin_id']}.png"
        save_path = IMG_DIR / fname

        if save_path.exists():
            r["local_path"] = str(save_path.relative_to(DIR))
            updated.append(r)
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 200:
                save_path.write_bytes(resp.content)
                r["local_path"] = str(save_path.relative_to(DIR))
                print(f"  ✓ char={r['char_id']} skin={r['skin_id']} ({len(resp.content):,} bytes)")
            else:
                r["local_path"] = ""
                print(f"  ✗ char={r['char_id']} skin={r['skin_id']} HTTP {resp.status_code}")
        except Exception as e:
            r["local_path"] = ""
            print(f"  ✗ char={r['char_id']} skin={r['skin_id']} 錯誤: {e}")

        time.sleep(0.3)
        updated.append(r)

    return updated


# ══════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════

def main():
    records = []

    # 嘗試 Playwright 提取全部
    print("=== 方式1: Playwright 提取 ===")
    records = extract_icon_urls_playwright()

    # 若 Selenium 未取得，用已知 Hash 作為起點
    if not records:
        print("\n=== 方式2: 使用已知 Hash ===")
        records = build_from_known_hashes()
        print(f"已知 {len(records)} 筆（可在 KNOWN_HASHES 中手動補充）")

    if not records:
        print("沒有取得任何 URL")
        return

    # 儲存 URL 對照表
    df = pd.DataFrame(records)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[儲存] URL 對照表 → {OUT_CSV} ({len(df)} 筆)")

    # 下載圖片
    print(f"\n=== 下載圖示 → {IMG_DIR} ===")
    records = download_icons(records, use_thumb=True)

    ok = sum(1 for r in records if r.get("local_path"))
    print(f"\n下載完成: {ok}/{len(records)} 成功")

    # 更新 CSV
    df = pd.DataFrame(records)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(df[["char_id", "skin_id", "local_path"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
