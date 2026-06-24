"""
賽馬娘角色資料集爬蟲
============================================================
目標頁面: https://wiki.biligame.com/umamusume/简中赛马娘一览

由於 Bilibili Wiki 使用 Tencent EdgeOne WAF (HTTP 567)，
標準 requests 無法直接存取。提供兩種方案：

方案 A (推薦): 解析已下載的 Markdown 檔案
  → 不需要任何額外套件，直接執行

方案 B: 使用 Selenium 自動化瀏覽器繞過 WAF
  → 需安裝: pip install selenium
  → 需安裝 ChromeDriver 或 GeckoDriver

輸出: uma_characters.csv
欄位: name, skins, photo_url, char_id, skin_id
============================================================
"""

import re
import os
import time
import pandas as pd
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(DIR, "uma_characters.csv")

# 方案 A 用的已下載 Markdown 路徑（若有的話）
DOWNLOADED_MD = "/root/.cursor/projects/workspaces-8-10-emi/uploads/_______-0.md"

# Bilibili Wiki 目標 URL
TARGET_URL = "https://wiki.biligame.com/umamusume/%E7%AE%80%E4%B8%AD%E8%B5%9B%E9%A9%AC%E5%A8%98%E4%B8%80%E8%A7%88"


# ══════════════════════════════════════════════
# 方案 A：解析已下載的 Markdown 檔
# ══════════════════════════════════════════════

def parse_from_markdown(md_path: str) -> list[dict]:
    """
    從已下載的 Markdown 中解析角色資料。
    頁面結構：
      Chr icon {char_id} {skin_id} 01.png
      【皮膚名稱】角色名稱
      **角色名稱**
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析每一個角色皮膚區塊
    # 格式: Chr icon XXXX XXXXXX 01.png\n\n【皮膚名】角色名\n\n**角色名**
    pattern = re.compile(
        r'(Chr icon (\d+) (\d+) \d+\.png)\s*\n+'   # icon 檔名 + char_id + skin_id
        r'【(.+?)】(.+?)\s*\n+'                       # 【皮膚名】角色名
        r'\*\*(.+?)\*\*',                             # **角色名**（正式名）
        re.DOTALL
    )

    entries = []
    for m in pattern.finditer(content):
        icon_file = m.group(1)
        char_id   = m.group(2)
        skin_id   = m.group(3)
        skin_name = m.group(4).strip()
        char_name = m.group(6).strip()

        entries.append({
            "name":      char_name,
            "skin_name": skin_name,
            "char_id":   char_id,
            "skin_id":   skin_id,
            "icon_file": icon_file,
            "photo_url": build_photo_url(icon_file),
        })

    return entries


def build_photo_url(icon_filename: str) -> str:
    """
    MediaWiki 圖片 URL 規則:
    URL = /images/{wiki}/{md5[0]}/{md5[:2]}/{filename}
    注意: spaces → underscores, 首字母大寫
    """
    import hashlib
    # MediaWiki 規則：空格改底線，首字母大寫
    fname = icon_filename.replace(" ", "_")
    fname = fname[0].upper() + fname[1:]
    md5 = hashlib.md5(fname.encode("utf-8")).hexdigest()
    a, ab = md5[0], md5[:2]
    return f"https://patchwiki.biligame.com/images/umamusume/{a}/{ab}/{fname}"


def aggregate_characters(entries: list[dict]) -> list[dict]:
    """
    將同一角色的多個皮膚合併為一筆，
    並以第一個皮膚的 photo_url 作為代表圖片。
    """
    char_map: dict[str, dict] = {}
    for e in entries:
        name = e["name"]
        if name not in char_map:
            char_map[name] = {
                "name":      name,
                "char_id":   e["char_id"],
                "skins":     [],
                "photo_url": e["photo_url"],  # 第一個皮膚圖
            }
        char_map[name]["skins"].append(e["skin_name"])

    result = []
    for char in char_map.values():
        char["skins"] = "、".join(char["skins"])
        result.append(char)
    return result


# ══════════════════════════════════════════════
# 方案 B：Selenium 自動化爬蟲（繞過 WAF）
# ══════════════════════════════════════════════

def crawl_with_selenium() -> str:
    """
    使用 Selenium 開啟瀏覽器，抓取頁面 HTML 後解析。
    回傳頁面 HTML 字串。
    需要先安裝:
      pip install selenium
      以及 Chrome + chromedriver (版本需對應)
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("請先安裝 Selenium: pip install selenium")
        return ""

    print("啟動 Chrome 瀏覽器...")
    options = Options()
    options.add_argument("--headless")        # 無頭模式（不顯示視窗）
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(TARGET_URL)

        # 等待頁面載入（等待角色卡片出現）
        print("等待頁面載入...")
        time.sleep(5)

        # 等待包含角色內容的元素出現
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "mw-content-text"))
        )

        html = driver.page_source
        driver.quit()
        print(f"頁面載入成功，HTML 長度: {len(html)}")
        return html

    except Exception as e:
        print(f"Selenium 爬取失敗: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        return ""


def parse_from_html(html: str) -> list[dict]:
    """從 Selenium 取得的 HTML 解析角色資料。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", id="mw-content-text")
    if not content:
        print("找不到 mw-content-text")
        return []

    entries = []
    # 找所有角色圖示 img
    for img in content.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if "Chr_icon" not in alt and "Chr icon" not in alt:
            continue

        # 找圖示後的角色名稱文字
        parent = img.find_parent()
        text = parent.get_text(separator="\n").strip() if parent else ""

        # 嘗試從 alt 屬性解析 char_id, skin_id
        m = re.search(r'Chr.icon.(\d+).(\d+)', alt)
        char_id = m.group(1) if m else ""
        skin_id = m.group(2) if m else ""

        # 從附近文字找皮膚名和角色名
        skin_m = re.search(r'【(.+?)】(.+)', text)
        if skin_m:
            entries.append({
                "name":      skin_m.group(2).strip(),
                "skin_name": skin_m.group(1).strip(),
                "char_id":   char_id,
                "skin_id":   skin_id,
                "icon_file": alt,
                "photo_url": src,
            })

    return entries


# ══════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════

def main():
    entries = []

    # 優先使用已下載的 Markdown
    if os.path.exists(DOWNLOADED_MD):
        print(f"[方案A] 從已下載的 Markdown 解析: {DOWNLOADED_MD}")
        entries = parse_from_markdown(DOWNLOADED_MD)
        print(f"解析到 {len(entries)} 筆皮膚記錄")
    else:
        print("[方案A] 找不到已下載的 Markdown，改用方案B (Selenium)")
        html = crawl_with_selenium()
        if html:
            entries = parse_from_html(html)
        else:
            print("方案B 也失敗，終止")
            return

    if not entries:
        print("沒有解析到任何資料")
        return

    # 合併同一角色的多個皮膚
    characters = aggregate_characters(entries)
    print(f"\n共 {len(characters)} 位不重複角色:")
    for c in characters:
        skin_count = len(c["skins"].split("、"))
        print(f"  {c['name']} (char_id={c['char_id']}, 皮膚數={skin_count})")

    # 儲存 CSV
    df = pd.DataFrame(characters)
    # 新增對照欄位：供 bilibili_uma_raw.csv 的標題搜尋用
    df["name_keyword"] = df["name"]  # 可手動擴充別名

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n已儲存至: {OUT_CSV}")
    print(df[["name", "char_id", "skins"]].to_string())


if __name__ == "__main__":
    main()
