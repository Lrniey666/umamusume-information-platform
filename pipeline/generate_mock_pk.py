"""
generate_mock_pk.py
────────────────────────────────────────────────────────────────────
從 uma_characters_bilingual.csv 讀取所有角色的真實頭像 URL，
配合隨機生成的 mock 評論/聲量資料，
產出 pk_uma_characters.csv，供 app_character_pk 顯示。

用途：在 T1b 評論爬蟲尚未執行/完成前，讓 UI 先顯示完整角色列表。
實際執行 T1b 後，pk_uma_characters.csv 會被覆蓋成真實資料。
"""

import pandas as pd
import random
import datetime
from pathlib import Path

DIR  = Path(__file__).parent
OUT  = DIR / "pk_uma_characters.csv"

random.seed(42)

COLOR_POOL = [
    "rgba(255,99,132,0.4)",  "rgba(54,162,235,0.4)",  "rgba(255,206,86,0.4)",
    "rgba(75,192,192,0.4)",  "rgba(153,102,255,0.4)", "rgba(255,159,64,0.4)",
    "rgba(231,76,60,0.4)",   "rgba(52,152,219,0.4)",  "rgba(46,204,113,0.4)",
    "rgba(155,89,182,0.4)",  "rgba(241,196,15,0.4)",  "rgba(26,188,156,0.4)",
]


def load_chars() -> list[dict]:
    df = pd.read_csv(DIR / "uma_characters_bilingual.csv", dtype=str)
    seen, result = set(), []
    for _, row in df.iterrows():
        cid = str(row.get("char_id", "")).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        result.append({
            "char_id":   cid,
            "name_trad": str(row.get("name_trad", "")).strip(),
            "icon_url":  str(row.get("icon_url", "")).strip(),
        })
    return result


def gen_senti():
    """隨機產生正/中/負比例（三數合計 100）"""
    pos = random.randint(55, 85)
    neg = random.randint(3, 20)
    neu = 100 - pos - neg
    return [pos, neu, neg]


def gen_freq_daily(n_comments: int) -> list[dict]:
    """
    產生過去 12 個月的月評論量，總和約等於 n_comments。
    """
    today = datetime.date.today()
    data  = []
    remaining = n_comments
    for m in range(11, -1, -1):
        d = (today.replace(day=1) - datetime.timedelta(days=30 * m))
        d = d.replace(day=1)
        share = random.randint(
            max(1, remaining // 14),
            max(2, remaining // 6),
        )
        share = min(share, remaining)
        data.append({"x": d.strftime("%Y-%m-%d"), "y": share})
        remaining -= share
        if remaining <= 0:
            break
    return data


def main():
    chars = load_chars()
    print(f"共 {len(chars)} 個角色")

    list_pkNames        = [c["name_trad"] for c in chars]
    list_photos         = [c["icon_url"]  for c in chars]
    list_colors         = [COLOR_POOL[i % len(COLOR_POOL)] for i in range(len(chars))]
    list_sentiInfo      = [gen_senti()                      for _ in chars]
    list_total_comments = [random.randint(20, 300)          for _ in chars]
    list_total_likes    = [c * random.randint(2, 6)         for c in list_total_comments]
    list_freq_daily     = [gen_freq_daily(c)                for c in list_total_comments]

    rows = [
        ("list_pkNames",        str(list_pkNames)),
        ("list_photos",         str(list_photos)),
        ("list_colors",         str(list_colors)),
        ("list_sentiInfo",      str(list_sentiInfo)),
        ("list_total_comments", str(list_total_comments)),
        ("list_total_likes",    str(list_total_likes)),
        ("list_freq_daily",     str(list_freq_daily)),
    ]
    df_out = pd.DataFrame(rows, columns=["name", "value"])
    df_out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"已儲存: {OUT}")
    print(f"角色數: {len(list_pkNames)}")
    print(f"前10名: {list_pkNames[:10]}")


if __name__ == "__main__":
    main()
