"""
補爬腳本：針對 bilibili_uma_raw.csv 中 content='找不到內文' 的列重新爬取
改用 div.mw-parser-output 直接取文字，不移除任何子標籤
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
import os

DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(DIR, "bilibili_uma_raw.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_content(soup):
    """依序嘗試多個選擇器取出文章內文"""
    # 策略 1: div.mw-parser-output（直接不過濾）
    po = soup.find("div", class_="mw-parser-output")
    if po:
        for tag in po.find_all(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = re.sub(r'[ \t]{2,}', ' ', po.get_text(separator='\n', strip=True))
        text = re.sub(r'\n{3,}', '\n\n', text)
        if len(text) > 30:
            return text

    # 策略 2: div#mw-content-text（整個區塊，不濾table）
    ct = soup.find("div", id="mw-content-text")
    if ct:
        for tag in ct.find_all(["script", "style"]):
            tag.decompose()
        text = re.sub(r'[ \t]{2,}', ' ', ct.get_text(separator='\n', strip=True))
        text = re.sub(r'\n{3,}', '\n\n', text)
        if len(text) > 30:
            return text

    # 策略 3: article 或 main tag
    for tag_name in ["article", "main"]:
        tag = soup.find(tag_name)
        if tag:
            text = tag.get_text(separator='\n', strip=True)
            if len(text) > 30:
                return text

    return ""


def extract_date(soup, content):
    """從 MediaWiki 頁面或內文取最後編輯日期"""
    # 方法 1: "此页面最后编辑于..."
    m = re.search(r'此页面最后编辑于(.+?)。', soup.get_text())
    if m:
        return m.group(1).strip()
    # 方法 2: 內文中的 YYYY.MM.DD 日期
    m2 = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', content)
    if m2:
        return f"{m2.group(1)}年{int(m2.group(2))}月{int(m2.group(3))}日"
    return ""


def main():
    df = pd.read_csv(CSV, sep="|")
    mask = df["content"] == "找不到內文"
    failed_idx = df[mask].index.tolist()
    print(f"需補爬: {len(failed_idx)} 筆")

    for i, idx in enumerate(failed_idx):
        row = df.loc[idx]
        url = str(row["link"])
        sleep_t = random.uniform(1.0, 2.0)
        print(f"[{i+1}/{len(failed_idx)}] {url[:80]} (等 {sleep_t:.1f}s)")
        time.sleep(sleep_t)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code}，跳過")
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            content = extract_content(soup)
            date_str = extract_date(soup, content)

            if content:
                df.at[idx, "content"] = content
                df.at[idx, "date"]    = date_str
                print(f"  ✓ content_len={len(content)}, date={repr(date_str)}")
            else:
                print(f"  ✗ 仍無法取得內文（頁面長度 {len(resp.text)}）")
        except Exception as e:
            print(f"  ✗ 錯誤: {e}")

    # 儲存
    df.to_csv(CSV, sep="|", index=False)
    still_fail = (df["content"] == "找不到內文").sum()
    ok_count = len(df) - still_fail
    print(f"\n補爬完成：有內文 {ok_count} 筆，仍失敗 {still_fail} 筆")
    print(f"已更新: {CSV}")


if __name__ == "__main__":
    main()
