# 賽馬娘資訊平台 — 完整資料 Pipeline 執行指引（P6）

## 前置條件

1. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

2. **設定 API Key**（確認 `.env` 內有以下內容）
   ```
   GEMINI_API_KEY=你的_Gemini_API_Key
   DJANGO_SECRET_KEY=隨機長字串
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   ```

3. **建立必要目錄**
   ```bash
   mkdir -p data/raw data/processed
   ```

---

## 完整執行序列

### Step 1：爬取各來源原始資料

各爬蟲已修復（P1–P3），輸出至 `data/raw/`：

```bash
# Bilibili BWIKI 官方公告（約 5–10 分鐘）
python pipeline/crawl_bilibili_uma.py

# 巴哈姆特哈啦板（約 2–4 小時，依頁數而定）
python pipeline/crawl_bahamut_uma.py

# ETtoday 遊戲新聞（約 10–20 分鐘）
python pipeline/crawl_ettoday_uma.py

# 聯合新聞網遊戲角落（約 5–10 分鐘）
python pipeline/crawl_udn_uma.py

# 宅宅新聞（約 5–10 分鐘）
python pipeline/crawl_gamme_uma.py
```

> **提示**：各爬蟲均支援「斷點續爬」，中斷後重跑會自動跳過已爬文章。

### Step 2：合併前處理（斷詞 + 去重）

```bash
python pipeline/preprocess.py
```

輸出：`data/processed/uma_combined_tokenized.csv`

**預期各來源筆數：**

| 來源 | 預期筆數（下限）|
|---|---|
| bilibili | ≥ 150 筆 |
| bahamut  | ≥ 500 筆 |
| ettoday  | ≥ 200 筆 |
| udn      | ≥ 150 筆 |
| gamme    | ≥ 30 筆  |
| **合計** | **≥ 1,000 筆** |

### Step 3：Gemini 情感標記

```bash
# 標記全部來源（讀取 uma_combined_tokenized.csv）
python pipeline/label_sentiment.py

# 或指定單一來源
python pipeline/label_sentiment.py --source bilibili
python pipeline/label_sentiment.py --source bahamut
python pipeline/label_sentiment.py --source udn
python pipeline/label_sentiment.py --source gamme
```

> **API Quota 估算**：1,000 筆 × 0.8 秒延遲 ≈ 約 14 分鐘。
> Gemini Flash 免費額度每日 1,500 次，一般可一次完成。

輸出：`data/processed/uma_news_preprocessed.csv`

### Step 4：生成分析用 CSV

```bash
python scripts/generate_topkey_csv.py
python scripts/generate_top_character_csv.py
```

### Step 5：清空 DB 並重新匯入

```bash
python scripts/import_uma_data.py --clear
```

或僅追加新資料（不清空）：

```bash
python scripts/import_uma_data.py
```

### Step 6：驗收

```bash
# 確認 DB 筆數
python manage.py shell -c "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())"

# 確認各來源
python manage.py shell -c "
from app_user_keyword_db.models import NewsData
from django.db.models import Count
for item in NewsData.objects.values('source').annotate(n=Count('id')).order_by('-n'):
    print(item)
"

# 確認 API 來源統計
curl http://localhost:8000/api/source_stats/
```

---

## 快速驗收指標

| 驗收項 | 預期結果 |
|---|---|
| `NewsData.objects.count()` | ≥ 1,000 |
| `/api/source_stats/` 回傳來源數 | 5 個（bilibili/bahamut/ettoday/udn/gamme）|
| `/userkeyword/?source=udn` | 有結果（非空）|
| `/userkeyword/?source=gamme` | 有結果（非空）|
| `uma_news_preprocessed.csv` 含有的 source 值 | 5 種 |

---

## 常見問題

### Q：bahamut 爬蟲太慢

A：正常現象。巴哈姆特有 5,000+ 篇貼文，建議：
- 設定 `MAX_PAGES=50` 限制頁數（先試跑少量）
- 或使用管理指令：`python manage.py scrape_bahamut --crawl --pages 50`

### Q：Gemini API 呼叫失敗

A：確認 `.env` 的 `GEMINI_API_KEY` 已設定，且未超過每日 quota（1,500 次/日）。

### Q：`preprocess.py` 顯示某來源 0 筆

A：該來源的 raw CSV 尚未爬取或路徑不對。確認 `data/raw/` 下有對應的 `{source}_uma_raw.csv`。

### Q：Django management command 匯入巴哈資料

```bash
# 直接從 CSV 匯入（不執行爬蟲）
python manage.py scrape_bahamut

# 先爬後匯入
python manage.py scrape_bahamut --crawl --pages 50

# 限制匯入 1000 筆
python manage.py scrape_bahamut --limit 1000
```
