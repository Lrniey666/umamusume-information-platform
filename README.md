<div align="center">

# 🥕 賽馬娘資訊平台
### Uma Musume Information Platform

<p>
  <img src="https://img.shields.io/badge/版本-0.6.43--alpha-blueviolet?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white" alt="django">
  <img src="https://img.shields.io/badge/Docker-支援-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="docker">
  <img src="https://img.shields.io/badge/AI-Gemini%20%2B%20Claude-FF6B35?style=for-the-badge" alt="ai">
</p>

<p>
  <strong>以賽馬娘 Pretty Derby 遊戲社群為主題，整合多平台輿情爬蟲、AI 分析報告、<br>LLM Agent、RAG 知識庫與 Discord Bot 的完整公眾輿論分析平台。</strong>
</p>

---

</div>

## 📋 目錄

- [專案簡介](#-專案簡介)
- [功能總覽](#-功能總覽)
- [技術架構](#-技術架構)
- [技術選型](#-技術選型)
- [資料來源](#-資料來源)
- [路由總表](#-路由總表)
- [快速啟動](#-快速啟動)
- [Docker 部署](#-docker-部署)
- [環境變數設定](#-環境變數設定)
- [專案結構](#-專案結構)
- [版本紀錄](#-版本紀錄)

---

## 🎯 專案簡介

本平台為**公眾輿論分析（Public Opinion Analysis, POA）**課程期末專案，以**賽馬娘 Pretty Derby** 玩家社群討論作為資料集，建構一套涵蓋完整 AI 應用技術棧的輿情分析系統。

### 核心目標

| 層次 | 說明 |
|------|------|
| **技術完整性** | 涵蓋 LLM 報告、留言情感分析、Agentic AI、RAG 知識庫、Docker 部署 |
| **主題一致性** | 全站以馬娘遊戲輿情為核心，資料、分析邏輯與 AI Prompt 均圍繞社群討論 |

### 平台數據規模

<div align="center">

| 📰 資料來源 | 💬 公告筆數 | 🤖 AI 引擎 | ⚡ 更新頻率 | 🎮 分析角色 |
|:---:|:---:|:---:|:---:|:---:|
| 6+ 平台 | 1,000+ 筆 | Gemini + Claude | 即時追蹤 | 全馬娘角色 |

</div>

---

## ✨ 功能總覽

### 🏠 首頁與內容展示

| 功能 | 路由 | 說明 |
|------|------|------|
| **AI 新聞精選首頁** | `/` | AI 生成新聞封面橫幅、毛玻璃卡片、平台功能導覽 |
| **賽馬娘人氣列表** | `/popularity-list/` | 角色人氣排行、多角色評論聲量折線圖 PK |
| **平台介紹頁** | `/introduction/` | 技術架構、資料來源、功能截圖完整說明 |
| **課程技術說明** | `/course/` | w12–w16 課程核心技術對照說明 |

### 📊 輿情分析

| 功能 | 路由 | 說明 |
|------|------|------|
| **關鍵字聲量分析** | `/userkeyword/` | 自訂關鍵詞在各類別的出現次數與時間趨勢 |
| **全文關聯分析** | `/userkeyword_assoc/` | 關鍵詞共現關係視覺化 |
| **關鍵詞情感分析** | `/userkeyword_senti/` | 特定詞彙正/負/中性情感分布折線圖 |
| **全文 DB 搜尋** | `/userkeyword_db/` | ORM 全文檢索公告文章 |
| **熱門關鍵詞排行** | `/uma_top_keyword/` | 5 大類別 Top-K 高頻詞橫式長條圖 |
| **熱門角色排行** | `/uma_top_character/` | 各類公告中馬娘角色曝光排行 |
| **關鍵詞相關性分析** | `/correlation/` | 詞頻相關係數矩陣熱力圖 |
| **公告儀表板** | `/dashboard/` | DB 搜尋、公告詳情、情感分數視覺化 |

### 🧠 AI 分析報告

| 功能 | 路由 | 說明 |
|------|------|------|
| **雙模型 AI 報告** | `/userkeyword_report/` | Gemini 3.5 Flash / Claude Sonnet 4.6 自選，生成 500 字+ Markdown 報告 |
| **留言情感儀表板** | `/comment_sentiment/` | APScheduler 排程分析、六維情緒圓餅圖（歡呼/開心/混亂/傻眼/憤怒/難過） |

### 🤖 Agentic AI

| 功能 | 路由 | 說明 |
|------|------|------|
| **馬娘 Agentic 助理** | `/agent/` | 6 種 Function Calling，自然語言多輪問答 |
| **RAG 知識庫問答** | `/rag/` | FAISS 持久索引，PDF/MD 上傳，含引用來源回答 |
| **Agentic RAG** | `/rag-agent/` | 語意搜尋 + DB 精確查詢雙工具自動路由 |
| **LangChain ReAct Agent** | `/langchain-agent/` | Thought → Action → Observation 推理迴圈展示 |
| **LangGraph StateGraph Agent** | `/langgraph-agent/` | StateGraph 多步驟複雜 Agent 框架展示 |

### 📺 多平台整合

| 功能 | 路由 | 說明 |
|------|------|------|
| **YouTube 影片情感** | `/youtube/` | YouTube Data API v3，影片留言情感 + 週聲量趨勢 |
| **Discord Bot** | `/discord/` | 每 30 分鐘爬取 → 雙層 AI 篩選 → 每日 08:00 彙整推播 |
| **UMA Info Portal** | `/uma-info/` | 官網資訊整合頁 |

### ⚙️ 管理控制台

| 功能 | 路由 | 說明 |
|------|------|------|
| **情報站控制台** | `/crawler-admin/` | 健康儀表板、爬蟲觸發、RAG 重建、Discord 推播管理 |
| **Django Admin** | `/admin/` | ORM 後台管理 |

---

## 🏗️ 技術架構

```
┌─────────────────────────────────────────────────────────────────┐
│                        使用者 / Discord                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / Discord Gateway
┌──────────────────────────────▼──────────────────────────────────┐
│                    Nginx（反向代理 + 靜態檔服務）                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │                                          │
┌─────────▼────────┐                      ┌─────────▼────────┐
│   Django + Gunicorn                      │   Discord Bot     │
│   (app_*/views)                          │   discord.py 2.4  │
│                                          │   APScheduler     │
│  ┌─────────────┐  ┌─────────────┐        │   自動新聞推播     │
│  │ RAG (FAISS) │  │ AI Agents   │        └─────────┬────────┘
│  │ 向量索引持久  │  │ LangChain   │                  │
│  │ 化 (./data) │  │ LangGraph   │                  │
│  └─────────────┘  └─────────────┘                  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              AI API Layer                    │   │
│  │  Google Gemini 3.5 Flash (文字/報告/篩選)     │   │
│  │  Gemini 3.1 Flash Image  (封面圖生成)         │   │
│  │  Anthropic Claude Sonnet 4.6 (分析報告)      │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└────────────────────────┬────────────────────────────┘
                         │ Django ORM
┌────────────────────────▼────────────────────────────┐
│                   SQLite / data/                     │
│   GameAnnouncement | Article | PlayerComment         │
│   GeneratedNewsArticle | DiscordNewsLog | ...        │
└─────────────────────────────────────────────────────┘
```

### 資料流程

```
[爬蟲] → data/raw/ → [前處理 Pipeline] → data/processed/
           │                                      │
           └──────────────────────────────────────┤
                                                  ▼
                                         Django ORM (SQLite)
                                                  │
                                    ┌─────────────┴────────────┐
                                    ▼                          ▼
                             [輿情分析模組]              [AI 報告模組]
                             聲量/情感/關聯              Gemini/Claude
                                    │                          │
                                    └─────────────┬────────────┘
                                                  ▼
                                          前端視覺化呈現
                                    (Chart.js / Three.js)
```

---

## 🛠️ 技術選型

### 後端框架

| 套件 | 版本 | 用途 |
|------|------|------|
| Django | `5.2 LTS` | Web 框架（支援至 2028-04） |
| Gunicorn | `≥23.0` | WSGI 伺服器 |
| WhiteNoise | `≥6.7` | 靜態檔服務 |
| APScheduler | `3.11.2` | 排程任務管理 |
| django-apscheduler | `0.7.0` | Django 整合 |

### AI / LLM

| 套件 | 版本 | 用途 |
|------|------|------|
| google-genai | `2.9.0` | Gemini 3.5 Flash 文字 / 3.1 Flash Image 圖片生成 |
| anthropic | `0.111.0` | Claude Sonnet 4.6 分析報告 |
| openai | `≥1.50.0` | Gemini OpenAI 相容端點 |
| langchain | `≥1.3.0` | ReAct Agent 框架 |
| langchain-google-genai | `≥4.2.0` | LangChain × Gemini 整合 |
| langgraph | `≥0.2.0` | StateGraph Agentic AI |
| faiss-cpu | `1.14.2` | 向量相似度搜尋（RAG） |

### 爬蟲 / 資料處理

| 套件 | 版本 | 用途 |
|------|------|------|
| requests | `≥2.32` | HTTP 爬蟲 |
| beautifulsoup4 | `≥4.12` | HTML 解析 |
| selenium | `≥4.20` | 動態頁面爬取 |
| pandas | `≥2.2` | 資料處理 |
| jieba | `≥0.42` | 中文斷詞 |
| opencc-python-reimplemented | `≥0.1.7` | 簡繁轉換 |
| pypdf | `≥4.0` | PDF 解析（RAG 知識庫） |

### 整合與基礎建設

| 套件 | 版本 | 用途 |
|------|------|------|
| discord.py | `2.4.0` | Discord Bot SDK |
| python-dotenv | `≥1.0` | 環境變數管理 |
| django-cors-headers | `≥4.3` | CORS 設定 |
| pytz | `≥2024.1` | 時區處理 |

---

## 📡 資料來源

| # | 來源平台 | 說明 | 類型 |
|---|----------|------|------|
| 1 | **巴哈姆特哈啦板** `bsn=34421` | 馬娘玩家社群討論、留言 | 論壇 |
| 2 | **Bilibili BWIKI** | 官方遊戲公告、活動資訊 | Wiki |
| 3 | **ETtoday 遊戲新聞** | 遊戲媒體報導 | 新聞 |
| 4 | **UDN 遊戲版** | 聯合新聞網遊戲報導 | 新聞 |
| 5 | **Gamme 遊戲電影** | 遊戲影音媒體 | 媒體 |
| 6 | **YouTube** | 影片留言、訂閱數、觀看趨勢 | 影音 |

---

## 🗺️ 路由總表

```
/                          首頁 AI 新聞精選
├── popularity-list/       賽馬娘人氣列表
├── introduction/          平台介紹頁
├── course/                課程技術說明
│
├── userkeyword/           關鍵字聲量分析
├── userkeyword_assoc/     全文關聯分析
├── userkeyword_senti/     關鍵詞情感分析
├── userkeyword_db/        全文 DB 搜尋
├── userkeyword_report/    雙模型 AI 分析報告
│
├── uma_top_keyword/       熱門關鍵詞排行
├── uma_top_character/     熱門角色排行
├── correlation/           關鍵詞相關性分析
│
├── dashboard/             公告列表儀表板
├── comment_sentiment/     留言情感排程儀表板
│
├── agent/                 Agentic AI 馬娘助理
├── rag/                   RAG 知識庫問答
├── rag-agent/             Agentic RAG（雙工具）
├── langchain-agent/       LangChain ReAct Agent
├── langgraph-agent/       LangGraph StateGraph Agent
│
├── youtube/               YouTube 影片情感儀表板
├── discord/               Discord Bot 管理
├── uma-info/              UMA Info Portal
│
├── crawler-admin/         情報站控制台
└── admin/                 Django 後台
```

---

## 🚀 快速啟動

### 前置需求

- Python **3.12+**
- Google AI Studio API 金鑰（[取得](https://aistudio.google.com/app/apikey)）
- Anthropic API 金鑰（[取得](https://console.anthropic.com/)）
- Discord Bot Token（選用，[建立](https://discord.com/developers/applications)）

### 安裝步驟

```bash
# 1. 複製專案
git clone <repo-url>
cd umamusume-information-platform

# 2. 建立虛擬環境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 安裝相依套件
pip install -r requirements.txt

# 4. 複製並設定環境變數
cp .env.example .env
# 使用編輯器填入金鑰（見下方「環境變數設定」）

# 5. 建立資料庫 & 套用 Migration
python manage.py migrate

# 6. 收集靜態檔案
python manage.py collectstatic --noinput

# 7. 啟動開發伺服器
python manage.py runserver
```

瀏覽 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可進入平台。

### 啟動 Discord Bot（選用）

```bash
python manage.py run_discord_bot
```

---

## 🐳 Docker 部署

```bash
# 建構並啟動全部服務（Django + Nginx + Discord Bot）
docker-compose up -d --build

# 查看日誌
docker-compose logs -f web-poa

# 停止服務
docker-compose down
```

> **注意**：正式環境建議換用 PostgreSQL 以避免 SQLite 多進程寫入競爭問題。

---

## 🔑 環境變數設定

複製 `.env.example` 為 `.env` 並填入以下必要參數：

```dotenv
# ── Django ──────────────────────────────
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# ── Google Gemini ────────────────────────
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image

# ── Anthropic Claude ────────────────────
ANTHROPIC_API_KEY=your-anthropic-api-key
CLAUDE_MODEL=claude-sonnet-4-6

# ── YouTube Data API ────────────────────
YOUTUBE_API_KEY=your-youtube-api-key

# ── Discord Bot ──────────────────────────
DISCORD_BOT_TOKEN=your-discord-bot-token
```

---

## 📁 專案結構

```
umamusume-information-platform/
│
├── 📂 app_character_pk/          首頁、人氣列表
├── 📂 app_user_keyword*/         關鍵詞分析系列（聲量/關聯/情感/DB/報告）
├── 📂 app_uma_top_keyword/       熱門關鍵詞排行
├── 📂 app_uma_top_character/     熱門角色排行
│
├── 📂 app_dashboard/             公告儀表板
├── 📂 app_comment_sentiment/     留言情感排程
├── 📂 app_correlation_analysis/  關鍵詞相關性
│
├── 📂 app_agent_uma/             Agentic AI（6 工具）
├── 📂 app_rag_uma/               RAG + FAISS
├── 📂 app_rag_agent/             Agentic RAG（O1）
├── 📂 app_agent_langchain/       LangChain Agent（O2）
├── 📂 app_agent_langgraph/       LangGraph Agent（O3）
│
├── 📂 app_youtube_uma/           YouTube 情感儀表板（O5）
├── 📂 app_discord_bot/           Discord Bot 推播（D1–D8）
├── 📂 app_uma_info_portal/       UMA Info Portal（U1–U16）
├── 📂 app_crawler_admin/         情報站控制台
│
├── 📂 data/                      原始 & 前處理資料
├── 📂 knowledge_base/            RAG 知識庫文件
├── 📂 pipeline/                  資料處理 Pipeline 腳本
├── 📂 scripts/                   工具腳本
├── 📂 SPEC/                      設計規格文件
├── 📂 plan/                      開發規劃文件
│
├── 📂 website_configs/           Django 設定、主路由
├── 📂 templates/                 全站共用模板（base.html）
├── 📂 static/                    CSS / JS 靜態資源
├── 📂 nginx/                     Nginx 設定
│
├── 🐳 docker-compose.yml
├── 📋 requirements.txt
├── ⚙️  manage.py
└── 🔐 .env.example
```

---

## 📦 版本紀錄

> 完整更新日誌請見 [CHANGELOG.md](./CHANGELOG.md)

| 版本 | 日期 | 主要變更 |
|------|------|---------|
| `0.6.43-alpha` | 2026-06-25 | 修正 Discord Bot PID 路徑偵測問題 |
| `0.6.42-alpha` | 2026-06-25 | 修復 Discord 推播 async ORM 呼叫問題 |
| `0.6.41-alpha` | 2026-06-25 | Dashboard 多項修復（路由/情感分數/N+1/分頁） |
| `0.6.40-alpha` | 2026-06-25 | 留言情感儀表板「0 已分析」修復 |
| `0.6.39-alpha` | 2026-06-25 | 首頁 AI 新聞載入修復 + Gemini Image 模型更新 |
| `0.6.38-alpha` | 2026-06-25 | AI 新聞橫幅四項視覺優化 |
| `0.6.34-alpha` | 2026-06-25 | 賽馬娘人氣列表獨立頁面 + 首頁 AI 新聞重設計 |

---

## 🗂️ 規格文件

| 文件 | 說明 |
|------|------|
| [`SPEC/INTENT_SPEC.md`](./SPEC/INTENT_SPEC.md) | 意圖規格：為什麼做、做什麼、使用者場景 |
| [`SPEC/DESIGN_SPEC.md`](./SPEC/DESIGN_SPEC.md) | 設計規格：UI/UX 設計系統、各模組介面規格 |
| [`SPEC/TASK_SPEC.md`](./SPEC/TASK_SPEC.md) | 任務規格：功能清單、驗收標準 |
| [`PROJECT_AUDIT.md`](./PROJECT_AUDIT.md) | 專案健檢報告：安全性、技術債、優化建議 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 完整版本變更紀錄 |

---

## 🎨 設計規範

- **主題切換**：深色 / 亮色雙主題，`data-bs-theme` 切換
- **毛玻璃卡片**：`backdrop-filter: blur(16px)`
- **語意 CSS Token**：`--color-accent`、`--color-gold`、`--color-border`
- **漸層文字標題**：品牌紫金配色
- **RWD**：Bootstrap 5 響應式佈局，手機優先
- **無障礙**：WCAG 對比度規範

---

<div align="center">

**賽馬娘資訊平台** — 以 AI 之力，追蹤馬娘社群脈動

<sub>Built with ❤️ using Django · Gemini · Claude · LangChain · LangGraph · Discord.py</sub>

</div>
