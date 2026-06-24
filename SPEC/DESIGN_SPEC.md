# 設計規格（Design Spec）

> 回答「怎麼做」。
> 涵蓋系統架構、資料模型、API 契約、邊界條件、錯誤處理策略。
>
> 最後更新：2026-06-23（依據 feature-completion-plan.html + admin-platform-plan.html 補全）

---

## 0. 版本矩陣（已查證 2026-06-22）

> ⚠️ **重要警告**：`gemini-2.0-flash` 已於 **2026 年 6 月 1 日停止服務**，請一律使用 `gemini-3.5-flash`。
> ⚠️ **重要警告**：`google-generativeai` 套件已正式**棄用**，請改用 `google-genai`。
> ⚠️ **重要警告**：`pipeline/label_sentiment.py` 原始版本有三個硬編碼錯誤須修復（見 § 16）。

| 類別 | 項目 | 採用版本 | 說明 |
|------|------|---------|------|
| **語言** | Python | **3.12** | 相容 Django 5.2 LTS + 所有主要套件 |
| **Web框架** | Django | **5.2.15 LTS** | LTS 至 2028/04，優於 6.0（非LTS，2026/08截止主流支援） |
| **Gemini SDK** | google-genai | **2.9.0** | 取代已棄用的 `google-generativeai` |
| **Gemini 模型** | gemini-3.5-flash | **gemini-3.5-flash** | 2026/05 GA；2.0-flash 已停服；3.1-flash-lite 為最新輕量選項 |
| **Gemini Embedding** | gemini-embedding-001 | **gemini-embedding-001** | 768維向量，RAG 首選 |
| **Claude SDK** | anthropic | **0.111.0** | 2026/06/18 最新版 |
| **Claude 模型** | claude-sonnet-4-6 | **claude-sonnet-4-6** | 量產首選 ($3/$15 per M tokens)；頂端選項已更新為 claude-opus-4-8（opus-4-1 已 deprecated 2026-06-05） |
| **排程** | APScheduler | **3.11.2** | 4.x 仍 alpha，使用穩定 3.x |
| **排程** | django-apscheduler | **0.7.0** | 2024/09，相容 Django 5.x |
| **向量庫** | faiss-cpu | **1.14.2** | 2026/05 最新 PyPI 穩定版 |
| **WSGI** | Gunicorn | **≥23.0** | 容器化部署用 |
| **反向代理** | Nginx | **1.26** stable | Alpine 映像 |
| **Docker** | Docker Engine | **27.x** | 搭配 Compose v2（`docker compose`） |
| **Docker 基礎映像** | python | **3.12-slim-bookworm** | 官方 slim，體積小 |
| **前端圖表** | Chart.js | **4.x** (CDN) | 注意 v4 API 與 v2 有差異 |
| **CSS 框架** | Bootstrap | **5.3** (CDN) | 官方維護中 |
| **Markdown 渲染** | Marked.js | **12.x** (CDN) | 用於 LLM 報告渲染 |
| **YouTube API** | YouTube Data API v3 | — | O5 已實作，每日 10,000 quota |
| **LangChain** | langchain | **≥1.3.0** | O2 已實作 |
| **LangGraph** | langgraph | **≥0.2.0** | O3 已實作 |
| **langchain-google-genai** | langchain-google-genai | **≥4.2.0** | O2/O3 Gemini 整合 |
| **Discord Bot SDK** | discord.py | **2.4.0** | D1-D8 已實作 |

---

## 1. 系統架構總覽

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Docker Compose 網路                            │
│                                                                      │
│  ┌─────────────┐    ┌────────────────────────────────────────────┐   │
│  │   Nginx     │    │          Django (Gunicorn)                  │   │
│  │  :80        │───►│                                            │   │
│  │  反向代理   │    │  app_character_pk         (首頁AI新聞+平台簡介 / popularity-list人氣列表)          │   │
│  │  靜態檔案   │    │  app_user_keyword         (聲量CSV)         │   │
│  └─────────────┘    │  app_user_keyword_association (關聯分析)   │   │
│                     │  app_user_keyword_sentiment   (情感CSV)    │   │
│  ┌─────────────┐    │  app_user_keyword_db      (ORM搜尋)        │   │
│  │  Browser    │◄──►│  app_user_keyword_llm_report (雙模型報告) │   │
│  │  Bootstrap  │    │  app_comment_sentiment    (留言情感排程)   │   │
│  │  Chart.js   │    │  app_uma_top_keyword      (熱門詞)         │   │
│  │  jQuery     │    │  app_uma_top_character    (熱門角色)       │   │
│  └─────────────┘    │  app_agent_uma            (Agentic AI)    │   │
│                     │  app_rag_uma              (RAG)            │   │
│                     │  app_poa_introduction     (介紹頁)         │   │
│                     │  app_correlation_analysis (相關性)        │   │
│                     │  app_crawler_admin        (情報站控制台)  │   │
│                     │  app_uma_news             (公告資料模型)   │   │
│                     │  app_uma_comments         (留言資料模型)   │   │
│                     │  app_dashboard            (公告儀表板)     │   │
│                     │  app_rag_agent            (Agentic RAG)   │   │
│                     │  app_agent_langchain      (LangChain)     │   │
│                     │  app_agent_langgraph      (LangGraph)     │   │
│                     │  app_course_intro         (課程介紹)      │   │
│                     │  app_youtube_uma          (YouTube 情感)  │   │
│                     │  app_discord_bot          (Discord Bot)   │   │
│                     │                                            │   │
│  外部 API           │  website_configs/ (settings/urls)        │   │
│  ┌─────────────┐    └────────────────┬───────────────────────────┘   │
│  │ Gemini API  │◄───────────────────►│                               │
│  │(google-genai│    ┌────────────────▼───────────────────────────┐   │
│  │ 2.9.0)      │    │       db.sqlite3 (Django ORM)               │   │
│  ├─────────────┤    │  NewsData   Article/Comment/ArticleEmotion  │   │
│  │ Claude API  │    │  YouTubeVideo/Comment  DiscordMessage        │   │
│  │(anthropic   │    │  DiscordBotConfig  DiscordNewsLog            │   │
│  │ 0.111.0)    │    └────────────────────────────────────────────┘   │
│  ├─────────────┤    FAISS Index (app_rag_uma/index/)                  │
│  │ YouTube API │    knowledge_base/（RAG + Agent 本地知識）            │
│  │(Data v3)    │                                                      │
│  └─────────────┘                                                      │
└──────────────────────────────────────────────────────────────────────┘

[離線 Pipeline — 部署前執行]
 data/raw/{source}_uma_raw.csv（5 來源統一格式）
   → preprocess.py → data/processed/uma_combined_tokenized.csv
     → label_sentiment.py → data/processed/uma_news_preprocessed.csv
       → scripts/import_uma_data.py → db.sqlite3 (NewsData)
       → scripts/generate_topkey_csv.py → uma_topkey_with_category.csv
       → scripts/generate_top_character_csv.py → uma_top_character_with_category.csv
```

### 技術選型表

| 層次 | 選型 | 版本 |
|------|------|------|
| Web 框架 | Django + Gunicorn | 5.2.15 LTS + ≥23.0 |
| 反向代理 | Nginx | 1.26 stable |
| 資料庫 | PostgreSQL（Docker 部署）／ SQLite（本機開發 fallback） | postgres:16-alpine + psycopg 3.x |
| Gemini LLM | google-genai | 2.9.0 |
| Claude LLM | anthropic | 0.111.0 |
| 向量搜尋 | faiss-cpu | 1.14.2 |
| 排程 | APScheduler 3.x + django-apscheduler | 3.11.2 + 0.7.0 |
| API 金鑰管理 | python-dotenv | ≥1.0 |
| 前端 CSS | Bootstrap 5.3 (CDN) | 5.3.x |
| 前端 JS | jQuery 3.7 + Chart.js 4.x + Marked.js (CDN) | 最新穩定 CDN |
| CORS | django-cors-headers | ≥4.x |
| 容器化 | Docker + Docker Compose v2 | Engine 27.x |

---

## 2. 專案目錄結構

```
umamusume-information-platform/
├── .env                              ← 金鑰（不入版控）
├── .env.example                      ← 金鑰範本（入版控）
├── manage.py
├── requirements.txt                  ← 所有套件版本釘牢
├── Dockerfile                        ← Django+Gunicorn 容器
├── docker-compose.yml                ← 多容器編排
├── feature-completion-plan.html      ← 功能補全計畫書（參考文件）
│
├── docker-files-poa/
│   ├── Dockerfile                    ← Django+Gunicorn 映像
│   └── entrypoint.sh                 ← 容器啟動初始化腳本（idempotent）
│
├── nginx/
│   └── nginx.conf                    ← 反向代理 + 靜態檔案
│
├── data/                             ← 統一資料目錄（P1–P6 修復後格式）
│   ├── raw/                          ← 各爬蟲原始輸出
│   │   ├── bilibili_uma_raw.csv
│   │   ├── bahamut_uma_raw.csv       ← 含 raw_category 欄位
│   │   ├── ettoday_uma_raw.csv
│   │   ├── udn_uma_raw.csv
│   │   └── gamme_uma_raw.csv
│   └── processed/                    ← 管線中間產物與最終輸出
│       ├── uma_combined_tokenized.csv  ← preprocess.py 輸出（多來源合併）
│       └── uma_news_preprocessed.csv   ← label_sentiment.py 輸出（情感標記完成）
│
├── pipeline/                         ← 離線資料爬蟲與前處理
│   ├── crawl_bilibili_uma.py         ← Bilibili BWIKI 公告爬蟲（P1 修復）
│   ├── crawl_bahamut_uma.py          ← 巴哈馬娘版爬蟲（P2 修復）
│   ├── crawl_ettoday_uma.py          ← ETtoday 新聞爬蟲（P3 修復）
│   ├── crawl_udn_uma.py              ← UDN 遊戲版爬蟲（P3 修復）
│   ├── crawl_gamme_uma.py            ← Gamme 遊戲媒體爬蟲（P3 修復）
│   ├── scrape_bahamut.py             ← APScheduler 呼叫的增量爬蟲（Article/Comment）
│   ├── preprocess.py                 ← 斷詞 / 去重 / 合併（P5 簡化）
│   └── label_sentiment.py            ← Gemini 批次情感標記（P4 修復）
│
├── scripts/                          ← 資料匯入與生成工具
│   ├── import_uma_data.py            ← uma_news_preprocessed.csv → db.sqlite3
│   ├── generate_topkey_csv.py        ← 生成 uma_topkey_with_category.csv
│   └── generate_top_character_csv.py ← 生成 uma_top_character_with_category.csv
│
├── knowledge_base/                   ← RAG + Agent 本地知識文件（H3 新增）
│   ├── uma_characters.md             ← 馬娘角色介紹
│   ├── uma_gacha.md                  ← 卡池機制說明
│   └── ...                           ← 可持續新增
│
├── website_configs/
│   ├── settings.py                   ← Django 設定
│   ├── urls.py                       ← 根路由
│   └── wsgi.py
│
├── templates/
│   └── base.html                     ← 全站基底（雙主題設計系統）
│
├── static/
│   └── css/, js/, img/               ← 靜態檔案（collectstatic 輸出）
│
├── app_character_pk/                 ← 首頁（AI新聞精選 + 平台簡介）+ /popularity-list/（人氣列表）
├── app_user_keyword/                 ← 關鍵字聲量分析（CSV）
├── app_user_keyword_association/     ← 全文關聯分析
├── app_user_keyword_sentiment/       ← 情感分析（CSV）
├── app_user_keyword_db/              ← ORM 全文搜尋
├── app_user_keyword_llm_report/      ← 雙模型 AI 分析報告（核心）
├── app_comment_sentiment/            ← 巴哈留言情感儀表板 + 排程（C1 補頁面）
├── app_uma_top_keyword/              ← 各類別熱門關鍵詞
├── app_uma_top_character/            ← 各類別熱門角色排行
├── app_agent_uma/                    ← Agentic AI 馬娘助理
│   ├── agent_core/
│   │   └── tools.py                  ← 6 種工具函數（含 read_local_document）
│   └── 第一階段說明.md
├── app_rag_uma/                      ← RAG 馬娘知識庫
│   ├── build_index.py                ← H1：預建 FAISS 索引腳本
│   └── index/
│       ├── uma_knowledge.faiss       ← 預建持久化索引
│       └── uma_knowledge_texts.pkl   ← chunk 文字 + metadata
├── app_poa_introduction/             ← 平台介紹頁
├── app_correlation_analysis/         ← 關鍵詞相關性分析
├── app_crawler_admin/                ← 情報站控制台（原爬蟲後台，含 YouTube/Discord/RAG 管理）
│   ├── views.py                      ← 控制台主視圖 + YouTube/Discord/RAG/Pipeline 子視圖
│   ├── urls.py
│   └── templates/app_crawler_admin/
│       ├── dashboard.html            ← 控制台首頁（Platform Health Dashboard）
│       ├── youtube.html              ← YouTube API 配額管理頁
│       ├── discord.html              ← Discord Bot 管理頁
│       ├── rag.html                  ← RAG 知識庫管理頁
│       └── pipeline.html             ← 爬蟲 Pipeline 一鍵執行頁
├── app_uma_news/                     ← 遊戲公告資料模型
├── app_uma_comments/                 ← 巴哈留言資料模型
├── app_dashboard/                    ← 公告列表儀表板
├── app_rag_agent/                    ← Agentic RAG（O1）
├── app_agent_langchain/              ← LangChain ReAct Agent（O2）
├── app_agent_langgraph/              ← LangGraph 狀態圖 Agent（O3）
│   └── graph_core/
│       ├── state.py                  ← AgentState
│       └── graph_agent.py            ← build_graph()
├── app_course_intro/                 ← 課程技術說明頁（O4）
├── app_youtube_uma/                  ← YouTube 影片情感儀表板（O5）
│   ├── models.py                     ← YouTubeVideo / YouTubeComment
│   ├── views.py
│   ├── urls.py
│   ├── jobs.py                       ← APScheduler 任務
│   └── management/commands/
│       └── crawl_youtube.py
└── app_discord_bot/                  ← Discord Bot 自動新聞推播（D1-D8）
    ├── models.py                     ← DiscordMessage / DiscordBotConfig / DiscordNewsLog
    ├── admin.py
    ├── crawler.py                    ← 頻道歷史增量爬取
    ├── classifier.py                 ← 雙層馬娘主題篩選
    ├── converter.py                  ← DiscordMessage → NewsData
    ├── news_generator.py             ← AI 新聞生成
    ├── scheduler.py                  ← APScheduler 5 個排程
    ├── views.py                      ← Bot 管理儀表板
    ├── urls.py
    └── management/commands/
        └── run_discord_bot.py        ← python manage.py run_discord_bot
```

---

## 3. 資料模型

### 3.1 Canonical Raw CSV 規格（P1–P3 修復後統一格式）

所有爬蟲輸出至 `data/raw/{source}_uma_raw.csv`，欄位順序統一如下：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `item_id` | str | 唯一識別碼（格式：`{source}_{唯一ID}`） |
| `source` | str | 資料來源（bilibili / bahamut / ettoday / udn / gamme） |
| `date` | str (YYYY-MM-DD) | 公告/文章日期（已在爬蟲端統一化） |
| `category` | str | 活動 / 卡池 / 競賽 / 系統 / 其他（已在爬蟲端轉繁體） |
| `title` | str | 標題（已在爬蟲端繁體化） |
| `content` | str | 全文內容（已在爬蟲端繁體化） |
| `link` | str | 原始頁面 URL |
| `photo_link` | str | 代表圖片 URL（可為空字串） |

**Bahamut 擴充欄位**（跟在標準欄位之後）：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `raw_category` | str | 原始論壇標籤（討論/情報/閒聊/問題等），保留供分析 |
| `author` | str | 作者帳號 |
| `gp` | int | 按讚數 |
| `reply_count` | int | 回覆數 |
| `view_count` | int | 瀏覽數 |

### 3.2 CSV：`data/processed/uma_news_preprocessed.csv`（聲量 / 情感 / DB 共用）

管線符號（`|`）分隔，UTF-8 BOM：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `item_id` | str | 唯一識別碼 |
| `source` | str | 資料來源（5 種） |
| `date` | str (YYYY-MM-DD) | 公告日期 |
| `category` | str | 活動 / 卡池 / 競賽 / 系統 / 其他 |
| `title` | str | 公告標題 |
| `content` | str | 公告全文（繁體中文） |
| `link` | str | 原始頁面 URL |
| `photo_link` | str | 代表圖片 URL |
| `tokens_filtered` | str | jieba 分詞結果（停用詞已移除） |
| `top_key_freq` | str | 前 15 關鍵字頻率（Python list 序列化） |
| `sentiment` | float | Gemini 情感分數（0.0 ~ 1.0，離線批次標記） |

### 3.3 CSV：`pk_uma_characters.csv`（角色 PK）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `list_pkNames` | list[str] | 角色名稱清單 |
| `list_photos` | list[str] | 角色圖片 URL 清單 |
| `list_colors` | list[str] | 圖表配色 HEX 清單 |
| `list_sentiInfo` | list[...] | 情感資訊陣列（Chart.js 格式） |

### 3.4 Django ORM：`app_user_keyword_db.models.NewsData`

```python
class NewsData(models.Model):
    item_id         = models.CharField(max_length=255, primary_key=True)
    source          = models.CharField(max_length=50, blank=True)   # 新增
    date            = models.DateField(null=True, blank=True)
    category        = models.CharField(max_length=255)
    title           = models.TextField()
    content         = models.TextField()
    link            = models.URLField(null=True, blank=True, max_length=500)
    photo_link      = models.URLField(null=True, blank=True, max_length=500)
    tokens_filtered = models.TextField(null=True, blank=True)
    top_key_freq    = models.TextField(null=True, blank=True)
    sentiment       = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'date']),
            models.Index(fields=['source']),  # 新增，支援來源過濾
        ]
```

### 3.5 Django ORM：`app_comment_sentiment` 模型群

```python
class Article(models.Model):
    article_id   = models.CharField(max_length=50, primary_key=True)  # 巴哈 sna
    title        = models.CharField(max_length=500)
    url          = models.URLField(max_length=500)
    author       = models.CharField(max_length=100, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    content      = models.TextField(blank=True)
    sentiment    = models.FloatField(null=True, blank=True)  # 0.0~1.0
    created_at   = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    article      = models.ForeignKey(Article, on_delete=models.CASCADE,
                                     related_name='comments')
    comment_id   = models.CharField(max_length=50, unique=True)
    content      = models.TextField()
    author       = models.CharField(max_length=100, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    sentiment    = models.FloatField(null=True, blank=True)

class ArticleEmotion(models.Model):
    """巴哈留言六維度情緒統計（對應巴哈 emoji）"""
    article      = models.OneToOneField(Article, on_delete=models.CASCADE,
                                        related_name='emotion')
    grin         = models.IntegerField(default=0)   # 哈
    happy        = models.IntegerField(default=0)   # 開心
    confused     = models.IntegerField(default=0)   # 混亂
    surprised    = models.IntegerField(default=0)   # 傻眼
    angry        = models.IntegerField(default=0)   # 憤怒
    sad          = models.IntegerField(default=0)   # 難過
```

### 3.6 Django ORM：`app_youtube_uma` 模型群（O5 已實作）

```python
class YouTubeVideo(models.Model):
    video_id      = models.CharField(max_length=20, primary_key=True)
    title         = models.TextField()
    channel_name  = models.CharField(max_length=200, blank=True)
    channel_id    = models.CharField(max_length=50, blank=True)
    published_at  = models.DateTimeField(null=True, blank=True)
    view_count    = models.BigIntegerField(default=0)
    like_count    = models.BigIntegerField(default=0)
    comment_count = models.BigIntegerField(default=0)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    description   = models.TextField(blank=True)
    tags          = models.TextField(blank=True)   # JSON 序列化
    sentiment     = models.FloatField(null=True, blank=True)  # 0.0~1.0
    crawled_at    = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['published_at']),
            models.Index(fields=['view_count']),
        ]
        ordering = ['-published_at']

class YouTubeComment(models.Model):
    comment_id   = models.CharField(max_length=100, primary_key=True)
    video        = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE,
                                     related_name='comments')
    text         = models.TextField()
    author       = models.CharField(max_length=200, blank=True)
    like_count   = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    sentiment    = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-like_count']
```

### 3.7 Django ORM：`app_discord_bot` 模型群（D1-D8 已實作）

```python
class DiscordMessage(models.Model):
    message_id   = models.CharField(max_length=30, primary_key=True)
    channel_id   = models.CharField(max_length=30)
    channel_name = models.CharField(max_length=100, blank=True)
    author       = models.CharField(max_length=100, blank=True)
    content      = models.TextField()
    attachments  = models.TextField(blank=True)    # JSON 序列化
    created_at   = models.DateTimeField()
    crawled_at   = models.DateTimeField(auto_now_add=True)
    is_uma_related = models.BooleanField(default=False)
    sentiment    = models.FloatField(null=True, blank=True)

class DiscordBotConfig(models.Model):
    """Discord Bot 設定（單筆，可從管理後台調整）"""
    bot_token        = models.CharField(max_length=100, blank=True)
    crawl_channel_ids = models.TextField(blank=True)    # 逗號分隔
    news_channel_id  = models.CharField(max_length=30, blank=True)
    news_model       = models.CharField(max_length=50, default='gemini-3.5-flash')
    crawl_limit      = models.IntegerField(default=100)
    is_active        = models.BooleanField(default=True)
    updated_at       = models.DateTimeField(auto_now=True)

class DiscordNewsLog(models.Model):
    """Discord 自動新聞推播記錄"""
    generated_at = models.DateTimeField(auto_now_add=True)
    channel_id   = models.CharField(max_length=30)
    content      = models.TextField()
    source_count = models.IntegerField(default=0)   # 來源訊息數量
    status       = models.CharField(max_length=20, default='sent')  # sent/failed
    error_msg    = models.TextField(blank=True)

    class Meta:
        ordering = ['-generated_at']
```

---

## 4. settings.py INSTALLED_APPS 目標

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django_apscheduler',
    # 主線 apps（基礎分析）
    'app_character_pk',
    'app_user_keyword',
    'app_user_keyword_association',
    'app_user_keyword_sentiment',
    'app_user_keyword_db',
    'app_user_keyword_llm_report',
    # Feature apps
    'app_comment_sentiment',
    'app_uma_top_keyword',
    'app_uma_top_character',
    # 進階 AI apps
    'app_agent_uma',
    'app_rag_uma',
    # 介紹 / 附加
    'app_poa_introduction',
    'app_correlation_analysis',
    # 資料管理 apps
    'app_crawler_admin',
    'app_uma_news',
    'app_uma_comments',
    'app_dashboard',
    # 選用 O1-O5（已實作）
    'app_rag_agent',
    'app_agent_langchain',
    'app_agent_langgraph',
    'app_course_intro',
    'app_youtube_uma',
    # Discord Bot（D1-D8 已實作）
    'app_discord_bot',
]
```

---

## 5. urls.py 根路由

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('',                    include('app_character_pk.urls')),          # 首頁（AI新聞 + 平台簡介）
    path('userkeyword/',        include('app_user_keyword.urls')),
    path('userkeyword_assoc/',  include('app_user_keyword_association.urls')),
    path('userkeyword_senti/',  include('app_user_keyword_sentiment.urls')),
    path('userkeyword_db/',     include('app_user_keyword_db.urls')),
    path('userkeyword_report/', include('app_user_keyword_llm_report.urls')),
    path('comment_sentiment/',  include('app_comment_sentiment.urls')),     # C1 補路由
    path('uma_top_keyword/',    include('app_uma_top_keyword.urls')),
    path('uma_top_character/',  include('app_uma_top_character.urls')),
    path('agent/',              include('app_agent_uma.urls')),             # C2 補 Navbar
    path('rag/',                include('app_rag_uma.urls')),               # C2 補 Navbar
    path('introduction/',       include('app_poa_introduction.urls')),      # C2 補 Navbar
    path('correlation/',        include('app_correlation_analysis.urls')),
    path('crawler-admin/',      include('app_crawler_admin.urls')),
    path('dashboard/',          include('app_dashboard.urls')),
    # Agentic RAG（O1）
    path('rag-agent/',          include('app_rag_agent.urls')),
    # LangChain ReAct（O2）
    path('langchain-agent/',    include('app_agent_langchain.urls')),
    # LangGraph Agent（O3）
    path('langgraph-agent/',    include('app_agent_langgraph.urls')),
    # 課程介紹（O4）
    path('course/',             include('app_course_intro.urls')),
    # YouTube 影片情感（O5）
    path('youtube/',            include('app_youtube_uma.urls')),
    # Discord Bot 管理
    path('discord/',            include('app_discord_bot.urls')),
    path('admin/',              admin.site.urls),
]
```

---

## 6. 雙模型 LLM 報告實作設計

### 6.1 前端（`app_user_keyword_llm_report/templates/.../home.html`）

```html
<div class="mb-3">
  <label class="form-label fw-bold">AI 模型選擇</label>
  <select name="model_provider" class="form-select">
    <option value="gemini">Gemini 3.5 Flash（google-genai 2.9.0）</option>
    <option value="claude">Claude Sonnet 4.6（anthropic 0.111.0）</option>
  </select>
</div>
```

### 6.2 後端（`app_user_keyword_llm_report/views.py`）

```python
import os
from google import genai                   # google-genai 2.9.0
from google.genai import types as genai_types
import anthropic                           # anthropic 0.111.0

def api_get_userkey_llm_report(request):
    provider = request.POST.get('model_provider', 'gemini')
    userkey  = request.POST.get('userkey', '')
    # ... 整合聲量 + 情感資料 ...
    system_prompt = (
        f"你是一位資深的遊戲社群數據分析專家，專精於《賽馬娘 Pretty Derby》。"
        f"以下是多來源（巴哈姆特 bsn=34421、Bilibili BWIKI、ETtoday、UDN、Gamme）"
        f"關於[{userkey}]的聲量與情感數據。"
        f"請撰寫至少 500 字的繁體中文分析報告，以 Markdown 排版。"
    )
    try:
        if provider == 'claude':
            client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt_content}]
            )
            report = msg.content[0].text
        else:  # gemini（預設）
            client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=2048,
                    temperature=0.7,
                ),
                contents=prompt_content,
            )
            report = response.text
        return JsonResponse({"report": report})
    except Exception as e:
        return JsonResponse({"error": "報告生成失敗，請稍後再試。"}, status=500)
```

> **注意**：google-genai 2.9.0 使用 `genai.Client` 的新式 SDK，不再使用 `genai.configure()` 舊式 API。

---

## 7. Agentic AI 設計（app_agent_uma）

### 7.1 工具函數清單（6 種）

| 工具名稱 | 說明 | 對應函數 |
|---------|------|---------|
| `get_keyword_volume` | 查詢關鍵字聲量（週數 N） | 呼叫聲量分析邏輯 |
| `get_keyword_sentiment` | 查詢情感比例 | 呼叫情感分析邏輯 |
| `search_articles` | 全文搜尋 DB 文章 | NewsData ORM 查詢 |
| `get_top_characters` | 取得熱門角色排行 | CSV 讀取 |
| `get_top_keywords` | 取得類別熱門詞彙 | CSV 讀取 |
| `read_local_document` | 讀取 `knowledge_base/` 本地知識文件 | 路徑讀取（H3 需補 knowledge_base/） |

### 7.2 知識庫文件說明

`app_agent_uma/agent_core/tools.py` 中的 `read_local_document()` 從 `knowledge_base/` 目錄讀取文件。**此目錄需由 H3 任務建立**，否則 Agent 呼叫此工具時報錯。

### 7.3 Agent 呼叫流程

```
使用者問題
  │
  ▼
Gemini 3.5 Flash（function calling mode）
  │
  ├── 解析意圖 → 選擇工具
  ├── 呼叫工具函數（最多 5 輪）
  ├── 取得工具結果
  └── 生成最終繁體中文回答
```

### 7.4 API 設計

```
POST /agent/chat/
Body: {"message": "這週卡池公告玩家反應如何？", "session_id": "abc123"}

Response 200:
{
  "reply": "根據最新資料，這週卡池公告...",
  "tool_calls": [
    {"tool": "get_keyword_sentiment", "args": {"userkey": "卡池", "weeks": 1}},
    {"tool": "search_articles", "args": {"query": "卡池", "limit": 5}}
  ],
  "model": "gemini-3.5-flash"
}
```

### 7.5 poa_agent_introduction 視圖修正（M1）

`app_agent_uma/views.py` 的 `poa_agent_introduction()` 原本嘗試讀取不存在的 `app_agent_genaisdk`、`app_agent_langchain`、`app_agent_langgraph` 目錄中的 Markdown 文件。

**快速方案（M1-A）**：修改為只讀取 `app_agent_uma/第一階段說明.md`（已存在）。

```python
def poa_agent_introduction(request):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, '第一階段說明.md')
    html_content = ''
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = markdown.markdown(f.read(), extensions=['extra'])
    return render(request, 'app_agent_uma/poa_agent_introduction.html',
                  {'content_phase1': html_content})
```

**完整方案（O2+O3）**：移植 LangChain / LangGraph app 後，視圖可擴展為三階段說明。

---

## 8. RAG 設計（app_rag_uma）

### 8.1 索引建立流程（H1：build_index.py）

```
來源 1：data/processed/bilibili_uma_preprocessed.csv（或直接讀 uma_news_preprocessed.csv）
來源 2：knowledge_base/*.md / *.txt
  │ text_splitter（chunk_size=512, overlap=64）
  ▼
chunks[]
  │ gemini-embedding-001（768 維）
  ▼
FAISS IndexFlatIP
  │ faiss.write_index()
  ▼
app_rag_uma/index/uma_knowledge.faiss（持久化）
app_rag_uma/index/uma_knowledge_texts.pkl（chunk 文字 + 來源 metadata）
```

### 8.2 啟動時預載索引（M3：views.py 修改）

```python
# app_rag_uma/views.py 頂部加入
import pickle, os, faiss
from django.conf import settings

INDEX_DIR   = os.path.join(settings.BASE_DIR, 'app_rag_uma', 'index')
_INDEX_FILE  = os.path.join(INDEX_DIR, 'uma_knowledge.faiss')
_TEXTS_FILE = os.path.join(INDEX_DIR, 'uma_knowledge_texts.pkl')

if os.path.exists(_INDEX_FILE) and os.path.exists(_TEXTS_FILE):
    _faiss_index = faiss.read_index(_INDEX_FILE)
    with open(_TEXTS_FILE, 'rb') as f:
        _vector_db_texts = pickle.load(f)
    print(f'[RAG] 已載入預建索引，共 {_faiss_index.ntotal} 個向量')
else:
    _vector_db_texts = []
    _faiss_index = faiss.IndexFlatL2(768)
    print('[RAG] 未找到預建索引，使用空白記憶體索引')
```

使用者上傳 PDF 後的向量**疊加**到已存在的索引上，而非覆蓋。

### 8.3 查詢流程

```
使用者問題
  │ gemini-embedding-001 嵌入
  ▼
FAISS 相似度搜尋（top-k=5）
  │
  ▼
取得 top-k chunk 原文
  │ 組成 RAG prompt
  ▼
Gemini 3.5 Flash 生成答案
  │
  ▼
回傳答案 + 引用段落（含來源文件名稱 + chunk index）
```

### 8.4 API 設計

```
POST /rag/query/
Body: {"question": "特別週的固有技能是什麼？"}

Response 200:
{
  "answer": "特別週的固有技能是「...",
  "sources": [
    {"doc": "uma_characters.md", "chunk_idx": 42, "snippet": "..."},
    {"doc": "uma_characters.md", "chunk_idx": 43, "snippet": "..."}
  ]
}

POST /rag/upload/
Body: multipart/form-data, file=<PDF or TXT>
Response 200: {"status": "ok", "chunks_added": 35}
```

---

## 9. 留言情感排程設計（app_comment_sentiment）

### 9.1 排程任務

| 任務 ID | Cron / 間隔 | 說明 |
|--------|------------|------|
| `scrape_bahamut_job` | `interval` 每 60 分鐘 | 爬取巴哈馬娘版最新貼文與留言，存入 Article + Comment |
| `analyze_sentiment_job` | `cron` 每日 02:00 | 對未標記 sentiment 的 Article / Comment 批次呼叫 Gemini 3.5 Flash 情感標記 |

### 9.2 新增儀表板頁面（C1 修復）

目前 `app_comment_sentiment` 只有排程 API 端點，**缺少頁面視圖與 templates**。

**新增 views（`app_comment_sentiment/views.py`）：**

```python
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Article

def dashboard(request):
    """留言情感儀表板 — 主頁面"""
    return render(request, 'app_comment_sentiment/dashboard.html')

def api_data(request):
    """返回文章列表 + 情緒六維度 JSON（供前端 Chart.js 使用）"""
    query = request.GET.get('q', '').strip()
    articles = Article.objects.all().order_by('-published_at', '-created_at')
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )
    data = []
    for article in articles[:50]:  # 限制回傳筆數，避免過大
        emotion_data = {}
        if hasattr(article, 'emotion') and article.emotion is not None:
            e = article.emotion
            emotion_data = {
                'grin': e.grin, 'happy': e.happy,
                'confused': e.confused, 'surprised': e.surprised,
                'angry': e.angry, 'sad': e.sad,
            }
        data.append({
            'id': article.article_id,
            'title': article.title,
            'url': article.url,
            'published_at': article.published_at.strftime('%Y-%m-%d') if article.published_at else '',
            'sentiment': article.sentiment,
            'comments_count': article.comments.count(),
            'emotion': emotion_data,
        })
    return JsonResponse({'articles': data, 'total': Article.objects.count()})
```

**新增路由至 `website_configs/urls.py`：**

```python
path('comment_sentiment/', include('app_comment_sentiment.urls')),
```

### 9.3 APScheduler 初始化（Django AppConfig.ready()）

```python
# app_comment_sentiment/apps.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
import os

class AppCommentSentimentConfig(AppConfig):
    name = 'app_comment_sentiment'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            return  # 避免 devserver reloader 重複啟動
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        scheduler.add_job(scrape_bahamut_job,    'interval', minutes=60, id='scrape_bahamut',
                          replace_existing=True)
        scheduler.add_job(analyze_sentiment_job, 'cron',     hour=2,     id='analyze_sentiment',
                          replace_existing=True)
        scheduler.start()
```

### 9.4 巴哈爬蟲（`pipeline/scrape_bahamut.py`）

| 參數 | 值 | 說明 |
|------|---|------|
| 目標 URL | `https://forum.gamer.com.tw/B.php?bsn=34421` | 馬娘哈啦板 |
| 斷點續爬 | 以 `sna`（文章流水號）為唯一鍵，已存在 DB 則跳過 | |
| 每次最多 | `MAX_NEW_ARTICLES = 50` | 避免單次執行過久 |
| 留言 API | `https://forum.gamer.com.tw/ajax/bahamut_post.php?bsn={}&snA={}&page={}` | 取文章留言 |
| User-Agent | 隨機輪替（6 個 UA） | 降低被封風險 |
| 失敗重試 | 最多 3 次，間隔 2 秒 | |

### 9.5 scrape_bahamut management command（H2 新增）

```python
# app_comment_sentiment/management/commands/scrape_bahamut.py
from django.core.management.base import BaseCommand
from app_comment_sentiment.models import Article, Comment
import requests
from bs4 import BeautifulSoup

BSN = '34421'
BASE_URL = f'https://forum.gamer.com.tw/B.php?bsn={BSN}'

class Command(BaseCommand):
    help = '爬取巴哈姆特馬娘哈啦板貼文與留言，存入 Article/Comment 表'

    def handle(self, *args, **options):
        resp = requests.get(BASE_URL, timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 解析貼文列表，存入 Article / Comment
        self.stdout.write(self.style.SUCCESS('爬取完成！'))
```

---

## 10. 資料管線修復設計（Pipeline P1–P6）

### 10.1 根本問題

`uma_news_preprocessed.csv` 目前僅有 **344 筆**（bilibili 166 + ettoday 87 + bahamut 91）：
- UDN 191 筆 raw 資料、Gamme 數十筆 raw 資料**完全未進入任何分析管線**
- Bahamut 原始資料有 **5,951 筆**，但只有 91 筆（1.5%）進入系統
- 根本原因：`label_sentiment.py` 硬編碼讀取舊路徑 `bilibili_uma_tokenized.csv`，且依賴 `/workspaces/8_10_emi/` 另一環境的設定檔

### 10.2 修復目標：Canonical Raw CSV 規格

所有爬蟲輸出至 `data/raw/{source}_uma_raw.csv`，欄位統一為：

```
item_id | source | date(YYYY-MM-DD) | category(繁中5類) | title | content | link | photo_link
```

### 10.3 label_sentiment.py 修復要點（P4）

三個必修項：
1. **修正輸入路徑**：`bilibili_uma_tokenized.csv` → `data/processed/uma_combined_tokenized.csv`
2. **移除硬編碼** `CONFIG_PATH=/workspaces/8_10_emi/...`，改用 `.env` + `python-dotenv`
3. **更新 Gemini 呼叫**：移除舊式 `requests.post`，改用 `google-genai 2.9.0` 新式 SDK

```python
# pipeline/label_sentiment.py（修復後關鍵片段）
from pathlib import Path
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY 未設定，請檢查 .env 檔案")

_ROOT   = Path(__file__).parent.parent
IN_CSV  = _ROOT / 'data' / 'processed' / 'uma_combined_tokenized.csv'
OUT_CSV = _ROOT / 'data' / 'processed' / 'uma_news_preprocessed.csv'

client = genai.Client(api_key=API_KEY)

def call_gemini(prompt: str) -> str | None:
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            config=genai_types.GenerateContentConfig(
                max_output_tokens=200, temperature=0.1,
            ),
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"  [Gemini] 呼叫失敗: {e}")
        return None

# 增量標記：已有 sentiment 值的列跳過
for i, row in df.iterrows():
    existing = row.get('sentiment')
    if existing is not None and str(existing) not in ('', 'nan', 'None'):
        continue
    # ... 呼叫 Gemini 標記 ...
```

### 10.4 完整 Pipeline 執行序列（P6）

```bash
# Step 1: 重新爬取（若 raw 資料需更新）
python pipeline/crawl_bilibili_uma.py
python pipeline/crawl_bahamut_uma.py
python pipeline/crawl_ettoday_uma.py
python pipeline/crawl_udn_uma.py
python pipeline/crawl_gamme_uma.py

# Step 2: 多來源合併前處理（斷詞 + 去重）→ uma_combined_tokenized.csv
python pipeline/preprocess.py

# Step 3: Gemini 情感標記（約 14 分鐘/1,000 筆）
python pipeline/label_sentiment.py

# Step 4: 生成熱門 CSV
python scripts/generate_topkey_csv.py
python scripts/generate_top_character_csv.py

# Step 5: 清空 DB 並重新匯入
python scripts/import_uma_data.py --clear
```

**預期 DB 筆數（修復後）：** bilibili ≥150、bahamut ≥500、ettoday ≥200、udn ≥150、gamme ≥30，**合計 ≥ 1,000 筆**。

---

## 11. Docker 部署架構

### 11.1 `docker-compose.yml` 服務

環境變數統一由**專案根目錄** `.env` 提供（與本機 `python manage.py runserver` 共用同一份；`settings.py` 亦以 `load_dotenv` 讀取根目錄 `.env`）。

四個服務：`db`（PostgreSQL）、`web-poa`（Django+Gunicorn）、`nginx`、`discord-bot`。

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: postgres-poa
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-umamusume}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - pgdata_poa:/var/lib/postgresql/data
    healthcheck:                       # web/bot 以 service_healthy 等待 DB 就緒
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-umamusume}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  web-poa:
    build: { context: ., dockerfile: ./docker-files-poa/Dockerfile }
    container_name: web-poa
    environment:                       # 啟用 PostgreSQL（settings.py 依此切換）
      DJANGO_DB_ENGINE: postgres
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      POSTGRES_DB: ${POSTGRES_DB:-umamusume}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - .:/app
      - static_volume_poa:/app/staticfiles
      - media_volume_poa:/app/media
    expose: ["8000"]
    env_file: ./.env
    depends_on:
      db: { condition: service_healthy }
    restart: unless-stopped

  nginx:
    build: { context: ./nginx }
    container_name: nginx-poa
    volumes:
      - static_volume_poa:/app/staticfiles
      - media_volume_poa:/app/media
    ports: ["80:80"]
    depends_on: [web-poa]
    restart: unless-stopped

  discord-bot:
    build: { context: ., dockerfile: ./docker-files-poa/Dockerfile }
    command: python manage.py run_discord_bot    # entrypoint 會 exec 此指令（非 Gunicorn）
    environment:                       # 與 web-poa 共用同一 PostgreSQL
      DJANGO_DB_ENGINE: postgres
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      POSTGRES_DB: ${POSTGRES_DB:-umamusume}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    env_file: ./.env
    volumes:
      - .:/app
      - media_volume_poa:/app/media
    depends_on:
      db: { condition: service_healthy }
      web-poa: { condition: service_started }
    restart: unless-stopped

volumes:
  static_volume_poa:
  media_volume_poa:
  pgdata_poa:
```

> **資料庫選型（0.6.45 變更）**：原先 SQLite 檔（`db.sqlite3`）位於 `.:/app` bind mount，在 Windows Docker Desktop（WSL2）下不支援 SQLite 的 POSIX 檔案鎖，且 `web-poa`（多 worker）＋ `discord-bot` 同時寫入會噴 `disk I/O error`（例：`_sync_guild_to_db` 失敗 → 頻道快取寫不進 → 推播設定無法完成）。改用 PostgreSQL 後由 DB 原生處理並發寫入，徹底解決。本機開發未設 `DJANGO_DB_ENGINE` 時仍走 SQLite。

### 11.2 `docker-files-poa/entrypoint.sh`（M2 更新；0.6.45 加入指令分流）

`Dockerfile` 設 `ENTRYPOINT ["/entrypoint.sh"]`。**0.6.45 修正前**，entrypoint 結尾寫死 `exec gunicorn ...`、忽略 compose 傳入的 `command`，導致 `discord-bot` 容器其實又跑了一個 Gunicorn、Bot 從未啟動。修正後改為「有傳入指令就 `exec "$@"`，否則才預設啟動 Gunicorn」：

```bash
#!/bin/bash
set -e

# ── 指令分流：bot 容器走精簡流程（不重複 migrate / 匯入，避免並發寫入）──
if [ "$#" -gt 0 ]; then
    echo "=== 啟動指定服務：$* ==="
    for i in $(seq 1 30); do          # 等 web-poa 完成遷移後再啟動
        if python manage.py migrate --check >/dev/null 2>&1; then break; fi
        sleep 2
    done
    exec "$@"                          # 例：python manage.py run_discord_bot
fi

# ── 預設（web-poa）：完整初始化後啟動 Gunicorn ──
python manage.py migrate              # PostgreSQL（依 settings.py 環境變數）

# idempotent 資料初始化（DB 空才匯入）
COUNT=$(python manage.py shell -c \
  "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())" \
  2>/dev/null || echo "0")
if [ "$COUNT" = "0" ]; then
    python scripts/import_uma_data.py
    python scripts/generate_topkey_csv.py
    python scripts/generate_top_character_csv.py
fi

# 建立 RAG 索引（如果不存在）
if [ ! -f "app_rag_uma/index/uma_knowledge.faiss" ]; then
    python app_rag_uma/build_index.py || echo "RAG 索引建立失敗（跳過）"
fi

exec gunicorn website_configs.wsgi:application \
    --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

### 11.3 `Dockerfile`

```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
```

### 11.4 `nginx/nginx.conf`

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    client_max_body_size 20M;

    location /static/ {
        alias /app/staticfiles/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 12. requirements.txt（版本釘牢）

```text
# Web Framework
Django==5.2.15
gunicorn>=23.0

# AI SDKs（版本查證 2026-06-22）
google-genai==2.9.0
anthropic==0.111.0

# Vector Search
faiss-cpu==1.14.2

# Scheduler
APScheduler==3.11.2
django-apscheduler==0.7.0

# Data Processing
pandas>=2.2
numpy>=1.26
jieba>=0.42

# Web Scraping
requests>=2.31
beautifulsoup4>=4.12
selenium>=4.20
playwright>=1.44

# Utilities
python-dotenv>=1.0
django-cors-headers>=4.3
opencc-python-reimplemented>=0.1.7
markdown>=3.5

# Production
whitenoise>=6.7

# O2/O3（LangChain/LangGraph — 已實作）
langchain>=1.3.0
langchain-google-genai>=4.2.0
langgraph>=0.2.0

# D1-D8（Discord Bot — 已實作）
discord.py==2.4.0
```

> **棄用警告**：勿使用 `google-generativeai`（已棄用）。勿使用 `openai` 套件呼叫 Gemini（舊方式）。

---

## 13. .env 金鑰規格

```
GEMINI_API_KEY=AIzaSy...                 # 必填
ANTHROPIC_API_KEY=sk-ant-api03-...       # 必填（選 Claude 時使用）
DJANGO_SECRET_KEY=隨機長字串              # 必填
DJANGO_DEBUG=False                        # 生產環境
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# YouTube Data API v3（O5 已實作）
YOUTUBE_API_KEY=AIzaSy...                # O5 必填

# Discord Bot（D1-D8 已實作）
DISCORD_BOT_TOKEN=Bot_your_token_here    # Discord 開發者後台取得
DISCORD_CRAWL_CHANNEL_IDS=123456789      # 逗號分隔多個頻道 ID
DISCORD_NEWS_CHANNEL_ID=111222333        # 新聞推播目標頻道 ID
DISCORD_NEWS_MODEL=gemini-3.5-flash      # 新聞生成模型
DISCORD_CRAWL_LIMIT=100                  # 每次爬取訊息上限
```

---

## 14. API 契約完整表

### 14.1 角色 PK
```
POST /api_get_character_pk/
Body: characters=特別週,無聲鈴鹿

Response 200:
{
  "pkNames": ["特別週", "無聲鈴鹿"],
  "photos":  ["https://...", "https://..."],
  "colors":  ["#7C3AED", "#2E9E6B"],
  "sentiInfo": [[...], [...]]
}
```

### 14.2 聲量分析
```
POST /userkeyword/api_get_top_userkey/
Body: userkey=卡池&cate=全部&cond=or&weeks=4

Response 200:
{
  "key_occurrence_cat": {"活動": 0, "卡池": 12, "競賽": 0, "系統": 0, "其他": 3, "全部": 15},
  "key_freq_cat":        {"活動": 0, "卡池": 24, ...},
  "key_time_freq":       [{"x": "2025-01-01", "y": 2}, ...]
}
Error: {"error": "查無結果，請換個關鍵字試試"}
```

### 14.3 情感分析
```
POST /userkeyword_senti/api_get_userkey_sentiment/
Body: userkey=限定&cate=全部&cond=or&weeks=12

Response 200:
{
  "sentiCount": {"Positive": 8, "Negative": 2, "Neutral": 3},
  "data_pos": [{"x": "2025-01-01", "y": 1}, ...],
  "data_neg": [{"x": "2025-01-01", "y": 0}, ...]
}
```

### 14.4 DB 版全文搜尋
```
POST /userkeyword_db/api_get_userkey_data/
Body: userkey=活動&cate=全部&cond=or&weeks=52

Response 200:
{
  "newslinks":    [{"title": "...", "link": "...", "photo_link": "..."}, ...],  // ≤10
  "num_articles": 42,
  "key_time_freq": [...],
  "sentiCount":   {"Positive": ..., "Negative": ..., "Neutral": ...}
}
```

### 14.5 LLM 報告生成
```
POST /userkeyword_report/api_get_userkey_llm_report/
Body: userkey=卡池&cate=全部&cond=or&weeks=4&model_provider=claude

Response 200: {"report": "# 《賽馬娘》卡池分析報告\n\n...（≥500字 Markdown）"}
Error:        {"error": "報告生成失敗，請稍後再試。"}
Error:        {"error": "Claude API 金鑰未設定"}  // ANTHROPIC_API_KEY 缺失時
```

### 14.6 留言情感儀表板（C1 補充）
```
GET /comment_sentiment/
→ 渲染儀表板頁面

GET /comment_sentiment/api/data/?q=卡池
Response 200:
{
  "articles": [
    {
      "id": "12345678",
      "title": "【情報】新卡池公告",
      "url": "https://forum.gamer.com.tw/...",
      "sentiment": 0.72,
      "emotion": {"grin": 15, "happy": 30, "confused": 5, "surprised": 3, "angry": 1, "sad": 0},
      "comments_count": 54,
      "published_at": "2026-06-15"
    }
  ],
  "total": 120
}

POST /comment_sentiment/api/trigger_scrape/
→ 手動觸發爬蟲（一次性執行）
Response 200: {"status": "started", "job_id": "scrape_bahamut"}
```

### 14.7 熱門關鍵詞
```
POST /uma_top_keyword/api_get_cate_topword/
Body: news_category=卡池&topk=10

Response 200:
{
  "chart_data": {"category": "卡池", "labels": ["卡池", "限定", ...], "values": [200, 150, ...]},
  "wf_pairs": [["卡池", 200], ["限定", 150], ...]
}
```

### 14.8 熱門角色
```
POST /uma_top_character/api_get_topCharacter/
Body: news_category=活動&topk=10

Response 200:
{
  "chart_data": {"category": "活動", "labels": ["特別週", "無聲鈴鹿", ...], "values": [45, 32, ...]},
  "wf_pairs": [["特別週", 45], ["無聲鈴鹿", 32], ...]
}
```

### 14.9 Agentic AI
```
POST /agent/chat/
Body (JSON): {"message": "最近限定卡玩家反應怎樣？", "session_id": "u123"}

Response 200:
{
  "reply": "根據分析資料，近4週限定關鍵字...",
  "tool_calls": [{"tool": "get_keyword_sentiment", "args": {"userkey": "限定", "weeks": 4}}],
  "model": "gemini-3.5-flash"
}
```

### 14.10 RAG 問答
```
POST /rag/query/
Body (JSON): {"question": "特別週的固有技能是什麼？"}

Response 200:
{
  "answer": "特別週的固有技能是「ハルウララ」，效果為...",
  "sources": [{"doc": "uma_characters.md", "chunk_idx": 42, "snippet": "..."}]
}
Error: {"error": "知識庫尚未建立，請先執行 build_index"}
```

### 14.11 來源統計（新增）
```
GET /api/source_stats/
Response 200:
{
  "sources": {
    "bilibili": 166, "bahamut": 500, "ettoday": 200,
    "udn": 150, "gamme": 30
  },
  "total": 1046
}
```

### 14.12 YouTube 儀表板（O5 已實作）
```
GET /youtube/
→ 渲染 YouTube 影片情感儀表板

GET /youtube/api/videos/
Response 200:
{
  "videos": [{
    "video_id": "abc123",
    "title": "...",
    "channel": "...",
    "view_count": 150000,
    "sentiment": 0.75,
    "sentiment_label": "Positive",
    "url": "https://www.youtube.com/watch?v=abc123"
  }],
  "total": 50
}

GET /youtube/api/stats/
Response 200:
{
  "weekly_trend": [{"week": "2026-06-01", "count": 12, "avg_sentiment": 0.68}]
}
```

### 14.13 情報站控制台 API（Admin Platform Plan A-F）
```
GET /crawler-admin/api/source_stats/
Response: {"sources": {"bilibili": 166, "bahamut": 500, "ettoday": 200, "udn": 150, "gamme": 30}, "total": 1046}

GET /crawler-admin/api/youtube_quota/
Response: {"date": "2026-06-23", "units_used": 1200, "units_limit": 10000, "percent": 12}

POST /crawler-admin/api/youtube_crawl/
Response: {"status": "started", "job_id": "crawl_youtube_manual"}

GET /crawler-admin/api/rag_status/
Response: {"index_exists": true, "vector_count": 1250, "index_size_kb": 384,
           "last_built": "2026-06-23T10:00:00", "kb_files": ["uma_characters.md"]}

POST /crawler-admin/api/rebuild_rag/
Response: {"status": "started"}

GET /crawler-admin/api/crawler_history/
Response: {"runs": [{"source": "bahamut", "started_at": "...", "success": true, "count": 50}]}

POST /crawler-admin/api/run_pipeline/
Body: {"steps": [2, 3, 4, 5]}   // 選擇要執行的 Step（1=爬蟲, 2=preprocess, 3=label, 4=topcsv, 5=import）
Response: {"status": "started", "steps": [2, 3, 4, 5]}

GET /crawler-admin/api/pipeline_status/
Response:
{
  "running": true,
  "progress_pct": 42,
  "estimated_remaining_s": 711,
  "running_step": 3,
  "steps": [
    {
      "step": 2,
      "label": "合併前處理（preprocess.py）",
      "status": "success",
      "progress_pct": 100,
      "tail": "...最近輸出...",
      "returncode": 0
    },
    {
      "step": 3,
      "label": "Gemini 情感標記（label_sentiment.py）",
      "status": "running",
      "progress_pct": 31,
      "tail": "...執行中增量 log..."
    }
  ]
}
```

### 14.14 爬蟲設定與排程 API 防呆（2026-06-23）
```
GET /crawler-admin/api/config/<source>/
Response 200:
{
  "source": "bilibili",
  "max_pages": 50,
  "delay_min": 0.8,
  "delay_max": 1.5,
  "use_playwright": false,
  "user_agent": "...",
  "extra_notes": ""
}

POST /crawler-admin/api/config/<source>/save/
Body: {"max_pages": 0, "delay_min": 0.0, "delay_max": 1.2, "use_playwright": false}
Response 200: {"ok": true, "config": {...最新儲存值...}}
Error 400:    {"error": "delay_max 不可小於 delay_min"}

POST /crawler-admin/api/schedule/save/
Body: {"source":"bahamut","mode":"daily","cron_expr":"0 2 * * *","enabled":true}
Response 200: {"ok": true, "schedule": {...}}
Error 400:    {"error": "不支援的 mode: xxx"} / {"error":"cron_expr 不可為空"}

GET /crawler-admin/api/history/?limit=oops
GET /crawler-admin/api/log/<source>/?offset=oops
→ 參數自動安全轉型（fallback 至預設值），不得回傳 500
```

### 14.15 Discord Bot API（D1-D8）
```
GET /discord/api/status/
Response: {"active": true, "channels": ["123456789"], "messages_today": 42,
           "last_crawl": "2026-06-23T14:30:00", "news_sent_today": 1}

POST /discord/api/trigger_news/
Response: {"status": "started"}

GET /discord/api/history/
Response: {"logs": [{"generated_at": "...", "status": "sent", "source_count": 15, "content": "..."}]}
```

---

## 15. 情感分類標準

| 分數範圍 | 分類 |
|---------|------|
| score ≥ 0.6 | Positive（正面） |
| score ≤ 0.4 | Negative（負面） |
| 0.4 < score < 0.6 | Neutral（中性） |

---

## 16. 邊界條件與錯誤處理

| 情況 | 處理方式 |
|------|---------|
| 關鍵字查無結果 | 回傳 `{"error": "查無結果，請換個關鍵字試試"}` |
| LLM API 失敗（timeout / 金鑰錯誤） | try-except，回傳 `{"error": "報告生成失敗，請稍後再試。"}` + server log |
| `.env` 缺少 `GEMINI_API_KEY` | `settings.py` 啟動時 `raise ValueError` |
| `.env` 缺少 `ANTHROPIC_API_KEY` | 選擇 Claude 時 `views.py` 檢查，回傳 `{"error": "Claude API 金鑰未設定"}` |
| `weeks=0` | 不套用日期篩選，查全部時間範圍 |
| DB 無任何資料（未執行 import） | `queryset.exists()` 為 False，回傳 error JSON |
| 角色 PK 選角少於 2 個 | 前端 JS 驗證，不送出 API |
| APScheduler 任務執行失敗 | `django_apscheduler` 記錄 `DjangoJobExecutionError`，不中斷 scheduler |
| FAISS 索引不存在（首次啟動） | RAG views 回傳 `{"error": "知識庫尚未建立，請先執行 build_index"}` |
| `knowledge_base/` 目錄不存在 | Agent `read_local_document` 工具回傳 "找不到知識庫"，不崩潰 |
| 上傳文件大小超過 20MB | Nginx 層 `client_max_body_size 20M` 回傳 413 |
| `label_sentiment.py` 讀取舊路徑 `bilibili_uma_tokenized.csv` | P4 修復：改讀 `data/processed/uma_combined_tokenized.csv` |
| `label_sentiment.py` 舊 `CONFIG_PATH` 指向另一環境 | P4 修復：移除硬編碼，改用 `.env` |
| `gemini-2.0-flash` 舊字串（設定錯誤） | 已棄用，請一律改為 `gemini-3.5-flash`（2026/6/1 停服） |
| `/comment_sentiment/` URL 不存在 | C1 修復：新增 dashboard view + urls 路由 |
| Navbar 缺失 AI/RAG/留言入口 | C2 修復：更新 `base.html` 加入所有已實作 app 連結 |
| `poa_agent_introduction` 讀取不存在目錄 | M1 修復：改為只讀取 `app_agent_uma/第一階段說明.md` |
| YouTube API Quota 超限 | O5 已實作：捕獲 HTTP 429，記錄到 `YouTubeQuotaLog`，停止本次爬取，下次排程繼續 |
| Discord Bot Token 無效 | 啟動時捕獲 `discord.LoginFailure`，寫入 log 並優雅退出，不影響 web 服務 |
| Discord 頻道 ID 不存在 | `crawler.py` 捕獲 `discord.NotFound`，跳過該頻道，繼續爬取其他頻道 |
| RAG 索引重建失敗（API 超時）| `rebuild_rag` API 以 `subprocess` 非同步執行，捕獲 returncode != 0，回傳錯誤 log |
| Pipeline 中途失敗 | 每個 Step 獨立執行，失敗的 Step 記錄錯誤後繼續後續 Step |
| `YouTubeQuotaLog` 日期重複 | `unique=True` + `get_or_create`，每日只建一筆 |

---

## 18. 資料管理中心設計（admin-platform-plan.html A1–F1）

> **改版背景**：原 `app_crawler_admin`（爬蟲後台）功能過於單一，僅能監控 5 來源爬蟲狀態。依 `admin-platform-plan.html` 規劃，擴充為「情報站控制台」，新增 YouTube API 管理、統一儀表板、Discord Bot 管理、RAG 知識庫管理等模組。

---

### 18.1 平台健康儀表板（A-系列：重命名 + 入口整合）

**路由**：`/crawler-admin/`（`app_crawler_admin/views.py` → `dashboard` 視圖）

**頁面元素：**

| 區塊 | 內容 | 技術 |
|------|------|------|
| 平台狀態卡 | NewsData 總筆數、Article/Comment 筆數、YouTubeVideo 筆數、DiscordMessage 筆數 | Django ORM count() |
| 5 爬蟲來源狀態 | 最後執行時間 + 成功/失敗次數 + 即時執行按鈕 | `CrawlerRun` 模型 |
| YouTube API 配額 | 今日已用 / 10,000 units 進度條 | `YouTubeQuotaLog` 模型 |
| Discord Bot 狀態 | 在線/離線、最後爬取時間、今日新聞推播次數 | `DiscordNewsLog` 模型 |
| RAG 索引狀態 | 索引存在 Y/N、向量數量、最後建立時間 | 讀取 `app_rag_uma/index/uma_knowledge.faiss` |
| 快速操作入口 | Pipeline 一鍵執行、Discord Bot 啟動/停止、RAG 重建索引按鈕 | AJAX POST |

**Navbar 新增入口：**

```html
<!-- 爬蟲後台更名為「情報站控制台」，在 base.html Navbar 中 -->
<a class="nav-link" href="{% url 'app_crawler_admin:dashboard' %}">
  🛡️ 情報站控制台
</a>
```

---

### 18.2 YouTube API 管理頁（B-系列）

**路由**：`/crawler-admin/youtube/`

**功能：**

| 功能 | 說明 |
|------|------|
| B1：配額用量圓環圖 | 今日已用量 / 10,000 units，Chart.js Doughnut，每小時自動刷新 |
| B2：新增搜尋關鍵字 | 表單提交搜尋詞 → `YOUTUBE_SEARCH_QUERIES` 環境變數或 DB 設定 |
| B3：影片清單管理 | 列表 + 分頁，可手動觸發重爬單部影片 |
| B4：情感趨勢折線圖 | 週/月維度的 avg_sentiment 折線圖（Chart.js） |
| B5：手動觸發爬取 | `python manage.py crawl_youtube` AJAX 呼叫，顯示即時進度 |

**`YouTubeQuotaLog` 模型（新增）：**

```python
class YouTubeQuotaLog(models.Model):
    """每日 YouTube API 配額使用記錄"""
    date          = models.DateField(auto_now_add=True, unique=True)
    units_used    = models.IntegerField(default=0)    # 今日已消耗
    units_limit   = models.IntegerField(default=10000)
    last_crawl_at = models.DateTimeField(null=True, blank=True)
    videos_added  = models.IntegerField(default=0)    # 本次新增影片數

    class Meta:
        ordering = ['-date']
```

**API：**
```
GET /crawler-admin/api/youtube_quota/
Response: {"date": "2026-06-23", "units_used": 1200, "units_limit": 10000, "percent": 12}

POST /crawler-admin/api/youtube_crawl/
Response: {"status": "started", "job_id": "crawl_youtube_manual"}
```

---

### 18.3 統一資料儀表板（C-系列）

**路由**：`/crawler-admin/` 首頁卡片 + `/dashboard/`（已存在）

| 功能 | 路由 | 說明 |
|------|------|------|
| C1：多來源資料量比較 | `/crawler-admin/api/source_stats/` | 各來源 NewsData 筆數長條圖 |
| C2：情感分數分布 | `/crawler-admin/api/sentiment_stats/` | 全資料庫 Positive/Neutral/Negative 圓餅圖 |
| C3：每日資料入庫趨勢 | `/crawler-admin/api/daily_stats/` | 7/30 天 NewsData 新增折線圖 |
| C4：爬蟲執行歷史 | `/crawler-admin/api/crawler_history/` | `CrawlerRun` 最近 20 次執行記錄表格 |

---

### 18.4 Discord Bot 管理頁（D-系列）

**路由**：`/crawler-admin/discord/` 或 `/discord/`

| 功能 | 說明 |
|------|------|
| D1：Bot 狀態監控 | 在線/離線、目前監聽頻道清單、今日爬取訊息數 |
| D2：設定管理 | 可視化修改 `DiscordBotConfig`（Token 遮罩顯示、頻道 ID 列表） |
| D3：推播歷史記錄 | `DiscordNewsLog` 列表，含推播時間、內容摘要、狀態（成功/失敗） |

**API：**
```
GET /discord/api/status/
Response: {"active": true, "channels": ["123456789", "987654321"], "messages_today": 42}

POST /discord/api/trigger_news/
Response: {"status": "started", "estimated_at": "2026-06-23T15:30:00"}
```

---

### 18.5 RAG 知識庫管理頁（E-系列）

**路由**：`/crawler-admin/rag/`

| 功能 | 說明 |
|------|------|
| E1：索引狀態顯示 | FAISS 索引存在 Y/N、向量數量、最後建立時間、索引大小（KB/MB） |
| E2：一鍵重建索引 | AJAX 呼叫 `python app_rag_uma/build_index.py`，顯示進度 log |
| 知識庫文件列表 | 顯示 `knowledge_base/` 下所有 `.md` 文件及大小 |
| 上傳知識庫文件 | 直接從管理頁上傳 `.md` / `.txt` 文件到 `knowledge_base/` |

**API：**
```
GET /crawler-admin/api/rag_status/
Response: {"index_exists": true, "vector_count": 1250, "index_size_kb": 384,
           "last_built": "2026-06-23T10:00:00", "kb_files": ["uma_characters.md"]}

POST /crawler-admin/api/rebuild_rag/
Response: {"status": "started"}
```

---

### 18.6 爬蟲 Pipeline 一鍵執行（F-系列）

**路由**：`/crawler-admin/pipeline/`

**功能：** 從管理界面觸發完整資料管線（F1）：

```
Step 1（選擇性）：重新爬取 5 來源 raw 資料
Step 2：python pipeline/preprocess.py
Step 3：python pipeline/label_sentiment.py
Step 4：python scripts/generate_topkey_csv.py + generate_top_character_csv.py
Step 5：python scripts/import_uma_data.py --clear（可選擇是否清空 DB）
```

**UI 設計：**
- 每個 Step 顯示進度條 + 即時 log（AJAX polling，每 1.5 秒刷新）
- 顯示「總進度（0~100）+ 目前執行 Step + 預估剩餘時間」
- 每個 Step 顯示 mini 進度條（`pending/running/success/failed`）與最近輸出摘錄
- 可單獨執行任意 Step（non-sequential 執行也支援）
- 執行歷史記錄（`CrawlerRun` 擴充）

---

## 19. Discord Bot 系統設計（D1-D8）

### 19.1 Bot 功能概觀

```
Discord 頻道（馬娘相關）
  │ discord.py（D2：run_discord_bot command）
  ▼
crawler.py（D3：增量爬取，以 message_id 去重）
  │
  ▼
classifier.py（D4：雙層篩選）
  ├── Layer 1：關鍵字匹配（馬娘/賽馬娘/特別週等）
  └── Layer 2：Gemini 確認（排除誤報）
  │
  ▼（is_uma_related=True 的訊息）
converter.py（D5：DiscordMessage → NewsData 格式）
  │
  ▼
news_generator.py（D6：Gemini 彙整 N 則訊息 → 一篇新聞）
  │
  ▼
Discord 頻道推播 + DiscordNewsLog 記錄
```

### 19.2 APScheduler 排程（Bot 常駐時）

| 任務 | Cron/Interval | 說明 |
|------|--------------|------|
| `discord_crawl_job` | `interval` 每 60 分鐘 | 爬取所有設定頻道的新訊息 |
| `discord_classify_job` | `interval` 每 2 小時 | 對未分類訊息執行雙層篩選 |
| `discord_convert_job` | `cron` 每日 01:00 | 將 `is_umamusume=True` 訊息轉換存入 NewsData |
| `discord_news_per_guild` | `cron` 每小時整點 | 依各伺服器 `GuildSetting.news_hour` 推播摘要 |
| 手動任務（控制台） | 按需 | `/crawler-admin/discord/` 可手動觸發 crawl / classify / convert / news |

> 舊版 SPEC 曾記載 classify 每 60 分鐘；實作為 **每 2 小時**（`scheduler.py`）。

### 19.4 D4：馬娘相關訊息辨識（雙層分類）

**實作檔案**：`app_discord_bot/classifier.py`  
**資料欄位**：`DiscordMessage.is_umamusume`（`True` / `False` / `None`）、`classified_by`（`keyword` / `gemini` / 空）

#### 19.4.1 三種分類狀態

| `is_umamusume` | UI 顯示 | 意義 |
|----------------|---------|------|
| `None` | 待分類 | 已爬取、尚未執行分類任務 |
| `True` | 馬娘 | 判定與《賽馬娘 Pretty Derby》相關 |
| `False` | 無關 | 判定與遊戲無關 |

爬取階段（`crawler.py`）**不**做馬娘判斷，一律寫入 `is_umamusume=None`。分類由排程或控制台手動任務「分類待分類訊息」執行 `run_classifier()`。

#### 19.4.2 爬取前置過濾（非分類）

`crawl_channel` 寫入 DB 前會略過：
- Bot 帳號發送的訊息（`msg.author.bot`）
- 純空白內容（`not msg.content.strip()`）

#### 19.4.3 Layer 1 — 關鍵字比對（`layer1_keyword`）

對每則 `is_umamusume=None` 的訊息，將 `content` 轉小寫後做**子字串包含**比對，命中任一關鍵字即標記：

- `is_umamusume = True`
- `classified_by = 'keyword'`

**關鍵字詞表**（`UMA_KEYWORDS`，可擴充）：

| 類別 | 範例 |
|------|------|
| 遊戲名稱 | 賽馬娘、馬娘、ウマ娘、umamusume、uma musume |
| 育成 / 玩法 | 育成、因子、技能、固有、進化技能、支援卡、抽卡、活動、劇情、PvP、速通 |
| 角色名 | 特別週、無聲鈴鹿、東海帝王、小栗帽、目白麥昆…（見 `classifier.py` 完整清單） |

**未命中關鍵字時**：
- 內容長度 **≤ 20 字** → 直接標記 `False`（`keyword`），不送 AI（避免短句浪費 API）
- 內容長度 **> 20 字** → 進入 Layer 2

#### 19.4.4 Layer 2 — Gemini 批次確認（`layer2_gemini_batch`）

將 Layer 1 未命中的長訊息以 **50 則為一批** 送 `gemini-3.1-flash-lite`（`temperature=0`），Prompt 要求逐則回覆 `序號. YES` 或 `序號. NO`（是否與「賽馬娘 Pretty Derby」遊戲相關）。

- 解析成功 → `is_umamusume` 依 YES/NO 設定，`classified_by = 'gemini'`
- API 失敗或無法解析該則 → **預設 `False`**（保守策略，避免誤標）

需設定環境變數 `GEMINI_API_KEY`。

#### 19.4.5 分類後資料流

```
is_umamusume=True  ──► converter.py ──► NewsData（source='discord'）
                   ──► news_generator.py 彙整推播素材
is_umamusume=False ──► 保留於 DiscordMessage，不進分析鏈
is_umamusume=None  ──► 等待下次 classify 任務
```

控制台「Discord 訊息查閱」可依 `classify=uma|nonuma|pending` 篩選；UMA Info 伺服器總覽的「賽馬娘相關」計數為 `is_umamusume=True`。

#### 19.4.6 限制與已知取捨

- 關鍵字為**子字串匹配**，可能誤判（例如非遊戲語境出現「活動」）
- Layer 2 每則訊息僅取前 **300 字** 送 Gemini（模型：`gemini-3.1-flash-lite`）
- 分類與爬取**非即時**：爬取後需等待 classify 排程或手動觸發
- 大量訊息時「待分類」會長時間偏高，屬預期行為

### 19.3 Docker 整合（D8）

```yaml
# docker-compose.yml 新增服務
discord-bot:
  build:
    context: .
    dockerfile: ./docker-files-poa/Dockerfile
  command: python manage.py run_discord_bot
  env_file: .env
  volumes:
    - .:/app
  depends_on:
    - web
  restart: unless-stopped
```

### 19.4 .env 新增變數

```
DISCORD_BOT_TOKEN=Bot_your_token_here
DISCORD_CRAWL_CHANNEL_IDS=123456789,987654321
DISCORD_NEWS_CHANNEL_ID=111222333
DISCORD_NEWS_MODEL=gemini-3.5-flash
DISCORD_CRAWL_LIMIT=100
```

---

## 20. 資料流（完整，含管線修復後）

```
[離線 Pipeline — 部署前執行，修復後支援 5 來源]
crawl_{bilibili,bahamut,ettoday,udn,gamme}_uma.py
  → data/raw/{source}_uma_raw.csv（Canonical 格式）
    → preprocess.py → data/processed/uma_combined_tokenized.csv
      → label_sentiment.py（google-genai 2.9.0）
        → data/processed/uma_news_preprocessed.csv（≥1,000 筆）
          → scripts/import_uma_data.py → db.sqlite3 (NewsData, ≥1,000 rows)
          → scripts/generate_topkey_csv.py → uma_topkey_with_category.csv
          → scripts/generate_top_character_csv.py → uma_top_character_with_category.csv

[執行期 — Django 服務中]
/  (首頁)
  └── app_character_pk: AI 新聞精選 + 平台簡介
/popularity-list/
  └── app_character_pk: 角色人氣列表（CSV PK 比較 + 聲量折線圖）

使用者輸入關鍵字
  ├── app_user_keyword: pandas CSV 聲量分析
  ├── app_user_keyword_sentiment: pandas CSV 情感分析
  ├── app_user_keyword_db: ORM 全文搜尋（支援 source 過濾）
  ├── app_user_keyword_llm_report:
  │     ├── 整合聲量 + 情感 → 組 prompt
  │     ├── provider=gemini  → google-genai 2.9.0 → gemini-3.5-flash
  │     └── provider=claude  → anthropic 0.111.0  → claude-sonnet-4-6
  ├── app_uma_top_keyword: CSV 熱門詞
  └── app_uma_top_character: CSV 熱門角色

/comment_sentiment/  （C1 修復後）
  └── 顯示 Article + ArticleEmotion 儀表板
  └── APScheduler（背景）:
        每60min → scrape_bahamut.py → Article + Comment DB
        每日02:00 → analyze_sentiment → ArticleEmotion DB

/agent/
  └── Gemini 3.5 Flash function calling
      → 6 種工具（含 read_local_document → knowledge_base/）
      → 多工具輪呼 → 自然語言答案

/rag/
  └── 啟動時載入預建 FAISS 索引（app_rag_uma/index/）
  └── gemini-embedding-001 → FAISS 相似搜尋 → Gemini 3.5 Flash 生成答案
  └── 使用者上傳 PDF → 疊加到現有索引

[O5 — YouTube]
/youtube/
  └── YouTube Data API v3（crawl_youtube management command）
  └── APScheduler: 每6h爬取、每日03:00情感標記
  └── YouTubeVideo + YouTubeComment + YouTubeQuotaLog → 情感儀表板

[D1-D8 — Discord Bot（獨立容器）]
discord-bot 容器（python manage.py run_discord_bot）
  └── crawler.py → DiscordMessage DB（增量，每30min）
  └── classifier.py → is_uma_related 標記（每60min）
  └── converter.py → DiscordMessage → NewsData（每120min）
  └── news_generator.py → DiscordNewsLog（每日08:00）

[情報站控制台 — Admin Platform]
/crawler-admin/          → Platform Health Dashboard（全平台狀態）
/crawler-admin/youtube/  → YouTube API 配額管理 + 手動觸發
/crawler-admin/discord/  → Discord Bot 管理 + 推播歷史
/crawler-admin/rag/      → RAG 索引狀態 + 一鍵重建
/crawler-admin/pipeline/ → Pipeline 分步執行 + 執行歷史

[O1-O4 — 進階 AI 系列]
/rag-agent/       → Agentic RAG（RAG + DB 雙工具 Agent）
/langchain-agent/ → LangChain ReAct Agent
/langgraph-agent/ → LangGraph StateGraph Agent
/course/          → API 介紹 + 課程說明頁

[Docker 執行期]
Browser → Nginx(:80) → Gunicorn(:8000) → Django → PostgreSQL（Docker；本機開發為 db.sqlite3）
                    ↳ /static/ → staticfiles/
entrypoint.sh:
  migrate → import_uma_data(idempotent) → build_index(if not exists) → gunicorn
discord-bot 容器 → python manage.py run_discord_bot（獨立執行）
```

---

## 21. AI 生成新聞整合設計（首頁 + 後台）

### 21.1 目標與範圍

- 參考 `umamusume-news-analysis-v1` 的「AI 生成新聞」流程，但資料輸入規格改為本專案既有 `NewsData`（多來源、既有分類與 source 欄位）。
- 前台：整合到首頁（`app_character_pk/home.html`），提供新聞主卡、摘要、來源連結與錯誤/空資料狀態。
- 後台：整合到 `crawler-admin`，新增 `AI 新聞管理` 頁面，提供生成、發布切換、刪除與清單管理。

### 21.2 資料模型（新增）

`app_user_keyword_llm_report.models.GeneratedNewsArticle`

- 查詢條件：`query`、`category`、`source`、`weeks`、`topk`
- 內容欄位：`title`、`subtitle`、`summary`、`content`、`cover_image_url`
- 引用資料：`source_chunks`、`source_links`（JSON）
- 發布流程：`status`（`draft`/`published`）、`created_by`、`created_at`、`updated_at`

### 21.3 後端服務層（最佳化）

`app_user_keyword_llm_report/services_ai_news.py`

1. 從 ORM 讀取 `NewsData`，依 `weeks/category/source/query` 篩選，避免重複落地 CSV 的 I/O。
2. 取樣來源片段（`source_chunks`）與引用連結（`source_links`），形成可追溯 context。
3. 新增查詢理解層（自然語言優先）：自動判斷 `keyword` / `natural_language` 模式，並抽取 `search_terms`（jieba + POS + stopwords）。
4. 檢索策略改為「語意降級容錯」：先用抽詞檢索；若自然語言模式結果過少，回退到時間/類別/來源範圍，避免空集合。
5. 文字模型改為「模型目錄 + model_id」路由：後端提供 Gemini/Claude 各三款模型清單（含屬性與成本標籤），前端動態拉取，避免 UI 硬編碼。
6. 若模型失敗，自動 fallback 生成保底新聞文稿，確保 API 可回應。
7. 新增封面圖生成流程：封面圖片固定使用 Gemini image model（`GEMINI_IMAGE_MODEL`），與文字 provider 解耦；即使內容由 Claude 生成，封面仍由 Gemini 生成。
8. 圖像落地至 `MEDIA_ROOT/ai_news_covers/`，回傳可直接顯示的 `cover_image_url`（`/media/...`）。
9. 若 Gemini 圖像生成失敗，依序 fallback：`photo_link` → `link`，確保前台永遠有可用封面來源。
10. 將新聞持久化為 `GeneratedNewsArticle`，供前台與後台共用。

### 21.4 API 契約（新增）

掛載於 `app_user_keyword_llm_report/urls.py`：

- `GET /userkeyword_report/api/model_options/`
  - 出參：`{items:[{id, provider, model, label, attrs, cost_label}], default_model_id, image_generation}`
- `POST /userkeyword_report/api/generate_ai_news/`
  - 入參：`query`、`category`、`source`、`weeks`、`topk`、`model_id`（相容舊參數 `provider`）、`auto_publish`
  - 出參：`{ok, news{..., query_mode, search_terms, text_model, image_model}}`
- `GET /userkeyword_report/api/latest_ai_news/?limit=1&status=published`
  - 出參：`{has_news, news:[...]}`（前台首頁使用）
- `GET /userkeyword_report/api/admin/news_list/?limit=30`
  - 出參：`{items:[...]}`（後台清單）
- `POST /userkeyword_report/api/admin/news/<id>/toggle/`
  - 功能：發布狀態切換
- `POST /userkeyword_report/api/admin/news/<id>/delete/`
  - 功能：刪除新聞

### 21.5 UI 與路由整合

- 首頁（`/`）：`app_character_pk/home.html`
  - 新增「AI 生成新聞精選」區塊，顯示最新 `published` 新聞。
  - 狀態完整：`loading` / `empty` / `error` / `result`。
- 後台（`/crawler-admin/ai-news/`）：
  - 新增 `app_crawler_admin/views.py::ai_news_management`
  - 新增 `app_crawler_admin/templates/app_crawler_admin/ai_news.html`
  - 側欄與儀表板快速入口同步整合。
  - **Discord 推播整合**（`0.5.6-alpha`）：同一頁面可觸發週報摘要推播、單篇 `GeneratedNewsArticle` 推播，並可選「生成後同步推播」。

### 21.7 Discord 推播整合（AI 新聞頁）

**服務層** `app_crawler_admin/discord_push.py`

| 函式 | 說明 |
|------|------|
| `get_discord_push_status()` | Bot 狀態、GuildSetting 推播目標、近期 `DiscordNewsLog`、進行中 `news` 任務 |
| `format_article_for_discord(article)` | 將 `GeneratedNewsArticle` 格式化為 Discord Markdown 文字 |
| `push_text_to_guilds(bot, text, …)` | 依 `GuildSetting` 推播至各伺服器 `news_channel_id` |
| `push_article(bot, article_id)` | 推播指定 AI 新聞稿 |
| `push_weekly_summary(bot)` | 產生週報摘要後推播（與排程相同資料來源） |

**API**（掛載於 `app_crawler_admin/urls.py`）

- `GET /crawler-admin/api/ai-news/discord-status/`
- `POST /crawler-admin/api/ai-news/discord-push-weekly/` — 觸發 `DiscordTaskRun(task_type=news)`，worker 走 `scheduler._run_per_guild_news(force_send=True)`
- `POST /crawler-admin/api/ai-news/discord-push-article/` — body：`{article_id, guild_ids?}`；worker 走 `discord_push.push_article`
- `POST /crawler-admin/api/ai-news/discord-push-articles/` — body：`{article_ids[], guild_ids?}`；單一 `news` 任務批次推播多篇文章

**任務銜接**

- `_launch_discord_task(..., news_opts={mode, article_id?, article_ids?, guild_ids?})` 於 thread 啟動前寫入 `_PENDING_NEWS_OPTS[run_id]`
- `news` worker 讀取 opts：`weekly`（預設）/ `article` / `articles`（批次）
- 與 Discord 控制台共用同一 `news` 任務類型，避免重複並發（同一時間僅一個 `news` 任務）

**UI**

- Discord 推播卡片：Bot 狀態、推播目標、近期紀錄、週報推播按鈕、連結至 Discord 控制台
- 新聞清單每列「推播至 Discord」
- 新聞清單支援勾選多篇後「批次推播勾選新聞」（預設推播到所有已設定伺服器）
- 生成參數「生成後同步推播至 Discord」勾選框
- 模型下拉由 `/userkeyword_report/api/model_options/` 動態載入，模型資訊區採用膠囊標籤（`pill`）呈現供應商 / 屬性 / 成本 / 圖像供應商狀態，避免純文字資訊不易掃讀
- 生成提示回顯本次使用模型，便於編輯台校對品質與成本策略

### 21.6 驗收要點

- [ ] `python manage.py check` 無錯誤
- [ ] 首頁可顯示最新已發布新聞（或正確顯示空狀態）
- [ ] 後台可用參數生成新聞，且可切換發布/刪除
- [ ] `GeneratedNewsArticle` migration 可正常遷移
- [ ] `provider=claude` 時仍可產生封面圖（固定走 Gemini image）
- [ ] `cover_image_url` 可由 `/media/ai_news_covers/*` 正常存取
- [ ] 自然語言輸入可自動切換 `query_mode=natural_language` 並回傳 `search_terms`
- [ ] AI 新聞頁可觸發週報推播與單篇推播，且 `DiscordNewsLog` 有對應紀錄
- [ ] AI 新聞頁模型清單由 API 動態載入，且可選 Gemini/Claude 各三款
- [ ] AI 新聞頁可批次推播勾選文章（多篇）至所有目標伺服器

---

## 22. 全站 UI 設計系統重構（2026-06-23）

> 依 `ui-redesign-plan.md` 與 `美學設計概要` 實作，目標為「專業、美觀、人性化」統一視覺。

### 22.1 主要變更檔案

- `static/css/design-system.css`
- `static/js/theme.js`
- `static/js/ui-fx.js`
- `templates/base.html`
- `app_crawler_admin/templates/app_crawler_admin/base_admin.html`

### 22.2 主題與配色契約

- 採語意化 Token（`--color-*`）統一管理堇紫/淺紫/金/白調色盤。
- 支援三態主題：
  - `light`
  - `dark`
  - `system`（跟隨 OS `prefers-color-scheme`）
- 主題偏好儲存鍵：`localStorage['uma-theme']`（前後台共用）。

### 22.3 動態與互動規範

- 動態背景：以 `.mesh-bg` 實作滿版 Animated Mesh Gradient。
- PWM 呼吸燈：主要按鈕 hover 與 `btn-query-ready` 使用金/淺紫 glow 動效。
- 卡片互動：hover 上浮、陰影增強、平滑過渡。
- 無障礙：`prefers-reduced-motion: reduce` 時停用高動態動畫。

### 22.4 基底模板整併策略

- 前台與控制台改為共享同一組 CSS/JS，避免雙套設計系統分裂。
- 前台與控制台皆先在 `<head>` 內預先套用主題，避免 FOUC（首次閃白/閃黑）。
- Bootstrap CDN 統一到 5.3.3（原先前台/控制台為 5.1.3）。

### 22.5 視覺與可讀性要求

- 表格與列表統一加入防重疊規範（`word-break`、`overflow-wrap`、`table-responsive`）。
- 下拉選單、表單、卡片、footer 全面套用玻璃擬態與留白規範。
- 主要入口頁移除馬 emoji，符合美學要求「不要有馬的 Emoji」。

## 23. 導覽、搜尋、動效與圖表規範（2026-06-23 增補）

### 23.1 導覽列（Top Navigation）

- 結構：`header.site-nav > .container > nav.navbar`，背景滿版至畫面邊界、內容置中於 `.container`。
- 分類精簡為 4 組：熱門分析 / 關鍵詞檢索 / 情感儀表板 / AI 功能。
- 頂層不再放「情報站控制台」「平台介紹」，改置於頁尾「站台導覽」區。
- 導覽文字縮小（`.site-nav .nav-link` 約 0.82rem）。
- 右側 `.nav-actions` 依序為：搜尋框、主題切換鈕。

### 23.2 站內搜尋

- 導覽列搜尋以 `GET` 提交至 `announcement_list`（參數名 `q`），沿用既有視圖與 `GameAnnouncement` 全文檢索，不另立 API。
- 搜尋落地頁 `app_dashboard/announcement_list.html` 一律使用設計系統樣式，禁止依賴已移除的 `btn-purple`／Bootstrap Icons。

### 23.3 動效規範

- 下拉選單：`.dropdown-menu` 採透明度 + 位移過渡（滑入＋淡入）。
- 區塊捲動顯示（從無到有，禁止「先顯示→淡出→再淡入」閃爍）：
  - 僅套用前台主內容（`html.reveal-ready #pageContent > [class*="col-"]`）；**控制台 `app_crawler_admin` 全頁不套用區塊淡入**。
  - `reveal-ready` 由前台 `templates/base.html` 的 `<head>` 內聯腳本於首次繪製前加到 `<html>`（僅在非 `prefers-reduced-motion` 且支援 `IntersectionObserver` 時）。
  - `ui-fx.js` 僅對前台選擇器加 `.in-view`，並保留 5 秒保險顯示（`revealAll`）與不支援 IO 時降階；`prefers-reduced-motion` 由媒體查詢強制顯示。

### 23.4 圖表規範

- 圖表容器一律使用固定高度（`.chart-fixed` 320px、`.chart-tall` 380px），並設 `maintainAspectRatio: false`，避免大塊圖配小字與互相擠壓。
- 字級下限：座標軸 ticks ≥ 12px、圖例/標題 ≥ 13px；折線使用 `lineTension` 平滑與漸層填色，圖例採 `usePointStyle`。
- 顏色一律自主題 Token 取得（`--color-positive/negative/neutral-tone/text-secondary`），確保深淺主題皆可讀。

### 23.5 主題切換鈕位置

- 前台：置於導覽列右側 `.nav-actions`（非固定浮層）。
- 控制台：置於側欄底部（`.sidebar` 為 flex column，鈕 `margin-top:auto`），避免覆蓋主內容操作按鈕。

### 23.6 前台/後台職責邊界

- 留言情感儀表板等前台頁面不得出現排程／任務手動控制；相關控制統一回歸 `crawler-admin` 後台。

---

## 24. 主站 3D 浮動 AI 虛擬客服（2026-06-24）

### 24.1 UI 掛載與資產

- 模型檔：`static/app_dashboard/vrm/1077_Narita_Top_Road.vrm`
- 腳本：`static/app_dashboard/js/ai-vrm-assistant.js`
- 樣式：`static/app_dashboard/css/ai-vrm-assistant.css`
- 全站掛載：`templates/base.html` 固定容器 `#ai-vrm-assistant-root`
- DOM 層級：`canvas-wrap` 內含 3D 畫布、對話泡泡（上方）與快捷提問 presets（底部疊加）；聊天輸入列獨立於 `canvas-wrap` 下方。

### 24.2 渲染與光源

- 使用 `Three.js`（CDN）與 `@pixiv/three-vrm`（CDN），**以 import map 統一單一 THREE 實例**。
- renderer 設定：
  - `alpha: true`
  - `antialias: true`
  - `setClearColor(..., 0)`（透明背景）
- 光源組合（三點打光，營造接近 Live2D 的二次元立體感）：
  - `AmbientLight`（整體底光，0.75）
  - `HemisphereLight`（天空/地面補色，0.45）
  - `DirectionalLight` 主光（斜前上方右側 `(2,2,2)`，2.2，加強明暗對比）
  - `DirectionalLight` 補光（另一側冷光，0.55，柔化陰影死角）
  - `DirectionalLight` 輪廓光（後上方暖光，0.7，勾勒髮絲/肩線邊緣）

### 24.2.1 看不到模型的已知元兇與對策（落地經驗）

- **雙 THREE 實例**：`three` 與 `three-vrm` 必須共用同一份 THREE（用 import map），否則 MToon 材質畫不出來。
- **視錐裁切**：載入後對 `vrm.scene` 全部 `frustumCulled = false`，避免 SkinnedMesh 被誤剔除。
- **大頭特寫陷阱**：框景**禁止**用 `getNormalizedBoneNode()` 的「頭/腰距離」推距離——normalized 屬 three-vrm 內部正規化空間，距離被壓縮會算出過近距離。
- **全黑陷阱（MMD 轉檔模型）**：框景**禁止**用 `THREE.Box3` 量全身高——第 0 幀 SpringBone 物理未穩定，邊界會被量到極端異常巨大值，相機被推到數萬單位外導致全黑。
- **正解**：`updateMatrixWorld(true)` 後，取頭骨**絕對高度**（防呆夾擠 `0.5<y<2.5`，否則退回 `1.4`），對焦 `head_y-0.2`，採**固定安全距離 `0.9`**（不做 FOV 反推）。
- **面向**：VRM0 需 `VRMUtils.rotateVRM0` 轉正面向鏡頭。

### 24.3 LookAt 視線跟隨

- 模型載入後指定 `vrm.lookAt.target`。
- 監聽全域 `mousemove`，將 2D 滑鼠座標轉為場景 3D 目標座標。
- 目標點偏移範圍依模型尺度（`model_scale_ref`）等比放大（0.9 / 0.7 × scale），追視更明顯。
- 目標點使用 `lerp` 平滑更新，提升自然感並避免抖動。
- LookAt、表情、骨骼皆需在 `requestAnimationFrame` 迴圈中呼叫 `vrm.update(delta)` 才會生效。

### 24.4 對話流程與 API

- 快捷提問 presets 以絕對定位疊加於 3D 畫布底部（藥丸按鈕 + 底部漸層底襯）；輸入框 + 發送鈕位於 canvas 下方獨立區塊，採玻璃擬態風格。
- 發送時泡泡顯示 loading（「思考中...」）。
- 透過 `fetch` 呼叫 `POST /agent/chat/`：
  - `Content-Type: application/json`
  - `X-CSRFToken`（由 cookie 取得）
  - payload：`{"message": "..."}`
- 成功：泡泡顯示 AI 回覆文字。
- 失敗：泡泡顯示 `HTTP status` 或可判讀錯誤訊息。

### 24.5 待機姿勢與表情互動

- **⚠ humanoid 骨骼位移地雷**：此 PMX→VRM 轉檔模型 humanoid 對應整體位移一節（`leftUpperArm` 槽實為肩膀、`leftLowerArm` 槽才是大臂、`leftHand` 槽是前臂、`head` 槽是緞帶骨）。詳見 `scripts/export_vrm_info.py` 導出資料與 `3d-ai-virtual-cs-spec.md §6.5`。
- **待機站姿（依位移修正）**：「放下大臂」轉 `lowerArm` 槽、「彎手肘」轉 `hand` 槽、肩膀槽保持不動（避免從肩關節硬拉造成網格塌陷）。
- **視線跟隨（依位移修正）**：humanoid `head` 槽是緞帶骨，改直接操作 `getObjectByName('Head')` 的真實頭骨，在世界空間疊加 yaw/pitch/roll 再換算回 local，`slerp` 平滑跟隨。採局部座標追視（容器中心 + 半徑 400px，半徑外平滑回正）。
- **互動狀態機**：`idle / welcoming / listening / talking` 四態，全部以 `lerp` 平滑過渡。迎賓揮手、傾聽前傾側傾、對話偽唇形同步（`aa`/`ih` 擺動）。預設提問藥丸按鈕點擊即提問。詳見 `plan/3d-ai-vrm-interactive-statemachine-plan.md` 與 `3d-ai-virtual-cs-spec.md §6.6 / §7`。
- **待機呼吸**：每幀對 `chest` 骨骼施加極小幅度 sin 起伏（±0.022 rad），避免角色像靜止立繪。
- **resting 微笑**：載入即套用 `Happy = 0.18`（刻意壓低，避免 joy 表情把眼睛笑瞇而看不出視線跟隨），靜態時仍有親和表情。
- **回覆強化**：收到回覆時短暫提升 `Happy = 0.85`，約 1.4 秒後還原回 resting 值（不歸零，避免變回無表情）。
- 使用 VRM expression manager；站姿一次性設定，呼吸/表情/視線於動畫迴圈持續更新。

### 24.6 後端相容策略（`app_agent_uma`）

- `/agent/chat/` 同時支援：
  - 既有表單 POST（原本聊天頁）
  - 新增 `application/json` POST（主站 3D 客服）
- 回傳契約：
  - 成功：`{"reply":"...", "message":"..."}`
  - 失敗：`{"error":"..."}` + 合理 HTTP status

---

## 25. Discord 控制台可觀測性設計（2026-06-24）

### 25.1 任務執行模型

新增 `app_discord_bot.DiscordTaskRun`，統一紀錄控制台手動任務：

- `task_type`: `crawl/classify/convert/news`
- `status`: `pending/running/success/failed/cancelled`
- `progress_pct`: 0~100
- `summary` / `error_message`
- `result_json`: 結果摘要（新增筆數、成功/失敗數）
- `log_text`: 完整執行日誌

此模型使任務生命周期可被輪詢、追蹤、稽核。

### 25.2 Discord 任務 API 契約（crawler-admin）

```
POST /crawler-admin/api/discord/task/start/
Body: {"task":"crawl|classify|convert|news"}
Response: {"status":"started|already_running","run":{...}}

GET /crawler-admin/api/discord/task/status/?run_id=<id>
Response: {"run": {...}} 或 {"runs":[...]}

GET /crawler-admin/api/discord/task/<run_id>/log/?offset=<n>
Response: {"lines":[...], "total":123, "run":{...}}
```

設計重點：
- 同類任務單飛（single-flight）：同類執行中時不重複啟動
- 前端以 polling 方式讀取狀態與增量 log

### 25.3 手動任務執行策略

- `classify` / `convert`：在背景執行緒直接呼叫既有服務模組
- `crawl` / `news`：建立短生命週期 Discord Client 連線，完成任務後自動關閉
  - 避免「必須先常駐 bot process 才能手動操作」的耦合
  - 同時保留既有常駐 Bot 排程機制

### 25.4 訊息查閱 API 擴充

`GET /crawler-admin/api/discord/recent_messages/` 新增：

- 篩選：`keyword`, `date_from`, `date_to`, `guild_id`, `channel_id`, `classify`
- 排序：`sort_by`, `sort_dir`
- 分頁：`limit`, `page`
- 回傳：`total`, `total_pages`, `guild_name`, `is_converted`, `created_at`
- 單筆查詢：`msg_id`（用於詳情 Modal 補查）

**訊息詳情 Modal（控制台 UI）**

- 列表仍顯示截斷預覽；點擊列或「查看」開啟 Modal 顯示完整內容
- 中繼資料：訊息 ID、發送/爬取時間、伺服器、頻道、作者、分類、NewsData 狀態
- 快捷操作：複製內容、複製 ID、`https://discord.com/channels/{guild}/{channel}/{msg}` 跳轉

新增刪除端點：

```
POST /crawler-admin/api/discord/messages/delete/
Body:
  {"msg_ids":[...]}                              # 刪除勾選
  或
  {"delete_filtered":true, ...filters...}       # 刪除篩選結果
```

### 25.5 Discord 資料併入分析鏈

`app_discord_bot/converter.py` 將 `DiscordMessage -> NewsData` 時明確標記：

- `source='discord'`
- `category='Discord'`

並在統計 API (`api_stats` / `api_source_stats`) 回傳來源聯集，確保 Discord 可在分析儀表板被辨識與統計。

---

## 26. UMA Info Portal — 推播設定集中化與頻道權限管控（2026-06-24）

### 26.1 設計原則

| 職責 | 管理端 |
|------|--------|
| 推播時程（頻率、整點） | **控制台後台**（`/crawler-admin/discord/`） |
| 推播目標頻道 / Ping 身分組 / 語氣 | **Portal 伺服器管理頁**（`/uma-info/servers/<guild_id>/manage/`） |
| 頻道讀取範圍（爬取來源） | Portal 伺服器管理頁 |

### 26.2 頻道權限快取

`GuildChannelCache` 新增：

- `bot_can_read (bool, default=True)` — `view_channel AND read_message_history`
- `bot_can_send (bool, default=True)` — `view_channel AND send_messages AND embed_links`

每次 `run_discord_bot` 同步頻道時，呼叫 `ch.permissions_for(guild.me)` 計算實際權限並寫入。

下拉清單過濾規則：

| 場景 | 使用欄位 |
|------|---------|
| 爬取頻道（single / advanced 規則） | `bot_can_read=True` |
| 推播頻道選擇 | `bot_can_send=True` |

### 26.3 推播頻道確認 Embed

當 `news_channel_id` 在 Portal 變更時：

1. `api_guild_settings_save` 儲存後，自動呼叫 `_send_news_channel_confirm_embed()`
2. Bot 向新頻道發送 Embed（Discord 藍色 `#5865F2`），內含：伺服器名稱、推播開關、語氣、Ping 身分組、Footer 指引
3. Bot 離線時前端顯示「Bot 未在線，確認訊息將於上線後補發」提示

獨立端點：
```
POST /uma-info/api/guilds/<guild_id>/confirm-news-channel/
Response: {"status":"sent"} 或 {"status":"bot_offline"}
```

### 26.5 伺服器統計 API（總覽即時刷新）

規劃中的 `GET /uma-info/api/guilds/<guild_id>/stats/` 已落地，供伺服器管理頁總覽與統計分頁動態更新。

```
GET /uma-info/api/guilds/<guild_id>/stats/
Response: {
  "guild_id": "...",
  "guild_name": "...",
  "stats": {
    "msg_count": 3863,
    "uma_count": 19,
    "pending_count": 3800,
    "nonuma_count": 44,
    "news_count": 0,
    "converted_count": 0,
    "channel_count": 345,
    "uma_pct": 0.5,
    "last_message_at": "2024-04-20 13:46",
    "refreshed_at": "2026-06-24 19:30:00"
  }
}
```

- 統計依 `DiscordMessage.guild_id` 與 `DiscordNewsLog.guild_id` 彙整，**每個伺服器獨立計算**
- 共用邏輯：`app_uma_info_portal/guild_stats.py` → `compute_guild_stats()`
- 前端：頁面載入 + 切換總覽/統計分頁 + 每 30 秒輪詢 + 手動「↻ 更新統計」

**注意**：若某伺服器總覽仍為 0，請確認：
1. 爬取任務是否針對該 `guild_id` 完成（控制台任務日誌可見 `▶ [N/M] 伺服器名稱`）
2. 是否誤開另一個已安裝但尚未爬取的伺服器管理頁

### 26.4 Migration

`app_uma_info_portal 0002_channel_bot_permissions`：新增 `bot_can_read`、`bot_can_send` 至 `GuildChannelCache`，已套用。

### 26.6 UMA Info 頂部導覽列（2026-06-25）

`app_uma_info_portal/templates/app_uma_info_portal/base_portal.html` 的 `.portal-nav` 為 UMA Info 專用頂部導覽，與主站 `templates/base.html` 分離。

**頂層項目（左側 `.nav-links`）**：

| 項目 | 連結 | 說明 |
|------|------|------|
| 品牌 | `{% url 'app_uma_info_portal:home' %}` | UMA Info 首頁 |
| 功能介紹 | 首頁 `#features` 錨點 | 產品功能說明 |
| 回主站 | `/` | 返回賽馬娘資訊平台主站 |

**右側 `.nav-right`**：主題切換鈕；已登入顯示 Discord 頭像／伺服器列表入口與登出，未登入顯示「以 Discord 登入」。

**刻意不放於頂層導覽**：

- **情報站控制台**（`/crawler-admin/`）：平台管理員專用，與 Discord 伺服器管理員使用的 UMA Info Portal 職責分離；一般 Portal 使用者不應從頂部導覽進入後台。

**頁尾**：可保留「賽馬娘資訊平台」「UMA Info」等站台連結；控制台入口若需保留，僅置於頁尾次要連結，不置於頂部導覽。

### 26.7 Discord Bot 回應與 UMA Info UI — 禁用馬 Emoji（2026-06-25）

依全站美學規範「不要有馬的 Emoji」，**Discord Bot 回覆與 UMA Info Portal 介面**一律不得使用 🐴、🐎、🏇 等馬相關 emoji。

| 範圍 | 規範 |
|------|------|
| Bot @mention 問答回覆 | **純文字** `message.reply()`；超過 1900 字分段送出，不使用 Embed（`run_discord_bot.py`） |
| Portal 品牌圖示 | 使用 Discord 藍漸層 **「U」字標**（`.brand-icon`、`.dm-bot-avatar`、`.cta-icon`），不使用馬 emoji |
| 邀請按鈕 | 搭配 Discord 官方 SVG 圖示 + 文字，不使用馬 emoji |
| 主站導覽 UMA Info 連結 | 純文字 `UMA Info`，不使用馬 emoji |

**允許**：📰、🤖、⚙️、📡、💡 等非馬類功能型 emoji 可保留，與 §22.5 主站規範一致。

**驗收**：檢查 `/uma-info/` 首頁 mockup、CTA、導覽列皆無馬 emoji；Discord 中 @UMA Info 回覆為一般文字訊息（非 Embed 卡片）。

### 26.8 @UMA Info AI 問答回覆格式（2026-06-25）

`handle_ai_chat`（`run_discord_bot.py`）在一般情形下以**純文字**回覆使用者 @mention：

- 使用 `message.reply(answer)`，與一般 Discord 對話一致
- 回答超過 1900 字時，首段以 `reply` 送出，其餘以 `channel.send` 分段（Discord 單則上限 2000 字）
- **不使用 Embed**（推播確認、新聞摘要等系統推播仍可使用 Embed，與問答分離）

**驗收**：在 Discord 頻道 @UMA Info 提問，Bot 回覆為一般文字泡泡，非藍色 Embed 卡片。

### 26.9 Discord 斜線指令 — 頻道讀取範圍與推播目標（2026-06-25）

將 UMA Info Portal「頻道讀取範圍」「推播目標」設定能力移植至 Discord 斜線指令，供伺服器管理員在 Discord 內直接操作，無需開啟官網。

**權限**：所有指令預設 `default_permissions=administrator`；執行時再次檢查 `interaction.user.guild_permissions.administrator`，非管理員以 ephemeral 拒絕。

**指令群組**（`app_discord_bot/slash_commands.py`，Bot `on_ready` 時 `tree.sync()`）：

| 群組 | 子指令 | 對應 Portal 功能 |
|------|--------|------------------|
| `/read-scope` | `view` | 查看讀取範圍 |
| `/read-scope` | `set scope [channel]` | 設定 all / announcements / single / advanced |
| `/read-scope` | `rule-add` / `rule-remove` / `rule-list` | 進階 Allow/Deny（`GuildChannelRule`） |
| `/news-target` | `view` | 查看推播目標 |
| `/news-target` | `set channel enabled tone ping_role` | 推播頻道、開關、語氣、Ping 身分組 |
| `/news-target` | `clear` | 清除推播頻道 |

**資料層**：斜線指令與 Portal API 共用 `app_uma_info_portal/guild_settings_service.py` 的 `update_guild_setting_fields()`，寫入 `GuildSetting` + `GuildSettingAudit`；推播頻道變更時同 Portal 觸發確認 Embed。

**推播頻道驗證**：`set channel` 前檢查 Bot 對目標頻道具備 `view_channel`、`send_messages`、`embed_links`。

**驗收**：
- 非管理員執行斜線指令 → ephemeral 權限不足
- 管理員 `/read-scope set` → 爬取任務依新 `read_scope` 運作
- 管理員 `/news-target set channel:#xxx` → Portal 同伺服器設定同步、推播頻道收到確認 Embed

### 26.10 @UMA Info 圖片讀取與分析（2026-06-25）

`@UMA Info` 問答支援**多模態輸入**：使用者 @mention 時可附帶圖片附件，Bot 下載後以 Gemini 視覺能力分析並以純文字回覆。

**實作**（`app_discord_bot/ai_chat.py`）：
- `collect_message_images(message)`：非同步下載 `message.attachments` 中的圖片
- `generate_ai_answer(question, guild_id, images)`：以 `Part.from_bytes` 組成多模態 `Content` 送 `UMA_CHAT_MODEL`
- 觸發條件：`@UMA Info` +（文字 **或** 圖片附件）；僅附圖無文字時使用預設提示「請分析這張圖片…」

**限制**：
| 項目 | 值 |
|------|-----|
| 支援格式 | PNG / JPEG / WEBP / GIF |
| 單張上限 | 4 MB |
| 每則訊息最多 | 4 張 |
| 模型 | `UMA_CHAT_MODEL`（需支援 vision，預設 `gemini-3.1-flash-lite`） |

**驗收**：在 Discord @UMA Info 並附上遊戲截圖，Bot 能描述圖中內容並以繁體中文回覆。

### 26.11 Discord 推播路徑一致性與 async 安全修正（2026-06-25）

針對 `/crawler-admin/ai-news/`「單篇推播 / 批次推播 / 週報推播」失敗問題，補齊以下設計：

1. **Web 手動推播與 Bot 排程推播一致**  
   `app_crawler_admin/discord_push.py` 的 `push_text_to_guilds()` 與 `app_discord_bot/scheduler.py` 同步採用：
   - `bot.get_channel(channel_id)`（快取命中）
   - 若為 `None` 則 `await bot.fetch_channel(channel_id)`（API 後援）

2. **async context 禁止直接 ORM 的修正**  
   在 async 函式中，所有 Django ORM 存取改用 `sync_to_async(..., thread_sensitive=True)` 包裝，避免：
   `You cannot call this from an async context - use a thread or sync_to_async.`
   - `discord_push.push_article()`：讀取 `GeneratedNewsArticle`
   - `discord_push.push_text_to_guilds()`：讀取 `GuildSetting`、寫入 `DiscordNewsLog`
   - `scheduler._run_per_guild_news()`：讀取 `GuildSetting`/`DiscordBotConfig`、寫入 `DiscordNewsLog`

3. **頻道 ID 與頻道型別防呆**  
   - `news_channel_id` 非數字時記錄 failed 並寫明 `無效頻道 ID`
   - 頻道不支援 `send()`（如論壇/分類）時記錄 failed 並跳過，不中斷整批推播

4. **Bot 狀態偵測一致化（PID 自管理）**  
   `run_discord_bot.py` 啟動時自寫 `discord_bot.pid`，結束時自清，避免「非控制台啟動」時被誤判離線。

**驗收**：
- `/crawler-admin/ai-news/` 單篇推播：`DiscordTaskRun(task_type='news')` 狀態為 success，且 `DiscordNewsLog` 新增 sent 記錄
- `news_channel_id` 非法或頻道型別不符時，不會整批崩潰，`DiscordNewsLog` 有 failed 原因
- Bot 以命令列啟動時，控制台 `api_discord_bot_status` 仍顯示 running

---

## 27. Discord 爬取任務 — 細粒度進度與結構化日誌（2026-06-24）

### 27.1 設計目標

使 `/crawler-admin/discord/` 中的「爬取頻道訊息」任務，在執行期間能即時顯示：
- 已連線 Bot 帳號 + 加入伺服器總數（預報工作量）
- 目前正在處理第幾個伺服器（N/M）及其讀取範圍
- 每個頻道爬取結果（+N 筆 / 無讀取權限 / 錯誤）
- 累積新訊息數與頻道進度

### 27.2 後端：async callback 機制

`crawler.py` 的三層函式均新增可選 async callback 參數：

```python
async def crawl_channel(bot, channel_id, guild_id='', log_fn=None) -> int
async def crawl_guild(bot, guild, log_fn=None, progress_fn=None, guild_index=0, guild_total=1) -> int
async def crawl_all_channels(bot, log_fn=None, progress_fn=None) -> int
```

- `log_fn(msg: str)` — 寫入一行日誌（async，由 `sync_to_async(_append_task_log)` 包裝）
- `progress_fn(pct: int, summary: str)` — 更新 `DiscordTaskRun.progress_pct` 與 `summary`（同上）

進度百分比分配：
- 0–10%：啟動 / 建立 Discord 連線
- 15%：連線成功
- 15–85%：爬取（70% 均分給所有伺服器，再細分給每個頻道）
- 90–100%：後端寫入結果、任務完成

### 27.2.0 任務啟動防重複與殘留清除

`_launch_discord_task(task_type, triggered_by, news_opts?)` 邏輯：

1. 查詢 DB 是否有同類型 `pending`/`running` 任務
2. 若找到：
   - 透過 `_ACTIVE_WORKERS[id].is_alive()` 確認 worker 仍存活
   - **存活** → 回傳既有任務，防止重複觸發
   - **已死或不存在**（Django 重啟後殘留）→ 將舊任務標記為 `failed`、清除對應 `_CANCEL_FLAGS` 旗標，繼續建立新任務
3. 建立新 `DiscordTaskRun`、啟動 daemon thread、寫入 `_ACTIVE_WORKERS`

> **設計依據**：Django 重啟後 `_ACTIVE_WORKERS` 清空，但 DB 仍可能殘留 `running` 狀態的紀錄。若不自動清除，前端會拿到舊任務並顯示舊日誌（包含取消記錄），造成誤判。

### 27.2.1 任務取消機制

支援任務類型：`crawl` / `classify` / `convert` / `news`

取消流程採「旗標 + 背景監看 + 例外」三重保障：

1. **前端** 點擊「⏹ 停止任務」→ `POST /api/discord/task/<run_id>/cancel/`
2. **`api_discord_task_cancel`**
   - 設定 `_CANCEL_FLAGS[run_id] = True`
   - 若 `_ACTIVE_WORKERS` 中無對應執行緒（殘留 `running`）→ 立即 `_finalize_cancelled()`，回傳 `status: cancelled`
   - 否則更新 `summary: 正在取消…` 並回傳 `run` 物件
3. **Discord 連線任務（crawl / news）**：`_watch_cancel()` 背景協程每 0.4 秒檢查旗標，觸發時 `bot.close()` 中斷 `bot.start()`（含連線等待階段）
4. **爬取迴圈**：`cancel_fn()` 於每個伺服器 / 頻道迭代前檢查 → `raise CrawlCancelledError`
5. **分類任務**：`run_classifier(cancel_check=...)` 於 Layer 1 逐則、Layer 2 每批次前檢查；取消時保留已完成分類
6. worker `except CrawlCancelledError` → `_finalize_cancelled()` → `status='cancelled'`
7. **前端** 收到取消回應後立即重設按鈕、加速輪詢（1 秒）直到 `cancelled`

```
POST /crawler-admin/api/discord/task/<run_id>/cancel/
Response:
  {"status":"cancel_requested","run_id":123,"run":{...}}   # worker 執行中
  {"status":"cancelled","run_id":123,"run":{...}}          # worker 不存在，已強制取消
  {"error":"任務狀態為 success，無法取消"} (400)
```

### 27.3 前端：即時統計欄與彩色日誌

`discord.html` 進度區新增：

**Stats Strip（任務執行中顯示）**
- 伺服器：`N / M`
- 頻道：`A / B`
- 累積新訊息：`+C 筆`
- 數值從 `run.summary` 字串以正則解析，每次 poll 更新

**日誌行著色規則**：

| 樣式 class | 顏色 | 觸發條件 |
|---|---|---|
| `log-hdr` | 藍粗體 | `▶` 開頭（伺服器標頭） |
| `log-ok` | 綠色 | `✅` / `✓` |
| `log-err` | 紅色 | `❌` / `✗` / 包含「失敗/error」 |
| `log-warn` | 黃色 | `⚠` / `⏳` / 包含「略過/警告」 |
| `log-inf` | 藍色 | `↳` / `[` / `Bot 已連線` |
| `log-sub` | 暗灰 | 包含「無讀取權限/無法存取」 |

**自動捲動開關**：預設開啟，使用者可暫停以手動瀏覽上方日誌。
