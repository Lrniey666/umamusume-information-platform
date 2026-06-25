# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

標籤說明

Added (新增)：新功能。

Changed (變更)：現有功能的變更。

Deprecated (棄用)：未來版本即將刪除的功能。

Removed (刪除)：此版本已移除的功能。

Fixed (修復)：Bug 的修復。

Security (安全)：安全性漏洞的修復。

－－－

## [0.6.59-alpha] - 2026-06-25

### Added
- **`/crawler-admin/youtube/` 情感分析使用面板**（`app_crawler_admin/templates/app_crawler_admin/youtube.html`、`app_crawler_admin/api_views.py`、`app_crawler_admin/urls.py`、`app_youtube_uma/management/commands/analyze_youtube_sentiment.py`）
  - 變更目的：後台管理頁原本只有爬取控制，無法在介面上查看情感分析覆蓋率，也無法手動觸發分析；新增面板讓管理員隨時掌握分析狀態並按需觸發。
  - 主要影響範圍：
    - `youtube.html`：頁面標題區新增「🤖 手動情感分析」快捷按鈕；影片列表後方加入「🤖 情感分析管理」卡片，包含已分析/待分析進度條、正面/中性/負面分布色條與數量、平均情感分數、手動觸發按鈕（可選分析批次上限 20/50/100/200 部）及排程說明提示。
    - `api_views.py`：新增 `api_youtube_sentiment_stats()`（GET，回傳 total/analyzed/pending/positive/neutral/negative/avg_sentiment）與 `api_youtube_analyze()`（POST，以 subprocess 非同步呼叫 `manage.py analyze_youtube_sentiment --limit N`）。
    - `urls.py`：新增路由 `api/youtube-sentiment-stats/` 與 `api/youtube-analyze/`。
    - `app_youtube_uma/management/commands/analyze_youtube_sentiment.py`：新管理指令，支援 `--limit` 參數，串接 Gemini gemini-3.5-flash 逐部影片分析留言樣本並寫入 `YouTubeVideo.sentiment`，輸出每部影片的 skip/ok/err 狀態。
  - 驗收方式：開啟 `http://localhost/crawler-admin/youtube/`，應看到「情感分析管理」面板正確顯示已分析數、待分析數、情感分布；點擊「手動觸發情感分析」後狀態列顯示「✅ 分析任務已在背景啟動」，約 8 秒後統計數字自動更新；若 GEMINI_API_KEY 未設定，管理指令會輸出跳過訊息而非崩潰。

## [0.6.58-alpha] - 2026-06-25

### Fixed
- **`/langchain-agent/` 思考模型不相容導致 500 Internal Server Error**（`app_agent_langchain/views.py`）
  - 變更目的：原本使用 `create_react_agent`（文字格式 ReAct：Thought/Action/Action Input/Observation），此格式需要模型嚴格輸出固定文字，但 `gemini-3.1-flash-lite` 等思考型模型會在回應中夾帶內部推理輸出，導致 LangChain 的 ReAct 格式解析器失敗並拋出例外，最終呈現為 HTTP 500。
  - 主要影響範圍：
    - `app_agent_langchain/views.py`：`_build_agent()` 改用 `create_tool_calling_agent`（原生 function calling）取代 `create_react_agent`；提示模板改為 `ChatPromptTemplate`（含 `system` / `chat_history` / `human` / `agent_scratchpad` 插槽）；`api_chat` 呼叫時補傳 `chat_history: []`。
  - 驗收方式：開啟 `/langchain-agent/`，輸入任意問題（如「最新的活動公告有哪些？」），應取得正常回覆，不再出現 500 錯誤；Docker logs 不應再出現 `Internal Server Error: /langchain-agent/api/chat/`。

## [0.6.57-alpha] - 2026-06-25

### Fixed
- **`/rag-agent/` 思考模型 Function Calling 400 INVALID_ARGUMENT 錯誤**（`app_rag_agent/views.py`）
  - 變更目的：`gemini-3.1-flash-lite` 等思考型（thinking）模型在呼叫工具時，回應 parts 中內嵌 `thought_signature`；若重新手動建構 model 訊息物件（丟棄 `thought_signature`），下一輪送出時 Gemini API 會回傳 `400 INVALID_ARGUMENT: Function call is missing a thought_signature`。
  - 主要影響範圍：
    - `app_rag_agent/views.py`（`api_chat`）：
      1. 將手動重建的 `messages.append({'role': 'model', 'parts': [...]})` 改為直接 `messages.append(candidate.content)`，保留原始 `thought_signature`。
      2. function_call 偵測改為遍歷所有 parts（`next(...)`），避免思考模型將 thought 輸出在 `parts[0]`、function_call 在後續 part 時被錯誤略過。
      3. 文字回應同樣遍歷所有 parts 找第一個有 `.text` 的 part。
  - 驗收方式：在 `/rag-agent/` 頁面輸入任意問題（如「這週哪些馬娘在活動中最熱？」），應正確觸發 `search_uma_announcements` 工具並回傳完整答案，不再出現 400 錯誤。

## [0.6.56-alpha] - 2026-06-25

### Fixed
- **`/uma_top_character/` 與 `/uma_top_keyword/` AJAX 無法觸發**（`app_uma_top_character/templates/.../home.html`、`app_uma_top_keyword/templates/.../home.html`、`base.html`）
  - 變更目的：兩頁點擊「查詢」或載入後圖表完全不顯示，nginx log 確認瀏覽器從未發出 POST 請求；根本原因為 jQuery 從 `code.jquery.com` CDN 外部載入，在部分網路環境或瀏覽器快取失效時無法取得，導致 `$` 未定義、`call_ajax()` 靜默崩潰。
  - 主要影響範圍：
    - `templates/base.html`：jQuery CDN 改為本機靜態檔 `vendor/jquery-3.6.0.min.js`，消除外部 CDN 依賴。
    - 兩頁 `home.html`：Chart.js CDN 改為本機 `vendor/Chart-2.7.3.min.js`；補齊 AJAX `error` handler；加入 X-CSRFToken header；`call_ajax()` 初始呼叫移至 `$(document).ready()` 內確保時序正確；宣告 `barchart` 變數避免全域汙染。
    - `static/vendor/`：新增 `jquery-3.6.0.min.js`、`Chart-2.7.3.min.js` 本機副本。
  - 驗收方式：開啟 `http://localhost/uma_top_character/` 與 `http://localhost/uma_top_keyword/`，頁面載入後應自動顯示「活動」類別的長條圖；nginx log 應出現對應的 POST 請求；選擇其他類別或點擊「查詢」應更新圖表；若 API 失敗應在清單區顯示紅色錯誤訊息。

## [0.6.55-alpha] - 2026-06-25

### Added
- **本機 dev server（SQLite）→ Docker PostgreSQL 搬遷腳本**（`scripts/migrate_dev_to_docker.ps1`、`scripts/reset_postgres_sequences.py`）
  - 變更目的：將舊 `python manage.py runserver` 累積的 SQLite 資料（含 Discord 訊息、爬蟲設定、Uma Info 伺服器設定等）完整匯入 Docker 版 PostgreSQL，避免 Docker 啟動後只剩 CSV 初始化的部分資料。
  - 主要影響範圍：
    - `scripts/migrate_dev_to_docker.ps1`：`dumpdata` → `flush` → `loaddata` → 同步 `media/` 至 Docker volume → 重啟服務。
    - `scripts/reset_postgres_sequences.py`：`loaddata` 後重設 PostgreSQL 序列，避免後續新增資料 PK 衝突。
    - `.gitignore`：忽略 `data/dev_sqlite_dump.json`（搬遷中間產物，約 85MB）。
  - 驗收方式：執行腳本後 `docker exec web-poa python manage.py shell -c "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())"` 應為 **3758**（與 `db.sqlite3` 一致）；`/crawler-admin/`、`/uma-info/` 應可看到原 dev 環境的爬蟲紀錄與 Discord 伺服器設定。

## [0.6.54-alpha] - 2026-06-25

### Changed
- **三個 Agent 頁面 AI 模型型號改從後端設定讀取**（`app_agent_langchain/`、`app_agent_langgraph/`、`app_rag_agent/`）
  - 變更目的：移除前端 HTML 與核心邏輯中硬編碼的 `'gemini-3.5-flash'` 字串，統一由 `settings.UMA_CHAT_MODEL`（對應 `.env` 的 `UMA_CHAT_MODEL`）集中管理，避免型號更新時需逐一修改多處程式碼。
  - 主要影響範圍：
    - `app_agent_langchain/views.py`：`_build_agent()` 改用 `settings.UMA_CHAT_MODEL`；`chat_view` 傳入 `model_name` context。
    - `app_agent_langgraph/graph_core/graph_agent.py`：`build_graph()` 改用 `settings.UMA_CHAT_MODEL`。
    - `app_agent_langgraph/views.py`：`chat_view` 傳入 `model_name` context。
    - `app_rag_agent/views.py`：移除 `GEMINI_MODEL` 常數，改用 `settings.UMA_CHAT_MODEL`；`chat_view` 傳入 `model_name` context。
    - 三個 `chat.html`：badge 由硬編碼文字改為 `{{ model_name }}`。
  - 驗收方式：開啟 `/langchain-agent/`、`/langgraph-agent/`、`/rag-agent/` 三頁，頁首 badge 應顯示 `settings.py` 的 `UMA_CHAT_MODEL` 值（預設 `gemini-3.5-flash`）；修改 `.env` 的 `UMA_CHAT_MODEL` 重啟後三頁 badge 同步更新。

## [0.6.53-alpha] - 2026-06-25

### Removed
- **移除 `/agent/chat/` 全頁聊天介面**（`app_agent_uma/templates/app_agent_uma/home.html` 已刪除；`app_agent_uma/views.py`、`templates/base.html` 同步更新）
  - 變更目的：全頁聊天介面的功能已由全站底部的 VRM 成田路 widget（`#ai-vrm-assistant-root`）完整取代，獨立頁面不再需要。
  - 主要影響範圍：`home.html` 已刪除；`chat_view` GET 處理器改為轉址至首頁（`app_character_pk:home`），POST 端點保留供 VRM widget 繼續呼叫；`base.html` AI 功能選單移除「Agentic AI 助理」連結。
  - 驗收方式：直接造訪 `http://localhost:8000/agent/chat/` 應 301 轉址至首頁；VRM 成田路 widget 仍可正常傳送訊息並取得 AI 回覆；導覽列「AI 功能」選單已無「Agentic AI 助理」項目。

## [0.6.52-alpha] - 2026-06-25

### Fixed
- **`/langchain-agent/` 與 `/langgraph-agent/` 淺色主題顯示異常**（`app_agent_langchain/templates/.../chat.html`、`app_agent_langgraph/templates/.../chat.html`）
  - 變更目的：兩頁所有卡片、聊天視窗、輸入框及氣泡皆使用硬寫暗色 `background`（`#1e1b2e`、`#1a1720`、`#231F2C` 等）inline style，切換至淺色主題時無法繼承 CSS 變數，導致白底頁面上仍顯示深紫色區塊。
  - 修正：新增 `{% block extra_css %}` 定義主題自適應 CSS 類別（`.lc-*` / `.lg-*`），所有背景、邊框、文字顏色改用 `var(--color-bg-*)` / `var(--color-text-*)` / `var(--color-border)` 等設計系統 CSS 變數；JS 動態插入的氣泡同步改為掛 class，不再寫入 hardcoded 色碼。
  - 驗收方式：切換至淺色主題後開啟兩頁，卡片、輸入框、氣泡應配合頁面淺色系顯示，不再出現深紫底色。
- **`/rag/` 送出問題後頁面整個掛掉（500 crash）**（`app_rag_uma/views.py`）
  - 變更目的：`rag_demo_view` 的 `action == "query"` 分支直接呼叫 `query_rag()`，無任何 `try-except`，API 層任何例外（模型名稱錯誤、網路逾時、FAISS 維度不符等）皆會導致 Django 500 頁面，使用者無法得知錯誤原因。另外 `query_rag` 中 `embed_content(contents=query_text)` 傳入純字串，與 `process_uploaded_pdf` 及 `app_rag_agent` 均傳 `list` 的行為不一致，可能導致 SDK 回傳結構不同而崩潰。
  - 修正：`action == "query"` 分支加 `try-except`，異常時將錯誤訊息填入 `context["answer"]` 顯示給使用者；`embed_content(contents=query_text)` 改為 `contents=[query_text]` 與批次嵌入行為一致。
  - 驗收方式：開啟 `/rag/`，在已有向量庫的情況下送出問題，應顯示 AI 回答；若 API Key 未設定或 API 返回錯誤，應顯示「⚠️ 查詢發生錯誤：…」提示，不再出現 500 白頁。

## [0.6.51-alpha] - 2026-06-25

### Fixed
- **`/youtube/` 頁面情感趨勢圖表不顯示的 Bug**（`app_youtube_uma/views.py`、`app_youtube_uma/templates/app_youtube_uma/dashboard.html`）
  - 變更目的：修正兩個連鎖問題：(1) 前端 JS `fetch` 呼叫 `api/stats/` 時未帶 `?q=` 查詢參數，導致圖表永遠查詢全局資料，與影片清單篩選結果不一致；全局影片若皆無情感分析結果（`sentiment=NULL`），`weekly_trend` 為空陣列，JS 直接以 empty-state 訊息取代 canvas，圖表消失。(2) `api_stats` view 未過濾 `published_at__isnull=False`，`TruncWeek(None)` 會產生 `week=None`，`str(None)[:10]` 輸出 `'None'` 字串污染圖表橫軸。
  - 主要影響範圍：`app_youtube_uma/views.py`（`api_stats` 新增 `q` 篩選與 `published_at__isnull=False` 條件）；`dashboard.html`（JS fetch URL 改為 `{% url %}?q={{ query|urlencode }}`）。
  - 驗收方式：開啟 `http://localhost:8000/youtube/?q=馬娘`，若 DB 中存有已情感分析的影片，圖表應顯示與搜尋關鍵字相符的週趨勢線；無相關資料時應顯示空狀態提示而非永久空白。

## [0.6.50-alpha] - 2026-06-25

### Changed
- **`/agent/chat/` 頁面 UI 調整**（`app_agent_uma/templates/app_agent_uma/home.html`）
  - 變更目的：移除與賽馬娘主題無關的純技術說明區塊（`mt-4 p-4 border rounded bg-white shadow-sm text-secondary`），並將聊天輸入表單重新設計為符合賽馬娘美學的主題風格。
  - 主要影響範圍：`home.html` CSS 樣式與 `#chat-form` HTML 結構；新增 `.uma-chat-form-wrapper`、`.uma-input`、`.uma-send-btn` 等賽馬娘主題樣式（左側紫金漸層賽道色條、馬蹄形圖示輸入框、紫金漸層送出按鈕）。
  - 驗收方式：開啟 `http://localhost:8000/agent/chat/`，頁面底部應顯示帶有左側色條、馬圖示輸入框與紫金漸層「發送」按鈕的輸入區；說明與範例提示詞區塊應已消失。

## [0.6.49-alpha] - 2026-06-25

### Fixed
- **修復 `/uma_top_keyword/` 頁面完全不顯示資料的 Bug**（`app_uma_top_keyword/templates/app_uma_top_keyword/home.html`）
  - 變更目的：`const MAX_TOPK = 30` 宣告在 `call_ajax()` 呼叫之後，導致 JavaScript Temporal Dead Zone（TDZ）錯誤——頁面載入時 `call_ajax()` 立即存取 `MAX_TOPK`，觸發 `ReferenceError: Cannot access 'MAX_TOPK' before initialization`；此未捕捉例外讓整個 script block 中止，事件監聽器未掛上、資料一筆都不顯示。
  - 主要影響範圍：`app_uma_top_keyword/templates/app_uma_top_keyword/home.html`（將 `const MAX_TOPK = 30` 移至 `call_ajax()` 呼叫之前）
  - 驗收方式：開啟 `http://localhost:8000/uma_top_keyword/`，頁面載入後應自動顯示「活動」類別的熱門關鍵詞清單與長條圖；切換類別或點擊「查詢」皆可正常更新資料。

## [0.6.48-alpha] - 2026-06-25

### Added
- **新增課堂展示專用頁：`class-5min-demo-script.html`（行動裝置優先）**
  - 變更目的：提供「5 分鐘口頭報告」可直接上台使用的單頁工具，支援中英雙語講稿、英文慢速演練、以及三個網站 + Discord 的快速點選流程。
  - 主要影響範圍：`class-5min-demo-script.html`
    - 手機 / 平板友善版面（Mobile First）
    - 300 秒倒數計時、進度條、步驟切換（Prev / Next）
    - 講稿模式切換：`EN First` / `Bilingual` / `ZH First`
    - 英文語音朗讀（Web Speech API）與語速調整（預設 0.85x）
    - 四段展示流程：主站、情報站控制台、UMA Info Portal、Discord 驗證
    - 每段提供快速開啟連結按鈕（可自訂 `baseUrl` 與 `discordUrl`）
    - 步驟完成標記（Mark Step Done）與互動高亮
  - 驗收方式：
    - 開啟 `class-5min-demo-script.html`，確認在手機寬度下可完整操作
    - 點擊 `Start 5:00`，倒數與進度條同步更新
    - 切換步驟後，講稿與提示內容跟著更新
    - 點擊步驟連結按鈕可開啟對應網站路由；填入 Discord URL 後可開啟伺服器頁
    - `Speak English` 可朗讀當前步驟英文稿，語速滑桿生效

## [0.6.47-alpha] - 2026-06-25

### Fixed
- **修復 Docker 部署時 Discord Bot 從未啟動（`docker-files-poa/entrypoint.sh`）**
  - 根本原因：`Dockerfile` 設定 `ENTRYPOINT ["/entrypoint.sh"]`，而 entrypoint 結尾寫死 `exec gunicorn ...`、完全忽略 `docker-compose.yml` 為 `discord-bot` 服務指定的 `command: python manage.py run_discord_bot`。結果 `discord-bot` 容器其實又跑了一個 Gunicorn 網頁伺服器，Bot 本體（含新聞推播排程、訊息分類、站內 AI 問答、頻道快取同步）從未啟動。
  - 修正：entrypoint 加入指令分流——若有傳入啟動指令（`$# > 0`）則等資料庫遷移就緒後 `exec "$@"`，否則才走完整初始化並啟動 Gunicorn。`discord-bot` 容器自此正確啟動 Bot；web-poa 行為不變。
  - 驗收：`docker compose logs discord-bot` 結尾應為「Bot 上線：…／已加入 N 個伺服器」，而非「啟動 Gunicorn／Listening at 0.0.0.0:8000」。

### Changed
- **資料庫改用 PostgreSQL（Docker 正式部署）；本機開發維持 SQLite**
  - 動機：原 `db.sqlite3` 位於 `.:/app` bind mount，在 Windows Docker Desktop（WSL2）下不支援 SQLite 的 POSIX 檔案鎖；`web-poa`（多 worker）＋ `discord-bot` 並發寫入時噴 `disk I/O error`（例：`_sync_guild_to_db` 失敗 → `GuildChannelCache` 寫不進 → 推播頻道下拉為空、推播設定無法完成、AI 新聞推播失敗）。
  - 變更範圍：
    - `website_configs/settings.py`：`DATABASES` 改為依 `DJANGO_DB_ENGINE` 環境變數切換——`postgres` 走 `django.db.backends.postgresql`（讀 `POSTGRES_*`），未設定則 fallback `db.sqlite3`。
    - `requirements.txt`：新增 `psycopg[binary]>=3.1`（PostgreSQL 驅動）。
    - `docker-compose.yml`：`db`（postgres:16-alpine）加 `pg_isready` healthcheck；`web-poa`、`discord-bot` 帶 `DJANGO_DB_ENGINE=postgres` 等 DB 環境變數並 `depends_on db: service_healthy`。
    - `.env.example`：新增 `POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD` 與說明。
  - 影響：切換後為全新空庫，分析資料由 entrypoint 自 CSV 重新匯入；舊 `db.sqlite3` 內的 `GuildSetting`（各伺服器推播頻道設定）需於 `/uma-info/` 重新設定，或以 `dumpdata`/`loaddata` 搬移。
  - 重新部署：`docker compose up -d --build`。

### Security
- 連帶解決並發寫入造成的資料庫不穩（含先前疑似 `db.sqlite3` 截斷／`disk I/O error`），降低設定與推播紀錄寫入遺失風險。

## [0.6.46-alpha] - 2026-06-25

### Changed
- **`project-intro.html` 升級為「專頁式互動專案介紹頁」**
  - 變更目的：依課程期末說明（Part 1~9）與 `ui-redesign-plan` / 美學規範，製作更完整的展示型 HTML 介紹頁，提升課堂 Demo 可讀性與互動性。
  - 主要影響範圍：`project-intro.html`
    - 新增「期末專題規格對照（第 1–9 部分）」互動面板（可切換：核心必做 / 進階加值 / 選做探索）
    - 新增「第 18 週 5 分鐘展示 + 互評機制」摘要卡，明確對應期末評分情境
    - 新增「美學設計概要落地」區塊，整理主題系統、動效、可及性與圖表規範
    - 路由總表新增即時搜尋過濾功能，便於展示時快速定位頁面
    - 導覽列新增「美學設計」「期末規格」入口，改善單頁導覽效率
  - 驗收方式：
    - 開啟 `project-intro.html` 後，確認可操作 Part 篩選按鈕且卡片顯示即時切換
    - 在路由總表輸入關鍵字可即時過濾，無結果時顯示提示訊息
    - 三態主題（light / dark / system）切換後，新增區塊字色與互動元件可正常閱讀

## [0.6.45-alpha] - 2026-06-25

### Fixed
- **確認 Embed 與推播完全靜默失敗的根本原因：`api_views.py` 缺少 `import logging`**（`app_uma_info_portal/api_views.py`）

  `_send_news_channel_confirm_embed()` 在錯誤處理分支呼叫 `logging.getLogger()` 但頂層沒有 `import logging`，導致執行時拋 `NameError`，整個函式靜默失敗，前端完全收不到反應。

  **修正**：在 `api_views.py` 頂部加入 `import logging`。

  **驗收**：shell 測試 `ok=True`，`#research-outsourcing` 頻道已收到確認 Embed。

## [0.6.44-alpha] - 2026-06-25

### Fixed
- **`/crawler-admin/ai-news/` Discord 推播全面失敗（根因：async context 直接操作 ORM）**
  - 症狀：手動推播單篇/批次/週報都失敗，`DiscordTaskRun.error_message` 顯示  
    `You cannot call this from an async context - use a thread or sync_to_async.`
  - 根因：`discord_push.py` 與 `scheduler.py` 的 async 路徑直接呼叫 Django ORM
  - 修正：
    - `app_crawler_admin/discord_push.py`
      - `push_article()` 讀取 `GeneratedNewsArticle` 改用 `sync_to_async`
      - `push_text_to_guilds()` 讀取 `GuildSetting` / 寫入 `DiscordNewsLog` 改用 `sync_to_async`
      - 新增 `news_channel_id` 非數字與「頻道不支援 send()」防呆
    - `app_discord_bot/scheduler.py`
      - `_run_per_guild_news()` 讀取 `GuildSetting` / `DiscordBotConfig`、寫入 `DiscordNewsLog` 改用 `sync_to_async`
      - 新增無效頻道 ID、頻道型別不支援 `send()` 的失敗計數與日誌
  - 驗收：手動推播任務可完成並寫入 `DiscordNewsLog(status='sent')`；異常頻道會寫 `failed` 原因且不拖垮整批

## [0.6.43-alpha] - 2026-06-25

### Fixed
- **`/dashboard/` 多項問題修復**
  - **連結錯誤**：`dashboard.html` 最新公告列表的 JS 連結 `/announcements/${id}/` 改為 `/dashboard/announcements/${id}/`（路由前綴遺漏導致 404）
  - **情緒分數顯示錯誤**：`announcement_detail.html` 中 `positive_score`/`negative_score`/`neutral_score`（0-1 浮點數）使用 `floatformat:0` 會把 0.65 顯示成 "1%"，改以 `{% widthratio %}` 正確呈現 65%
  - **API 全表載入**：`dashboard.html` 的 `$.getJSON('/api/announcements/')` 載入全部 2153 筆後只取前 6 筆，改為 `?limit=6`；`api_announcements` view 補上 `?limit` 支援
  - **N+1 查詢**：`api_announcements` 補 `select_related('sentiment')` 避免每筆公告各打一次 sentiment 查詢
  - **total_comments 全表迴圈**：`api_stats` 將 `sum(a.comments_count for a in ...)` 改為 `PlayerComment.objects.count()`（單次 SQL COUNT）
  - **公告列表無分頁**：`announcement_list` view 加 `Paginator`（每頁 24 筆），`announcement_list.html` 顯示分頁控制列及正確總筆數
  - 影響範圍：`app_dashboard/views.py`、`app_dashboard/api_views.py`、`templates/dashboard.html`、`announcement_detail.html`、`announcement_list.html`
  - 驗收方式：`/dashboard/` 最新公告點擊可進入詳情頁；`/dashboard/announcements/` 顯示分頁；情緒分數 > 0 時數字與進度條一致

## [0.6.42-alpha] - 2026-06-25

### Fixed
- **留言情感儀表板「0 已分析」問題修復**
  - 根本原因：舊的 `analyze_comments` 命令只分析 `GameAnnouncement`，儀表板 `api_data` 卻顯示 `Article`（巴哈姆特哈啦板文章），導致 `Article.analyzed_at` 永遠為 NULL
  - 新增 `app_comment_sentiment/management/commands/analyze_articles.py`，專門分析 `Article` 物件，寫入 `Article.analyzed_at`、`positive_score`/`negative_score`/`neutral_score` 及 `ArticleEmotion` 六維情緒
  - `views.py` 的 `api_run_task` 改呼叫 `analyze_articles`（原為 `analyze_comments`）
  - `requirements.txt` 補上 `openai>=1.50.0`（Gemini OpenAI 相容端點所需）
  - 影響範圍：`app_comment_sentiment/management/commands/analyze_articles.py`（新增）、`app_comment_sentiment/views.py`、`requirements.txt`
  - 驗收方式：執行 `python manage.py analyze_articles --limit 3` 後，DB 中對應文章的 `analyzed_at` 應有值，儀表板「已分析」數字應大於 0

## [0.6.41-alpha] - 2026-06-25

### Fixed
- **首頁 AI 新聞載入失敗修復**
  - `api_latest_ai_news` 與 `api_ai_news_admin_list` 補上 `try-except`，發生任何 DB/運行例外時改回傳 `{'has_news': false, 'error': '...'}` JSON，不再回傳 HTML 500 頁面
  - 前台 `loadLatestAiNews()` 加入 `resp.ok` 檢查，HTTP 非 200 時主動取 body 片段作為錯誤說明；`.catch()` 現在附帶 `err.message` 並輸出至 `console.error` 以便除錯
  - 影響範圍：`app_user_keyword_llm_report/views.py`、`app_character_pk/templates/app_character_pk/home.html`

- **封面圖生成模型版本更新（gemini-2.5-flash-image-preview 已停服）**
  - `gemini-2.5-flash-image-preview` 的 preview 版本已停服，`gemini-3.1-flash-image` 為 2026-05-28 GA（退役不早於 2027-05-28）
  - 同步更新 `website_configs/settings.py` 與 `app_user_keyword_llm_report/services_ai_news.py` 的 `GEMINI_IMAGE_MODEL` 預設值
  - 新生成的 AI 新聞封面圖將由 `gemini-3.1-flash-image` 實際產出，而非靜默 fallback 至來源圖連結

---

## [0.6.40-alpha] - 2026-06-25

### Changed
- **首頁版面調整：AI 新聞橫幅四項優化**（`app_character_pk/templates/app_character_pk/home.html`）

  **變更目的**：改善封面橫幅的視覺呈現與頁面資訊層級。

  1. **`aiNewsCoverImg` 加高（不裁切）**：移除固定 `aspect-ratio: 16/9` 與 `max-height: 420px`，改為 `width: 100%; height: auto; max-height: 640px;`，圖片自然展開不遮蓋任何部分。
  2. **`ai-news-banner-caption` 改疊於圖片下方**：由原本 `position: absolute`（疊於圖片右側）改為 `position: static`，成為圖片正下方的獨立區塊；`ai-news-banner-overlay` 層已移除。
  3. **Caption 背景改為右至左漸層**：caption 背景使用 `linear-gradient(to left, 紫金色調 → 表面色)`，右側帶有品牌紫/金色調，往左漸褪，亮色主題亦有對應的淺色漸層配置。
  4. **`col-lg-12 intro-section` 移至頁面頂端**：平台簡介（標題、stats、說明）改置於 `{% block content %}` 第一區塊，AI 新聞卡片位置移至簡介區塊之後，頁面資訊層級更符合「先認識平台 → 再看新聞內容」的閱讀邏輯。

  **影響範圍**：`app_character_pk/templates/app_character_pk/home.html`（CSS + HTML 結構）

  **驗收方式**：首頁載入後，簡介區塊最先出現；封面圖片完整顯示無裁切；圖片下方 caption（標題＋meta）背景為右深左淡漸層；亮色/深色主題切換後 caption 均可正常閱讀。

---

## [0.6.39-alpha] - 2026-06-25

### Fixed
- **持久 Bot 狀態仍被誤判離線（PID 寫入路徑層級錯誤）**
  - 症狀：`run_discord_bot` 已連上 Gateway，但 `get_bot_status()` 顯示 `running=False`，`news` 任務誤走 thread/臨時連線路徑
  - 根因：`run_discord_bot.py` 的 PID 路徑誤用 `parents[4]`，寫到專案外層，`bot_manager` 在專案根目錄找不到 pid 檔
  - 修正：改為 `parents[3] / 'discord_bot.pid'`（專案根目錄）
  - 驗收：`get_bot_status()` 回傳 `{'running': True, 'source': 'pidfile'}`，新建 `news` 任務 runner 為 `bot` 且可成功推播

## [0.6.38-alpha] - 2026-06-25

### Fixed
- **Bot PID 檔自動管理（不再需要從控制台啟動才能被偵測）**（`run_discord_bot.py`）

  Bot 啟動時自行寫入 `discord_bot.pid`；結束時自動清除。無論用哪種方式啟動都能被控制台偵測。

- **`push_text_to_guilds` 加入 `fetch_channel` fallback**（`discord_push.py`）

  與 `scheduler.py` 一致，頻道不在快取時改用 Discord API 查詢，避免靜默跳過。

## [0.6.37-alpha] - 2026-06-25

### Changed
- **首頁 AI 新聞封面橫幅：三項視覺優化**（`app_character_pk/templates/app_character_pk/home.html`）

  1. **加高封面橫幅**：改用 `aspect-ratio: 16/9` + `max-height: 420px`，依圖片原始比例顯示完整圖片，不再強制裁切。
  2. **漸層遮罩改為右至左**：右側（標題文字區）不透明 → 左側（圖片主體區）透明，讓圖片左側完整可見。
  3. **亮色主題遮罩改用亮色配色**：深色主題保留深色遮罩（白色文字），亮色主題改為淺紫白色遮罩（深色文字），避免影響閱讀；標題文字、meta、badge 顏色依主題分別設定，確保 WCAG 對比度。
  4. **手機版 RWD 降級**：螢幕寬 ≤640px 時，標題區退回底部漸層模式，避免右側欄位過窄。

  **驗收方式**：亮/深色主題下標題文字皆清晰可讀；圖片完整顯示不被裁切（16:9 比例）

## [0.6.36-alpha] - 2026-06-25

### Fixed
- **首頁 AI 新聞卡：封面圖下方大片空白問題**（`app_character_pk/templates/app_character_pk/home.html`）

  **根本原因**：原先採左右雙欄 Grid 版型，左側封面圖設有 `max-height` 限制，右側文字欄過長時圖片停在固定高度，左欄其餘空間變成空白。

  **修正方案**：改為上下版型（報紙風格）：
  1. **封面橫幅（全寬，220px）**：有圖時以全寬橫幅顯示封面，底部疊加黑色漸層遮罩，標題文字與 meta 直接疊加在圖片底部。
  2. **無封面時**：改顯示純色漸層 placeholder banner，同樣呈現標題與 meta。
  3. **正文區（全寬）**：副標、摘要（斜體引言樣式，左側紫色邊線）、正文段落依序向下排列，完全無空白問題。
  4. **參考來源（底部橫排）**：改為無序號 flex 橫排 chip 樣式，視覺更清爽。

  **驗收方式**：無論正文長短，頁面均無左側大片空白；封面圖有無皆正常渲染

## [0.6.35-alpha] - 2026-06-25

### Added
- **新增「賽馬娘人氣列表」獨立頁面**（`app_character_pk`）

  **變更目的**：原首頁「角色人氣排行」與「評論聲量變化」功能獨立至新路由，讓首頁聚焦於 AI 新聞精選。

  **主要影響範圍**：
  - `app_character_pk/views.py`：新增 `popularity_list` 視圖
  - `app_character_pk/urls.py`：新增 `path('popularity-list/', ..., name='popularity_list')`
  - `app_character_pk/templates/app_character_pk/popularity_list.html`：全新人氣列表頁面，包含角色人氣排行（排序/篩選/分頁）與評論聲量折線圖 PK 功能
  - `templates/base.html`：導覽列「熱門分析」下拉選單改連至 `/popularity-list/`，文字改為「賽馬娘人氣列表」

  **驗收方式**：訪問 `/popularity-list/` 應顯示角色人氣卡片與聲量折線圖；Ctrl 多選仍可正常比較

### Changed
- **首頁（`/`）重新設計**（`app_character_pk/templates/app_character_pk/home.html`）

  **變更目的**：首頁移除角色人氣排行與聲量圖表，改以 AI 生成新聞精選為主視覺，並向下滑新增精美的平台簡介區域（符合《美學設計概要》與 `ui-redesign-plan.md` 規範）。

  **主要影響範圍**：
  - 首頁上半部：AI 生成新聞精選（毛玻璃卡片、封面圖、摘要、參考來源）
  - 首頁下半部（向下滑顯示）：
    - 平台標題與品牌定語（漸層文字渲染）
    - 統計資訊藥丸條（5+ 來源、1000+ 公告、AI 雙引擎、即時追蹤）
    - 六大功能卡片（人氣列表、關鍵詞分析、AI 報告、留言情感、AI 助理、RAG 問答）
    - 進階 AI 工具橫幅（LangChain/LangGraph/YouTube/Discord）
    - 九大資料來源展示條

  **設計規範落實**：
  - 毛玻璃卡片（`backdrop-filter: blur(16px)`）
  - 漸層文字標題、PWM 呼吸感 hover 上浮動效
  - 語意化 CSS Token（`--color-accent`、`--color-gold`、`--color-border` 等）
  - 深淺雙主題完整支援

  **驗收方式**：首頁顯示 AI 新聞後向下滑可見六大功能卡片與資料來源；點擊各卡片可正確導向對應頁面

## [0.6.34-alpha] - 2026-06-25

### Fixed
- **AI 新聞推播失敗（根本原因：`generate_news()` 參數不匹配）**（`app_discord_bot/news_generator.py`、`scheduler.py`）

  **根本原因**：`scheduler.py` 第 94 行呼叫 `generate_news(model=model_env, tone=tone)`，但 `generate_news()` 簽章不接受 `tone` 參數 → 拋 `TypeError` → 主推播流程整個崩潰，最終任務顯示「成功 0、失敗 0」但實際未送出任何訊息。

  **修正**：
  - `generate_news()` 新增 `tone` 參數（`lively` 活潑 / `concise` 簡潔），依語氣調整 system prompt
  - 將 `SYSTEM_PROMPT` 常數改為 `_build_system_prompt(tone)` 動態組裝

- **推播確認 Embed 在部分情形下未出現**（`app_uma_info_portal/api_views.py`、`server_manage.html`）

  **原因**：推播頻道下拉未排除論壇／分類等無法直接 POST 訊息的頻道類型；發送失敗時前端無明確錯誤原因。

  **修正**：
  - `_send_news_channel_confirm_embed`：改回傳 `(ok, reason)`，依 Discord 狀態碼（403/404/400）回傳可判讀原因
  - 推播頻道下拉僅保留 `text` / `news` 類型頻道（排除論壇、分類、語音）
  - 前端橫幅顯示後端回傳的具體失敗原因

  **驗收**：選擇文字頻道儲存 → 收到確認 Embed；若 Bot 缺權限或頻道類型不符 → 前端顯示明確原因。

## [0.6.33-alpha] - 2026-06-25

### Fixed
- **AI 新聞推播到 Discord 頻道失敗**（`app_discord_bot/scheduler.py`、`ai_chat.py`）

  **原因**：
  1. `scheduler.py`：`bot.get_channel()` 只搜本地快取，新設定的頻道不在快取中時直接跳過不推播
  2. `ai_chat.py`：`_build_ai_context` 從不存在的 `app_uma_news.NewsData` import（欄位名稱也有誤）

  **修正**：
  - `scheduler.py`：`get_channel()` 回 `None` 時改用 `await bot.fetch_channel()` 直接查詢 Discord API
  - `ai_chat.py`：改從 `app_user_keyword_db.models.NewsData` 正確 import，修正欄位名稱（`date`、`content`）

  **驗收**：Bot 手動推播成功，Discord 頻道收到 AI 新聞摘要。

## [0.6.32-alpha] - 2026-06-25

### Fixed
- **ai-news 頁面推播至 Discord 失敗**（`app_crawler_admin/discord_push.py`）

  `push_text_to_guilds()` 使用 `bot.get_channel()` 只搜本地快取，頻道不在快取時靜默失敗（同 scheduler 的問題）。

  **修正**：加入 `await bot.fetch_channel()` fallback，直接查詢 Discord API。

## [0.6.31-alpha] - 2026-06-25

### Fixed
- **推播設定儲存後 Discord 確認 Embed 未發出（架構根本修正）**（`app_uma_info_portal/api_views.py`、`guild_settings_service.py`、`server_manage.html`）

  **根本原因**：Django web server 與 `run_discord_bot` 是完全獨立的 Python 進程，`get_bot_instance()` 在 web 進程中永遠回傳 `None`，舊實作從根本上無法工作。

  **修正**：
  - `_send_news_channel_confirm_embed`：改用 **Discord HTTP API**（`POST /channels/{id}/messages`）直接以 Bot Token 發送 Embed，完全不依賴 Bot 進程是否在線
  - `guild_settings_service.py`：移除 service 層 Embed 觸發（改由前端統一負責）
  - `saveNewsSettings()`：只要儲存時有設定推播頻道，每次都發 Embed 確認
  - 前端錯誤提示改為通用格式（不再顯示 Bot 離線）

  **驗收**：Portal 推播設定頁儲存後，Discord 目標頻道收到確認 Embed（前提：`DISCORD_BOT_TOKEN` 正確、Bot 有目標頻道發送訊息權限）。

## [0.6.30-alpha] - 2026-06-25

### Added
- **@UMA Info 支援圖片讀取與分析**（`app_discord_bot/ai_chat.py`、`run_discord_bot.py`）

  **功能**：使用者 @mention Bot 時可附上圖片（PNG/JPEG/WEBP/GIF），Bot 下載附件後以 Gemini 多模態 API 分析畫面內容並回覆。僅附圖無文字時使用預設分析提示。

  **限制**：單張 ≤ 4MB、每則最多 4 張；模型沿用 `UMA_CHAT_MODEL`。

  **驗收**：@UMA Info + 遊戲截圖 → Bot 以繁體中文描述並分析圖片內容。

## [0.6.29-alpha] - 2026-06-25

### Added
- **Discord 斜線指令：頻道讀取範圍與推播目標**（需伺服器管理員）

  **目的**：將 UMA Info Portal 管理頁（`/uma-info/servers/<id>/manage/`）的「頻道讀取範圍」「推播目標」功能移植至 Discord，管理員可直接在伺服器內設定。

  **新增指令**（`app_discord_bot/slash_commands.py`）：
  - `/read-scope`：`view`、`set`、`rule-add`、`rule-remove`、`rule-list`
  - `/news-target`：`view`、`set`、`clear`

  **共用服務**：`app_uma_info_portal/guild_settings_service.py` 統一更新 `GuildSetting` 與稽核；Portal `api_guild_settings_save` 改為呼叫同一服務。

  **權限**：`default_permissions=administrator` + 執行時二次驗證；回覆採 ephemeral 避免洗版。

  **驗收**：管理員在 Discord 設定推播頻道後，Portal 同伺服器設定同步；推播頻道收到確認 Embed。

## [0.6.28-alpha] - 2026-06-25

### Changed
- **@UMA Info AI 問答改為純文字回覆**（`app_discord_bot/management/commands/run_discord_bot.py`）

  **目的**：一般 @mention 問答與 Discord 日常對話一致，不再以 Embed 卡片呈現。

  **行為**：
  - 成功回覆：`message.reply()` 送出純文字；超過 1900 字時首段 reply、其餘分段 `channel.send`
  - 推播確認、新聞摘要等系統訊息仍可使用 Embed（與問答分離）

  **UI**：`app_uma_info_portal/home.html` AI 問答 mockup 同步改為文字泡泡預覽。

  **驗收**：Discord 中 @UMA Info 提問，回覆為一般文字訊息而非 Embed 卡片。

## [0.6.27-alpha] - 2026-06-25

### Changed
- **Discord Bot 回應與 UMA Info UI 移除馬 Emoji**（符合美學規範「不要有馬的 Emoji」）

  **修改範圍**：
  - `app_discord_bot/management/commands/run_discord_bot.py`：AI 問答 Embed 標題 `🐴 UMA Info 回覆` → `UMA Info 回覆`
  - `app_uma_info_portal/templates/app_uma_info_portal/base_portal.html`：品牌圖示改為 Discord 藍漸層「U」字標
  - `app_uma_info_portal/templates/app_uma_info_portal/home.html`：邀請按鈕、Bot mockup 頭像、Embed 預覽、CTA 區塊移除 🐴，改為「U」字標或 Discord SVG
  - `templates/base.html`：主站導覽 UMA Info 連結移除 🐴

  **驗收**：`/uma-info/` 全頁與 Discord @UMA Info 回覆 Embed 標題皆無 🐴／🐎／🏇；品牌識別改以「U」字標與 Discord 色系呈現。

## [0.6.26-alpha] - 2026-06-25

### Changed
- **UMA Info 頂部導覽列移除「控制台」**（`app_uma_info_portal/templates/app_uma_info_portal/base_portal.html`）

  **目的**：UMA Info Portal 面向 Discord 伺服器管理員；情報站控制台（`/crawler-admin/`）為平台管理員專用，不應出現在 Portal 頂部導覽，避免一般使用者誤入後台。

  **影響範圍**：UMA Info 全站頂部 `.portal-nav`；頁尾連結維持不變。

  **驗收**：開啟 `/uma-info/` 任一頁面，頂部導覽僅顯示「功能介紹」「回主站」，右側為主題切換與登入／登出；不再出現「控制台」連結。

## [0.6.25-alpha] - 2026-06-25

### Fixed
- **@UMA Info AI 問答無法回應**（`app_discord_bot/management/commands/run_discord_bot.py`）

  **根本原因**：`_generate_ai_answer` 使用舊版 SDK `import google.generativeai as genai`，但專案已移除該套件，僅安裝新版 `google-genai`（`from google import genai`），導致每次有人 @UMA Info 都觸發 `ModuleNotFoundError`，Bot 靜默回傳空值、沒有任何 Discord 回覆。

  **修改**：改為使用新版 `google-genai` SDK（`client.models.generate_content`），並同步套用 `system_instruction` 參數格式；預設模型更新為 `gemini-3.1-flash-lite`（與 `UMA_CHAT_MODEL` env 一致）。

  **驗收**：重啟持久 Bot 後，在 Discord @UMA Info 詢問賽馬娘相關問題，Bot 應正常以繁體中文回覆。

## [0.6.24-alpha] - 2026-06-24

### Fixed
- **Discord 訊息分類器效能重構**（`app_discord_bot/classifier.py`、`app_crawler_admin/api_views.py`）

  **問題**：原版一次將全部未分類訊息載入記憶體（80k+ ORM 物件），Layer 1 跑完後才一次寫入 DB，導致：
  - 長時間無進度輸出（看起來卡住）
  - Layer 2 Gemini 呼叫次數無上限（80k 訊息 ÷ 50 = 1,600+ API 呼叫，成本高）
  - 中途取消或 crash 時所有已完成分類結果全部遺失

  **修改**：
  - 改為分批讀取（`CHUNK_SIZE=2000`），每批 Layer 1 完成後立即寫入 DB
  - 新增 `MAX_L2_BATCHES=200`（10,000 則上限），達上限後本次結束，下次繼續
  - 取消時保留已完成的 Layer 2 結果
  - 任務結果新增 `limit_reached` 狀態，UI 提示「請再次觸發繼續」

  **驗收**：觸發 classify 任務，每 2,000 筆會輸出進度日誌，任務在合理時間內完成並可分批累進。

## [0.6.23-alpha] - 2026-06-24

### Changed
- **Discord 訊息分類器 Layer 2 模型與截斷長度調整**（`app_discord_bot/classifier.py`）
  - AI 模型：`gemini-3.5-flash` → `gemini-3.1-flash-lite`（降低大批量分類成本）
  - 每則訊息截斷長度：前 200 字 → 前 300 字（提供更充分的語境，提升分類準確率）
  - **驗收**：在 `/crawler-admin/discord/` 觸發分類任務，日誌應顯示 `gemini-3.1-flash-lite` 呼叫成功且分類結果合理。

## [0.6.22-alpha] - 2026-06-24

### Fixed
- **手動任務觸發一啟動即顯示舊取消記錄**

  **問題**：Django 重啟後，先前的 `crawl` 任務（task #4）仍以 `running` 狀態殘留在 DB 中。`_launch_discord_task` 找到此殘留任務後直接回傳，沒有驗證 worker 執行緒是否仍存活，導致前端連上舊任務、顯示上次取消留下的日誌（「⚠ 已收到取消請求…」）。

  **修復**：
  - `app_crawler_admin/api_views.py` — `_launch_discord_task` 在回傳既有任務前，先透過 `_ACTIVE_WORKERS` 確認 worker 存活：
    - Worker 仍存活 → 正常回傳，防止重複觸發
    - Worker 已死或不存在（重啟後殘留）→ 自動將該任務標記為 `failed`、清除對應 cancel 旗標，再建立全新任務
  - 手動清除 DB 中 task #4 的殘留 `running` 狀態

  **驗收**：重啟 Django 後再點擊任何手動任務，應正常啟動新任務而非顯示舊日誌。

## [0.6.21-alpha] - 2026-06-24

### Changed
- **Discord 任務架構重構：消除「持久 Bot / 臨時 Bot」雙連線衝突**

  **問題根源**：`crawl` 與 `news` 任務先前由 Django 行程在獨立執行緒中啟動「臨時 Bot」，與持久 Bot（`manage.py run_discord_bot`）共用同一個 Bot Token，導致 Discord Gateway 只允許一條 Session 的限制引發衝突，任務卡在「⏳ 正在連線至 Discord Gateway…」。

  **解法**：
  1. `DiscordTaskRun` 新增 `runner`（`bot` / `thread`）與 `cancel_requested`（Boolean）欄位。
  2. 持久 Bot（`run_discord_bot.py`）`on_ready` 啟動 `_task_poller` 背景協程，每 2 秒輪詢 DB，自動接手 `runner='bot'` 的 `pending` 任務並在同一 asyncio 事件迴圈中執行，完全不需要新開 Gateway 連線。
  3. `_launch_discord_task`（`api_views.py`）在偵測到持久 Bot 運行時，將 `crawl` / `news` 任務的 `runner` 設為 `'bot'`，不再啟動執行緒；持久 Bot 未運行時 fallback 為舊有臨時 Bot 執行緒（`classify` / `convert` 不需要 Discord 連線，維持執行緒方式不變）。
  4. 取消 API 同時設定記憶體旗標 `_CANCEL_FLAGS` 與 DB `cancel_requested` 欄位，跨行程取消信號均可被偵測。
  5. 移除 `_run_discord_ephemeral_bot` 中「暫停 / 恢復持久 Bot」的臨時處理邏輯，現在 fallback 路徑只在 Bot 不在線時才會觸發，無 Gateway 衝突。

  **影響範圍**：`app_discord_bot/models.py`、`migrations/0005_add_runner_cancel_requested.py`、`app_discord_bot/management/commands/run_discord_bot.py`、`app_crawler_admin/api_views.py`。

  **驗收方式**：
  - 啟動持久 Bot，在 `/crawler-admin/discord/` 觸發 crawl 任務 → 任務直接顯示「由持久 Bot 接手執行」，無 Gateway 卡住。
  - 取消任務 → Bot 行程的 `cancel_fn` 透過 `cancel_requested` DB 欄位正確停止爬取。
  - 停止持久 Bot，再觸發 crawl 任務 → Fallback 為臨時 Bot 執行，任務正常完成。

## [0.6.20-alpha] - 2026-06-24

### Changed
- **Docker Compose 環境變數改為共用專案根目錄 `.env`**
  - 目的：本機開發與容器部署使用同一份設定，避免 `docker-files-poa/.env` 與根目錄 `.env` 雙軌維護；對齊 `SPEC/DESIGN_SPEC.md` §11.1 規格。
  - 影響範圍：
    - `docker-compose.yml`：`web-poa`、`discord-bot` 的 `env_file` 由 `./docker-files-poa/.env` 改為 `./.env`
    - `docker-files-poa/.env.example`：標記廢止，改指向根目錄 `.env.example`
    - `SPEC/DESIGN_SPEC.md` §11.1：同步實際服務結構與 `env_file` 路徑
    - `SPEC/TASK_SPEC.md` T16：補充環境變數路徑說明
  - 驗收：
    1. 專案根目錄已有 `.env` 時，`docker compose config` 不再報 env file 找不到
    2. `docker compose up -d` 後容器內可讀取與本機相同的 API 金鑰與 Django 設定

## [0.6.19-alpha] - 2026-06-24

### Added
- **Discord 爬取並行化 + UI 可設定訊息上限**

  **目的**：加速頻道爬取（原循序 + 0.5 s sleep → 並行 Semaphore），並移除寫死的 `DISCORD_CRAWL_LIMIT`，改由 `/crawler-admin/discord/` 頁面自行設定。

  **主要變更**：
  - `app_discord_bot/models.py`：新增 `DiscordCrawlSettings`（singleton，pk=1），欄位：`crawl_limit`（預設 1000，0=不限）、`concurrency`（預設 3，範圍 1–10）
  - `app_discord_bot/migrations/0004_add_discord_crawl_settings.py`：對應 migration
  - `app_discord_bot/crawler.py`：
    - `crawl_guild` 改以 `asyncio.Semaphore(concurrency)` 並行所有頻道
    - 共享 `asyncio.Event` 傳遞取消信號，並行時也能快速停止
    - `crawl_channel` 接受 `crawl_limit` 參數；`None` = 不限
    - `_get_crawl_settings()` 優先讀 `DiscordCrawlSettings`，fallback `DISCORD_CRAWL_LIMIT` 環境變數
    - 移除每頻道間的固定 `asyncio.sleep(0.5)`（並行已有自然節流）
  - `app_crawler_admin/api_views.py`：新增 `api_discord_crawl_settings_get`、`api_discord_crawl_settings_save`
  - `app_crawler_admin/urls.py`：新增 `api/discord/crawl-settings/` 與 `api/discord/crawl-settings/save/`
  - `app_crawler_admin/templates/app_crawler_admin/discord.html`：「爬取全域設定」卡片，含每頻道訊息上限與並行頻道數輸入，即時顯示目前生效值

  **驗收**：
  1. 開啟 `/crawler-admin/discord/` 可看到「爬取全域設定」卡片
  2. 修改值後點「儲存設定」，badge 顯示新設定值
  3. 執行爬取任務，日誌顯示「每頻道上限：N · 並行數：M」
  4. 多個頻道同時出現在日誌中（並行特徵）

## [0.6.18-alpha] - 2026-06-24

### Changed
- **`/userkeyword_assoc/` 版面優化與關聯詞 Pill 風格**（`app_user_keyword_association/templates/.../home.html`）：
  - 將五個獨立 `col-lg-6` 卡片重新組織為三個 `col-12 > row.align-items-start` 巢狀列，確保每對卡片各自形成獨立的 flex 行，根除「一高一矮導致後續元件出現大空白」的版面問題。
  - 第一列：輸入條件 + 文字雲；第二列：公告清單 + 同時出現段落；第三列：關聯詞（獨立半欄）。
  - 公告清單與段落列的 `card-body` 加入 `max-height: 420px; overflow-y: auto`，防止單卡過高撐壞整列高度平衡。
  - 「與它同時出現的熱門詞彙」列表改為 `.word-pill` 膠囊標籤（`border-radius: 999px`、`background: --color-accent-muted`），詞彙與次數並排顯示，視覺更清晰。
  - 文字雲 SVG 改用 `width="100%" viewBox` 回應式寫法，適配不同容器寬度。
  - 驗收：各查詢結果卡片高度不再互相干擾；關聯詞區塊以膠囊 pill 標籤呈現。

---

## [0.6.17-alpha] - 2026-06-24

### Fixed
- **`/userkeyword_assoc/` 任何操作皆回傳伺服器錯誤**（`app_user_keyword_association/views.py`）：
  - `filter_dataFrame_fullText` 對 `df.date.max()` 未處理混型欄位（`str + float NaN`）導致 `TypeError`。
  - 改以 `.dropna()` 再過濾長度為 10 的有效日期字串後取 `max()`，並加入 `try/except` 保護 `datetime.strptime`，與 `app_user_keyword.views.filter_dataFrame` 相同的防呆邏輯。
  - 驗收：輸入任意關鍵字點擊查詢，不再出現「伺服器錯誤，請稍後再試」。

### Changed
- **`/uma_top_character/` 熱門角色長條圖動態高度**（`app_uma_top_character/templates/.../home.html`）：
  - Chart 容器加入 `id="chart-container"` 並改用 `maintainAspectRatio: false`。
  - 每筆資料高 44px、最小 200px，確保條列越多圖表越高，文字與條列不再擠在一起。
  - `topk` 輸入值自動限制最大值 30，超過時回落至 30。
- **`/uma_top_keyword/` 熱門關鍵詞長條圖縱橫調換 + 動態高度**（`app_uma_top_keyword/templates/.../home.html`）：
  - `type: 'bar'`（垂直）改為 `type: 'horizontalBar'`（水平），對應 `scales` 由 `yAxes` 改為 `xAxes`。
  - 同樣加入動態高度（每列 44px）與 `topk` 最大值 30 限制。
- **`/userkeyword_db/` 導覽連結文字**（`templates/base.html`）：
  - 「公告全文檢索（資料庫版）」→「公告全文檢索」，移除括號附注。
- **`/comment_sentiment/` 統計卡片標籤**（`app_comment_sentiment/templates/.../dashboard.html`）：
  - 「公告總數」→「文章總數」，語意更準確。

---

## [0.6.16-alpha] - 2026-06-24

### Fixed
- **AI 新聞模型目錄版本更新（過期版本修正）**
  - `claude-opus-4-1` 已於 2026-06-05 正式 deprecated（退役期 2026-08-05），替換為 `claude-opus-4-8`（2026-05-28 GA）
  - `gemini-2.5-flash-lite`（2025-07 GA）替換為更新的 `gemini-3.1-flash-lite`（2026-05-07 GA）
  - 預設排序調整：Gemini 改以最新 `gemini-3.5-flash` 優先，`gemini-2.5-pro` 次之
  - 影響範圍：`app_user_keyword_llm_report/services_ai_news.py` — `DEFAULT_TEXT_MODEL_CATALOG`
- **AI 新聞模型下拉選項移除括號純文字標籤**
  - `<option>` 內原本附加的「（供應商｜屬性｜成本）」純文字已移除，下拉保持乾淨的模型名稱；模型資訊改由下方膠囊標籤展示
  - 影響範圍：`app_crawler_admin/templates/app_crawler_admin/ai_news.html`

---

## [0.6.15-alpha] - 2026-06-24

### Changed
- **AI 新聞管理頁模型資訊標籤樣式升級（非純文字）**
  - 目的：提高模型資訊可讀性，與同頁 Discord 狀態膠囊視覺一致。
  - 影響範圍：
    - `app_crawler_admin/templates/app_crawler_admin/ai_news.html`
  - 變更內容：
    - `aiModelMeta` 由純文字改為 `pill` 膠囊標籤組合，顯示：
      - 供應商（Gemini/Claude）
      - 模型屬性（多個標籤）
      - 成本標示
      - 封面圖固定 Gemini 狀態
    - 新增前端 `escHtml()`，避免標籤文字插入時造成 HTML 注入風險。

### Verified
- UI 行為：模型切換時，屬性與成本標籤會即時以膠囊樣式更新。

---

## [0.6.14-alpha] - 2026-06-24

### Added
- **AI 新聞模型動態目錄 API（後端配置化）**
  - 目的：模型更新時不需改前端模板，改由後端集中管理。
  - 影響範圍：
    - `app_user_keyword_llm_report/services_ai_news.py`：新增模型目錄解析、`model_id` 路由與回傳 `text_model`/`image_model`
    - `app_user_keyword_llm_report/views.py`、`urls.py`：新增 `GET /userkeyword_report/api/model_options/`
    - `website_configs/settings.py`：新增 `AI_NEWS_TEXT_MODELS`、`AI_NEWS_DEFAULT_TEXT_MODEL` 環境設定入口
  - 成效：AI 新聞管理中心可動態載入 Gemini/Claude 各三款模型，並顯示模型屬性與成本標籤；封面圖仍固定走 Gemini。

- **AI 新聞 Discord 批次推播（多篇文章）**
  - 目的：提升編輯台一次推播多則重點新聞的效率。
  - 影響範圍：
    - `app_crawler_admin/api_views.py`：新增 `POST /crawler-admin/api/ai-news/discord-push-articles/`；`news` 任務新增 `articles` 批次模式
    - `app_crawler_admin/urls.py`：掛載批次推播 API 路由
    - `app_crawler_admin/templates/app_crawler_admin/ai_news.html`：新聞列表新增勾選框、全選、批次推播按鈕
  - 成效：可在 AI 新聞頁勾選多篇文章，一次推播至所有已設定推播伺服器（仍共用單一 `news` 任務避免並發衝突）。

### Changed
- **AI 新聞管理頁模型選擇 UI 改為 API 驅動**
  - 原本模型選單硬編碼在模板，改為頁面載入時呼叫 `model_options` API。
  - 生成提示增加本次實際使用模型顯示，便於編輯台校對內容品質與成本策略。

### Verified
- `python manage.py check`：通過（0 error）。
- `ReadLints`：本次變更檔案無新增 lint 錯誤。

---

## [0.6.13-alpha] - 2026-06-25

### Added
- **AI 客服收起/展開切換按鈕**：
  - **HTML（`base.html`）**：新增 `.ai-vrm-assistant-body` wrapper 包住 speech、canvas-wrap、chat，以及獨立的 `.ai-vrm-assistant-toggle` 按鈕列，置於 root 最底部。
  - **CSS（`ai-vrm-assistant.css`）**：
    - `.ai-vrm-assistant-body`：展開時正常顯示；收起時（`.is-collapsed`）套用 `opacity: 0; transform: scale(0.94) translateY(10px); pointer-events: none`，平滑淡出縮小。
    - `.ai-vrm-assistant-toggle-btn`：預設為毛玻璃小膠囊，顯示「↓ 收起」；收起狀態升格為漸層 FAB 按鈕，顯示「💬 成田路」，有 hover 上浮效果。
    - `.vrm-toggle-hide` / `.vrm-toggle-show`：以 CSS `display` 切換對應圖示文字。
  - **JS（`ai-vrm-assistant.js`）**：初始化時讀取 `localStorage('vrm-assistant-collapsed')` 還原收起狀態；點擊 toggle 按鈕執行 `classList.toggle('is-collapsed')` 並寫回 localStorage 持久化。

### 驗收
- 點擊「↓ 收起」後 3D 模型、對話框、預設問題淡出，右下角保留「💬 成田路」FAB 按鈕。
- 點擊 FAB 按鈕後客服淡入展開。
- 重新整理後收起/展開狀態保持不變（localStorage 記憶）。
- toggle 按鈕本身始終可點擊（`pointer-events: auto`），不受主 root `pointer-events: none` 影響。

---

## [0.6.12-alpha] - 2026-06-24

### Changed
- **廢除 Canvas Bleed，改用放大透明畫布策略（`ai-vrm-assistant.css`）**：
  - 刪除 canvas 元素負值定位（`top: -28px; left: -14px; calc(100%+28px)`）。
  - `canvas-wrap` 直接放大至 `350×450`（行動版 `300×390`），background 改為 `transparent`。
  - canvas 元素改為 `top:0; left:0; width/height: 100%` 填滿容器。
  - `#ai-vrm-assistant-root` 寬度同步改為 `350px`（行動版 `300px`）。
  - JS 移除 `CANVAS_BLEED_TOP=28` / `CANVAS_BLEED_SIDE=14` 常數；renderer 初始化與 `on_resize()` 直接讀取 `canvas_wrap.clientWidth/Height`，無額外加減。
- **有機揮手動畫（`ai-vrm-assistant.js`）**：
  - `set_state('welcoming')` 姿勢目標更新：`rUpperZ=0.15`（手臂更高舉）、`rForeX=1.5`（肘部強彎）。
  - 移除 `apply_pose_to_bones` 的 `wave_offset` 參數與 `bone_r_upper.rotation.y` 簡單揮手。
  - `tick()` 新增多關節正弦波邏輯：`bone_r_fore.rotation.z = sin(elapsed*4.8)*0.48`（前臂左右搖擺）、`bone_r_fore.rotation.y = sin(elapsed*4.8-0.5)*0.22`（腕部相位差跟隨），兩者皆以 `lerp` 驅動；非 welcoming 狀態時 lerp 回 0 確保平滑歸位。

### 驗收
- welcoming 時右臂清晰高舉、前臂自然左右揮動，不再被畫布邊緣截切。
- 透明畫布區域滑鼠事件穿透，不阻擋主頁面點擊。
- 非 welcoming 狀態切換後揮手骨骼平滑歸零，不閃跳。

---

## [0.6.11-alpha] - 2026-06-24

### Fixed
- **UMA Info Portal「AI 問答設定」模型名稱錯誤**：使用方式區塊原本硬寫 `Gemini 2.5 Flash Lite`，改為依 `settings.UMA_CHAT_MODEL`（`.env` `UMA_CHAT_MODEL`）動態顯示，目前預設為 **Gemini 3.1 Flash Lite**。
  - 影響範圍：`app_uma_info_portal/views.py`、`server_manage.html`
- **3D 客服對話泡泡 / 輸入列 / 預設問題按鈕接入設計系統 Design Token**：原本各元件使用硬編碼 `rgba()` 顏色，切換明/暗主題時顏色不隨之改變。改為全面使用 `design-system.css` 定義的 CSS 自訂屬性（`--color-bg-elevated`、`--color-bg-surface`、`--color-text-primary`、`--color-border`、`--color-shadow-*`、`--color-accent`、`--color-accent-soft`、`--color-glow-purple`），自動響應 `[data-theme]` 切換，並移除已無用的 `[data-theme="light"]` 硬覆寫。送出按鈕漸層改以 `var(--color-accent)` 為基底。
  - 影響範圍：`static/app_dashboard/css/ai-vrm-assistant.css`
- **AI 客服 429 RESOURCE_EXHAUSTED 友善錯誤處理**：Gemini API 月度額度耗盡時，後端原本直接將原始 SDK 例外字串回傳前端（含 URL、詳細 JSON），現改為偵測 `429` / `RESOURCE_EXHAUSTED` / `spending_cap` 關鍵字，回傳 HTTP 503 + 可判讀的中文提示「AI 服務本月用量已達上限，暫時無法回應，請稍後再試或聯繫管理員。」，對話泡泡顯示友善訊息而非技術錯誤堆疊。
  - 影響範圍：`app_agent_uma/views.py`

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.css` 與 `app_agent_uma/views.py` 無 lint 錯誤。
- 待人工 `Ctrl + F5` 切換明/暗主題驗證對話泡泡/輸入框顏色是否跟隨主題。

---

## [0.6.10-alpha] - 2026-06-24

### Added
- **AI 新聞管理頁整合 Discord 推播**

  **目的**：讓 `/crawler-admin/ai-news/` 可直接觸發與 Discord Bot 相同的新聞推播流程，不必切換至 Discord 控制台。

  **主要變更**：
  - 新增 `app_crawler_admin/discord_push.py`：推播狀態查詢、文章格式化、`push_text_to_guilds` / `push_article` / `push_weekly_summary`
  - 新增 API：
    - `GET /crawler-admin/api/ai-news/discord-status/` — Bot 狀態、推播目標、近期 `DiscordNewsLog`、進行中 `news` 任務
    - `POST /crawler-admin/api/ai-news/discord-push-weekly/` — 觸發週報摘要推播（與 Discord 控制台 `news` 任務相同，走 `scheduler._run_per_guild_news`）
    - `POST /crawler-admin/api/ai-news/discord-push-article/` — 將指定 `GeneratedNewsArticle` 推播至各伺服器推播頻道
  - `api_views.py`：`news` 任務 worker 支援 `_PENDING_NEWS_OPTS`（`weekly` / `article` 模式）；`_launch_discord_task` 新增 `news_opts` 參數
  - `ai_news.html`：Discord 推播卡片（目標伺服器、近期紀錄、週報推播按鈕）、清單列「推播至 Discord」、生成參數「生成後同步推播至 Discord」勾選

  **驗收**：
  1. 開啟 `/crawler-admin/ai-news/`，Discord 推播卡片可顯示目標伺服器與近期紀錄
  2. 點「推播週報摘要」可啟動背景任務，完成後 `DiscordNewsLog` 新增紀錄
  3. 清單中點「推播至 Discord」可將該篇 `GeneratedNewsArticle` 內容推播
  4. 勾選「生成後同步推播」並生成新聞後，自動觸發單篇推播任務

## [0.6.9-alpha] - 2026-06-24

### Fixed
- **Discord 手動任務「停止」功能根治（第二輪）**

  **問題**：取消後按鈕卡在「⏳ 取消中…」、任務長時間停在「建立 Discord 連線」15% 無法停止；`classify` / `convert` / `news` 任務完全不支援取消；伺服器重啟後殘留 `running` 紀錄無法清除。

  **後端（`api_views.py`）**
  - 新增 `_ACTIVE_WORKERS` 追蹤背景執行緒；取消時若 worker 不存在 → **立即**標記 `cancelled`（處理殘留任務）
  - `_run_discord_ephemeral_bot` 新增 `_watch_cancel()` 背景協程：每 0.4 秒檢查旗標，觸發時 `bot.close()` 中斷連線（解決連線階段無法取消）
  - 統一 `_finalize_cancelled()` 處理取消結束狀態
  - `classify` / `convert` / `news` / `crawl` 全面接入取消檢查
  - 取消 API 回傳最新 `run` 物件（含 `summary: 正在取消…`）

  **後端（`classifier.py`）**
  - `run_classifier(cancel_check=...)` 支援 Layer 1 / Layer 2 批次中斷，取消時保留已完成分類結果

  **前端（`discord.html`）**
  - 取消請求成功後**立即重設**停止按鈕（不再等 poll 成功）
  - 收到 API 回傳的 `run` 立即更新進度 UI
  - 若 worker 已死直接顯示「已取消」
  - 取消後改為每 1 秒輪詢，最多 60 秒

### 驗收方式
- 爬取任務在「建立 Discord 連線」階段點停止 → 數秒內變為 `已取消`，按鈕不再卡住
- 分類任務執行中點停止 → 可中斷並保留已分類部分
- 對殘留 `running` 任務點停止 → 立即標記 `cancelled`

---

## [0.6.8-alpha] - 2026-06-24

### Changed
- **對話泡移出 canvas-wrap**：將 `.ai-vrm-assistant-speech` 從 `.ai-vrm-assistant-canvas-wrap` 內部移至其上方（HTML 層級為兄弟節點，排列於 canvas-wrap 之前），使對話泡顯示於人物畫布上方，不再遮擋角色。
- **CSS 動畫改為 max-height 正常流**：移除原本的 `position: absolute`、`top`、`z-index` 與 `transform: scaleY` 動畫，改以 `max-height: 0 → 200px` 加 `margin-bottom` 過渡，動畫效果為由下向上展開；隱藏時元素高度收合至 0 不占空間；`overflow: visible` 於 `.is-visible` 時開放，確保下方箭頭（`::after`）正常顯示。

### 驗收
- 送出問題後，對話泡出現在 3D 人物上方，不覆蓋角色畫面。
- 對話泡展開動畫由下往上，收合時空間消失，不留白。
- 箭頭指向下方人物，視覺銜接正確。
- 明 / 暗主題切換後，泡泡背景與邊框色同步更新。

---

## [0.6.7-alpha] - 2026-06-24

### Documentation
- **`SPEC/DESIGN_SPEC.md` §19.4**：補充「D4 馬娘相關訊息辨識」完整規格
  - 三種狀態（`None` 待分類 / `True` 馬娘 / `False` 無關）
  - Layer 1 關鍵字子字串比對 + Layer 2 Gemini 批次確認流程
  - 短訊息（≤20 字）略過 AI、分類後資料流（NewsData / 推播）
  - 修正 §19.2 排程表與實作一致（classify 每 2 小時、convert 每日 01:00）

---

## [0.6.6-alpha] - 2026-06-24

### Added
- **UMA Info 伺服器總覽 — 即時統計刷新**

  **問題**：Discord Bot 在控制台已爬取大量訊息，但 Portal 伺服器管理頁「總覽」數字仍為 0 或不更新。原因為統計僅在**頁面初次載入（SSR）**時計算，無 API 可動態刷新；使用者若未手動重新整理頁面，數字不會變動。

  **後端**
  - 新增 `app_uma_info_portal/guild_stats.py`：`compute_guild_stats(guild_id)` 共用統計邏輯
  - 新增 `GET /uma-info/api/guilds/<guild_id>/stats/`（`api_guild_stats`）
  - 回傳：`msg_count`、`uma_count`、`pending_count`、`news_count`、`converted_count`、`channel_count`、`uma_pct`、`last_message_at`、`refreshed_at`
  - `server_manage` view 改為呼叫共用函式

  **前端（`server_manage.html`）**
  - 總覽 / 統計分頁新增「↻ 更新統計」按鈕
  - 頁面載入、切換至總覽/統計分頁、每 30 秒自動呼叫 stats API 更新數字
  - 顯示「統計時間」與「最新訊息時間」
  - 統計分頁修正「相關訊息比例」誤顯示為原始筆數的 bug（改為 `uma_pct`%）
  - 新增「待分類」「已轉 NewsData」統計卡

  **伺服器選擇頁（`servers.html`）**
  - 已安裝伺服器卡片顯示「已收集 N 則訊息」預覽，方便辨識哪個伺服器有資料

### 驗收方式
- 控制台爬取完成後，進入 `/uma-info/servers/<guild_id>/manage/` 總覽應顯示正確訊息數（或點「更新統計」/ 等待自動刷新）
- `GET /uma-info/api/guilds/<guild_id>/stats/` 回傳與 DB 一致的 `msg_count`

---

## [0.6.5-alpha] - 2026-06-24

### Changed
- **Phase 4：`services/news_service.py` 廢棄通知**
  - 為 `load_news_df()`、`NEWS_CSV`、`TOPKEY_CSV`、`TOP_CHARACTER_CSV`、`CHARACTERS_CSV` 加入廢棄說明
  - 說明每個常數/函式的 DB 替代方案（`NewsData.objects.filter(status='labeled')` 等）
  - 此模組在過渡期間仍可用作 fallback，不影響現有 CSV 工作流
  - 新程式碼不應再直接依賴此模組讀取主要分析資料

### Fixed
- **`app_crawler_admin/api_views.py` 語法錯誤（`except` 縮排錯置）**
  - `api_discord_channel_add()` 函式中，`except Exception as e:` 縮排誤置於 `try` 區塊內（return 之後）
  - 修正縮排，`except` 正確對齊 `try`

### 驗收方式
- `python manage.py check` 無語法錯誤
- 舊有 CSV 工作流（`load_news_df()`）仍可正常執行

---

## [0.6.4-alpha] - 2026-06-24

### Changed
- **Phase 3：三個分析 Views 改從 DB 讀取，保留 CSV fallback**
  - **`app_user_keyword/views.py`**：新增 `_load_df_from_db()` 優先讀 `NewsData(status='labeled')`；若 DB 無資料自動 fallback 至 CSV；保留 `df` 全域變數供 `app_user_keyword_association`、`app_user_keyword_sentiment`、`app_correlation_analysis` 借用，**不破壞任何既有 views**
  - **`app_uma_top_keyword/views.py`**：新增 `_load_topkey_data()` 以 `Max(computed_date)` 取最新快照，讀 `TopKeyword.objects.filter(window_days=0, computed_date=latest)` 並按分類整理；fallback 至 CSV
  - **`app_uma_top_character/views.py`**：新增 `_load_topchar_data()` 讀 `TopCharacter` DB，fallback 至 CSV；`values_list('character', 'mention_count')` 回傳格式與原 CSV `eval()` 相容

### 驗收方式
- 啟動 Django Server，各分析頁面正常顯示（有資料 → DB；無資料 → CSV fallback）
- `[app_user_keyword] 從 DB 載入 N 筆` 日誌在 DB 有 labeled 資料時出現
- `fallback: 從 CSV 載入` 日誌在 DB 無資料時出現

---

## [0.6.3-alpha] - 2026-06-24

### Added
- **Phase 2d：`UmaCharacter` 角色靜態資料模型**
  - 新增 `UmaCharacter` 模型至 `app_user_keyword_db/models.py`：`name_tw`、`name_jp`、`name_en`、`icon_url`、`is_active`、`updated_at`
  - 產生對應 migration：`app_user_keyword_db/migrations/0004_add_umacharacter_model.py`
  - `generate_top_character_csv.py` 已可優先讀 `UmaCharacter` DB，fallback 至 bilingual CSV

### Changed
- **Phase 2b：pipeline 腳本雙輸出（CSV + DB）**
  - **`pipeline/preprocess.py`**：新增 Django ORM 整合；優先讀 `NewsData(status='raw')`，fallback CSV；斷詞結果 `bulk_update` 至 DB，`status` 改為 `'tokenized'`；CSV 仍同步輸出（向下相容）
  - **`pipeline/label_sentiment.py`**：新增 `--db` 旗標可改讀 `NewsData(status='tokenized')`；情感標記後 `bulk_update` `sentiment + status='labeled'`；CSV 仍同步輸出；新增 `_load_df_from_db()` / `_sync_sentiment_to_db()` 函式
  - **`scripts/generate_topkey_csv.py`**：新增 Django ORM；優先讀 DB，fallback CSV；計算結果 `bulk_create(update_conflicts=True)` 至 `TopKeyword` DB（`window_days=0, computed_date=today`）；CSV 仍同步輸出
  - **`scripts/generate_top_character_csv.py`**：同上，目標模型改為 `TopCharacter`；角色名稱優先讀 `UmaCharacter` DB，fallback bilingual CSV

- **Phase 2c：5 支網路爬蟲直寫 NewsData DB**
  - **`pipeline/crawl_bilibili_uma.py`**：`item_id` 改為 URL slug（`_make_item_id()`，`urllib.parse.unquote` + `/` → `_`），修復重爬偽新增問題；爬取後呼叫 `_upsert_to_db()` 寫 NewsData
  - **`pipeline/crawl_ettoday_uma.py`**：`append_row()` 加入 `_upsert_to_db()`，每篇即時同步至 DB（`status='raw'`）
  - **`pipeline/crawl_udn_uma.py`**：同上
  - **`pipeline/crawl_gamme_uma.py`**：同上
  - **`pipeline/crawl_bahamut_uma.py`**：同上
  - 所有爬蟲均加入 Django 環境設定（`django.setup()`），使用 `update_or_create` 防重複

### 驗收方式
- 執行任一爬蟲後，`NewsData.objects.filter(source=...)` 應有新筆數
- 執行 `python pipeline/preprocess.py` 後，已爬取的 `status='raw'` 筆數應改為 `'tokenized'`
- 執行 `python pipeline/label_sentiment.py --db` 後，`status='tokenized'` 改為 `'labeled'`
- 執行 `python scripts/generate_topkey_csv.py` 後，`TopKeyword.objects.count()` > 0
- `⚠️ Bilibili item_id 破壞性更動`：需清除舊 bilibili DB 資料及 CSV，重新爬取以避免新舊 ID 混用

---

## [0.6.2-alpha] - 2026-06-24

### Fixed
- **Discord 任務停止按鈕卡在「取消中…」狀態**

  **根本原因：** `pollTask()` 的 `catch` 只顯示 toast，**不重設按鈕狀態**，導致輪詢失敗一次後按鈕永遠停在「⏸ 取消中…」，必須手動重新整理頁面才能恢復。

  **修復項目：**

  **前端（`discord.html`）**
  - 新增 `_resetStopBtn()` 輔助函式，統一重設按鈕狀態
  - 新增 `_checkAndSyncTaskStatus()` — 靜默取得最新任務狀態、若已非 running 則立即更新 UI、停止計時器
  - `cancelTask()`：送出取消成功後，以 `setTimeout(_checkAndSyncTaskStatus, 3000/8000)` 主動在 3 秒、8 秒後各確認一次狀態，不依賴 poll 成功才更新
  - 新增 `_pollFailCount` 計數器：每 3 次失敗 toast 一次（避免刷屏）；≥3 次後觸發 `_checkAndSyncTaskStatus` 靜默同步

  **後端（`api_views.py`）**
  - crawl task worker：在呼叫 `_run_discord_ephemeral_bot` **之前**先檢查 `_CANCEL_FLAGS`；若取消在連線前已請求，立即標記 `cancelled` 並返回，不進行 Discord 連線
  - `_TempBot.on_ready`：Discord 連線成功後**立即再次**檢查 `_CANCEL_FLAGS`，若旗標已設定則直接 `raise CrawlCancelledError` 並關閉 Bot，避免連線期間送出的取消請求被忽略直到第一個頻道

### 驗收方式
- 點擊「停止任務」後 3–5 秒內，按鈕應自動從「⏸ 取消中…」恢復為隱藏（任務結束）
- 即使 polling 失敗（網路抖動），按鈕最多在 8 秒後自動重設
- 在 Discord 連線建立前點擊停止，任務應立即標記 cancelled 而非等待連線完成

---

## [0.6.1-alpha] - 2026-06-24

### Added
- **Discord 訊息查閱 — 點擊查看完整訊息詳情 Modal**

  解決列表中訊息內容被截斷（`truncatechars` / `ellipsis`）無法完整查閱的問題。

  **前端（`discord.html`）**
  - 新增 Bootstrap Modal「訊息詳情」，顯示：訊息 ID、發送時間、爬取時間、伺服器、頻道、作者、分類、分類方式、NewsData 轉換狀態、完整訊息內容（可捲動、`pre-wrap` 保留換行）
  - 表格列可點擊開啟詳情；新增「查看」操作欄；勾選框與操作欄不觸發列點擊
  - 詳情頁提供「複製內容」「複製訊息 ID」「在 Discord 開啟」（需 guild/channel/msg ID 齊全）快捷操作
  - 以 `msgCache` 快取目前頁面訊息；若快取未命中則以 `msg_id` 向 API 補查

  **後端（`api_views.py`）**
  - `GET /api/discord/recent_messages/` 新增 `msg_id` 篩選參數（單筆查詢）
  - 回應新增 `created_at`（爬取入庫時間）欄位

### 驗收方式
- 在 `/crawler-admin/discord/` 訊息列表點擊任一行或「查看」→ Modal 顯示完整內容與中繼資料
- 長訊息可在 Modal 內捲動閱讀；複製與 Discord 連結可用

---

## [0.6.0-alpha] - 2026-06-24

### Fixed
- **LookAt Y 軸上下反轉修正**：`on_mouse_move` 中 `dy` 原本取負號，導致滑鼠在容器下方時模型反而往上看。DOM Y 軸向下為正、Three.js 正 pitch 為向前傾（看下方），方向本已一致，移除負號後行為正確。
  - 影響範圍：`static/app_dashboard/js/ai-vrm-assistant.js`

### Changed
- **預設問題替換**：`幫我統整負面評論` 改為 `能帶我瀏覽本平台嗎?`，並新增 `FIXED_REPLIES` 機制；觸發時直接顯示固定文字「你沒有手嗎?平台就這麼大，自己去滑一滑」，不發送 API 請求。
  - 影響範圍：`templates/base.html`、`static/app_dashboard/js/ai-vrm-assistant.js`
- **鏡頭向下平移**：`frame_upper_body` 中 `pan_up` 由 `0.32` 降至 `0.05`，構圖重心下移。
  - 影響範圍：`static/app_dashboard/js/ai-vrm-assistant.js`
- **預設提問區背景全透明**：移除 `.ai-vrm-assistant-presets` 的漸層底襯，改為 `background: transparent`。
  - 影響範圍：`static/app_dashboard/css/ai-vrm-assistant.css`
- **對話泡泡改為由下向上伸展動畫**：隱藏狀態改為 `transform: scaleY(0.05); transform-origin: bottom center`，出現時 `scaleY(1)` 搭配彈性 cubic-bezier，視覺上從底部向上展開。
  - 影響範圍：`static/app_dashboard/css/ai-vrm-assistant.css`
- **Canvas 出血區域（防截切）**：`canvas-wrap` 改為 `overflow: visible`；canvas 元素以 `position: absolute` 超出容器上方 28px、左右各 14px（CSS）；JS 端新增 `CANVAS_BLEED_TOP = 28 / CANVAS_BLEED_SIDE = 14`，renderer/camera aspect 一致擴大，確保揮手等動作不被邊緣截切。手機版出血量 24/12px。
  - 影響範圍：`static/app_dashboard/js/ai-vrm-assistant.js`、`static/app_dashboard/css/ai-vrm-assistant.css`

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 與 `ai-vrm-assistant.css` 無 lint 錯誤。
- 待人工 `Ctrl + F5` 驗證：揮手不被截切、鏡頭構圖下移、泡泡由下展開、預設問題透明背景、`能帶我瀏覽本平台嗎?` 固定回覆、Y 軸視線正確。

---

## [0.5.9-alpha] - 2026-06-24

### Added
- **主站 3D 浮動 AI 虛擬客服「馬娘客服 成田路」**

  在主站全站 `templates/base.html` 右下角新增常駐 3D AI 虛擬客服，以 VRM 模型（`1077_Narita_Top_Road.vrm`）渲染成田路角色，串接既有 Django Agentic AI 端點 `POST /agent/chat/`。

  **靜態資產**
  - `static/app_dashboard/vrm/1077_Narita_Top_Road.vrm`（VRM 模型）
  - `static/app_dashboard/js/ai-vrm-assistant.js`（渲染 + 互動 + API 串接）
  - `static/app_dashboard/css/ai-vrm-assistant.css`（毛玻璃聊天框、泡泡、容器樣式）

  **前端依賴（import map CDN）**
  - `three@0.160.0`、`@pixiv/three-vrm@2.1.3`
  - 以 `<script type="importmap">` 統一 THREE 實例，避免 MToon 材質雙份 THREE 衝突

  **3D 渲染技術重點**
  - 透明背景 `WebGLRenderer(alpha:true)`；三點打光（主光/補光/輪廓光）+ AmbientLight + HemisphereLight
  - `VRMUtils.rotateVRM0(vrm)` 確保 VRM0 模型面向鏡頭；`frustumCulled = false` 防止 SkinnedMesh 誤剔除
  - **絕對安全座標框景**（禁用 `THREE.Box3`）：取 `head` 骨骼世界高度加防呆夾擠，固定安全距離 `0.9`，解決 SpringBone 第 0 幀異常邊界導致畫面全黑的問題

  **VRM 骨骼偏移修正**（此模型 PMX→VRM 自動轉檔誤標骨骼）
  - `leftUpperArm` 實際綁到肩膀骨、`leftLowerArm` 才是真大臂，依此修正自然站姿旋轉軸
  - `head` 槽實際綁到緞帶彈簧骨，VRM 內建 bone LookAt 失效 → 改以 `scene.getObjectByName('Head')` 直接操控真實頭骨

  **四階段狀態機（平滑 Lerp 過渡）**
  - `welcoming`：載入完成即觸發 2.5 秒揮手 + `happy=1.0`，結束後自動回 idle
  - `idle`：spine 呼吸（`±0.022 rad`）+ head/neck 隨機相位正弦微動，`happy=0.18`
  - `listening`：input focus 時頭部前傾 + 側傾、專注表情
  - `talking`：解說手勢 + `aa/ih` 偽唇形同步，持續時長依回覆長度 clamp

  **局部座標 LookAt 視線追蹤**
  - 有效半徑 `400px`；半徑外平滑歸位；`look_nx/look_ny` 每幀 `lerp(0.08)` 趨近頭骨旋轉目標

  **聊天 UI**
  - 毛玻璃輸入框（`backdrop-filter: blur`）+ 角色上方回覆泡泡（淡入淡出）
  - 5 組預設提問快捷按鈕
  - Enter 送出、空字串阻擋、loading 期間禁用重複送出

  **API 串接（`/agent/chat/`）**
  - `X-CSRFToken` cookie 讀取 + JSON body；回應欄位容錯解析（`reply`/`message`/`response`）
  - HTTP 非 2xx 顯示狀態碼，fetch 例外顯示網路錯誤，解析失敗提示格式錯誤

  **文件**
  - `plan/3d-ai-virtual-cs-plan.md`（實作計畫）
  - `SPEC/3d-ai-virtual-cs-spec.md`（完整技術規格，含骨骼偏移表、框景地雷說明）

### Tests
- `python manage.py check`：無錯誤
- `python manage.py test app_agent_uma.tests`：`/agent/chat/` JSON 請求與主站掛載點均通過

### Known Notes
- 測試環境出現 SciPy / NumPy 版本警告，非本功能引入，不影響驗收

---

## [0.5.8-alpha] - 2026-06-24

### Added
- **Discord 爬取任務取消功能（停止任務按鈕）**

  **後端（`crawler.py`）**
  - 新增 `CrawlCancelledError(Exception)` 例外類別
  - `crawl_all_channels` / `crawl_guild` 新增 `cancel_fn: CancelFn` async callback 參數
  - `crawl_all_channels` 在每個**伺服器**迭代前呼叫 `cancel_fn()`；`crawl_guild` 在每個**頻道**迭代前同樣檢查
  - 若旗標已設定，記錄 `⛔ 偵測到取消請求` 日誌並 `raise CrawlCancelledError`

  **後端（`api_views.py`）**
  - 新增全域 `_CANCEL_FLAGS: dict[int, bool]` 記憶體旗標（run_id → True）
  - 新增 `api_discord_task_cancel(request, run_id)` 端點（`POST`）：設定旗標、在日誌追加提示、回傳 `{status: cancel_requested}`
  - crawl 任務 worker 加入 `cancel_fn` async callback（讀取 `_CANCEL_FLAGS`）
  - 以 `try/except CrawlCancelledError / finally` 包覆 crawl 執行，取消時寫入 `status='cancelled'`；`finally` 清除旗標避免記憶體洩漏

  **路由（`urls.py`）**
  - 新增 `POST /crawler-admin/api/discord/task/<run_id>/cancel/`

  **前端（`discord.html`）**
  - 新增「⏹ 停止任務」按鈕（`#btnStopTask`），僅在 `.is-running` class 存在時顯示
  - 新增 `cancelTask()` JS 函式：`confirm()` → 呼叫取消 API → 顯示 toast + 日誌行 → 繼續 polling
  - 按鈕點擊後顯示「⏳ 取消中…」並 disable，任務結束後自動復位
  - `updateTaskProgressUI()` 在 `isRunning = false` 時重設停止按鈕狀態

### 驗收方式
- 任務執行中，進度標頭右側應顯示紅色「⏹ 停止任務」按鈕
- 點擊並確認後，按鈕顯示「⏳ 取消中…」，日誌出現 `⚠ 已送出取消請求…`
- 最多完成當前頻道後，日誌出現 `⛔ 偵測到取消請求…`，任務狀態變為 `cancelled`，進度條變灰
- 任務完成/失敗/取消後，停止按鈕隱藏

---

## [0.5.7-alpha] - 2026-06-24

### Added
- **`crawler.py` — 逐伺服器 / 逐頻道 async progress callback**
  - `crawl_channel`、`crawl_guild`、`crawl_all_channels` 新增可選 `log_fn(msg)` / `progress_fn(pct, summary)` async callback 參數
  - `crawl_guild` 在每個頻道爬取完成後立即呼叫 `progress_fn`，以 `guild_index / guild_total × 70%`（15%–85%）精準計算細粒度進度百分比
  - `crawl_all_channels` 在連線後立即輸出「加入 N 個伺服器」並初始化進度
  - 每個頻道輸出結構化日誌（`✓ #頻道名：+N 筆` / `✗ 頻道：無讀取權限`），伺服器標頭以 `▶ [N/M] 名稱 · 範圍 · 頻道數` 格式標示
  - 舊版（Scheduler 等）不傳 callback 時保持向後相容

- **`api_views.py` — crawl 任務接入 async callback**
  - 將 `_append_task_log` 與 `_update_task` 包裝為 `sync_to_async` 安全 async callback，傳入 `crawl_all_channels`
  - 任務啟動後先輸出「⏳ 正在連線至 Discord Gateway…」，連線成功後即輸出 Bot 帳號與伺服器總數

- **`discord.html` — 任務進度 UI 全面強化**
  - **即時統計欄（Stats Strip）**：任務執行中顯示「伺服器 N/M」、「頻道 A/B」、「累積新訊息 +C 筆」，數值由 summary 字串即時解析更新
  - **彩色日誌分級**：新增 `log-hdr`（藍粗體，伺服器標頭）、`log-warn`（黃色，警告/略過）、`log-sub`（暗灰，縮排補充說明）CSS class；`colorLogLine()` 新增對 `▶`、`↳`、`✓`、`✗`、`⚠`、`⏳` 等符號的識別
  - **自動捲動開關**：新增「↓ 自動捲動 / ⏸ 自動捲動」按鈕，預設開啟，可暫停以手動閱讀上方日誌
  - **日誌行數統計**：改用正則計算純行數，移除 HTML 標籤干擾
  - **日誌框高度**：從 300px 擴充至 400px

### Changed
- `updateTaskProgressUI`：執行中時標題改為「任務名稱 + 小字 summary」二段顯示，避免長摘要截斷進度標題

### 驗收方式
- 點擊「爬取頻道訊息」後進度區應顯示：`⏳ 正在連線` → `✓ 已連線 · Bot: XXX · N 個伺服器` → 逐頻道 `✓ #name: +N 筆` → 伺服器進度 `▶ [1/2]` 標頭，統計欄即時更新 → 100% `✅ 完成`
- 存在無讀取權限頻道時，對應行以黃色 `⚠` 顯示，不影響整體爬取

---

## [0.5.6-alpha] - 2026-06-24

### Fixed
- **`crawler.py` — Django ORM `SynchronousOnlyOperation` 根治**：`crawl_channel`、`crawl_guild`、`crawl_all_channels` 均為 async 函式，在 `on_ready` async context 中直接呼叫 Django ORM（`DiscordMessage.objects.filter()`、`bulk_create()`、`GuildSetting`、`GuildChannelRule` 等）觸發 `SynchronousOnlyOperation: You cannot call this from an async context` 錯誤，導致所有伺服器爬取全部靜默失敗、資料庫維持 0 筆
  - **修復方式**：將所有 ORM 操作抽出為獨立同步輔助函式（`_get_last_msg_timestamp`、`_bulk_create_messages`、`_get_guild_scope`、`_get_fallback_channel_ids`），並在 async 函式中以 `sync_to_async(fn)(args)` 形式呼叫，完全符合 Django async 安全規範
  - **驗收確認**：修復後實際爬取 2 個伺服器，成功寫入 **2105 筆** `DiscordMessage`，無 ORM 相關錯誤

---

## [0.5.5-alpha] - 2026-06-24

### Fixed
- **全站深色主題稽核（第二輪）— 前台頁面硬編碼淺色背景修正**：在 0.4.20 修正控制台後，全面掃描主專案所有 53 個模板，發現以下前台頁面存在深色主題下淺色背景 / 文字對比失效問題：

  - **`app_dashboard/templates/app_dashboard/dashboard.html`（4 處）**：儀表板統計卡片圖示圓圈（`.stat-icon`）使用硬編碼淺色柔和底色（`#ede9fe` 紫、`#dcfce7` 綠、`#fef9c3` 黃、`#fee2e2` 紅），深色主題下淺底 + 深色圖示顏色失效。改以語意色 class（`.stat-icon-purple/green/amber/red`）並新增 `[data-theme="dark"]` 覆寫（半透明強調底 + 淺色圖示文字）。

  - **`app_discord_bot/templates/app_discord_bot/dashboard.html`（1 處）**：「新增頻道」Collapse 表單容器 `style="background:#f8f9ff;"` 為淺藍白，深色主題下形成顯眼淺色區塊。改為 `var(--color-bg-elevated)`。

  - **`app_agent_uma/templates/app_agent_uma/home.html`（3 處）**：POA Agent 聊天頁繼承舊版 Bootstrap 聊天樣式：`.chat-box` 使用 `#f9f9f9`，`.bot .msg` 使用 `white` 氣泡，深色主題下均為嚴重白底區塊。全部改為主題變數：`.chat-box` → `var(--color-bg-base)` + `var(--color-border)`；`.bot .msg` → `var(--color-bg-elevated)` + `var(--color-border)` + `var(--color-text-primary)`；`.user .msg` → `var(--color-accent)`（取代 Bootstrap 藍 `#0d6efd`，深淺主題皆適配）。

### Notes（稽核確認正常、無需修改的項目）
- **`app_agent_langgraph/chat.html`、`app_agent_langchain/chat.html`**：整體設計為「永遠深色介面」（仿終端機 / AI Chat），與後台 log 面板同屬刻意設計，保留。
- **`app_uma_info_portal/home.html` Discord 訊息模擬框**：`.discord-mockup { background: #313338 }` 模擬 Discord 深色 UI，保留。
- **`#5865F2` Discord 品牌藍**：出現於 `app_discord_bot`、`app_uma_info_portal`、`app_course_intro`，品牌識別色，高彩度白字對比充足，雙主題均可讀，保留。
- **`app_comment_sentiment`、`app_character_pk`、`app_uma_top_keyword/character`、`app_user_keyword*` 等前台功能頁**：全部已使用 `var(--color-*)` 主題變數，無需修改。
- **`app_poa_introduction/course-introduction.html`**：使用獨立靜態資源集（`assets_course_intro/`），無主題切換，低優先級靜態展示頁，待未來整合時重構。

### 影響範圍
- `app_dashboard/templates/app_dashboard/dashboard.html`
- `app_discord_bot/templates/app_discord_bot/dashboard.html`
- `app_agent_uma/templates/app_agent_uma/home.html`

## [0.5.4-alpha] - 2026-06-24

### Fixed
- **Windows asyncio 執行緒相容性修復（`app_crawler_admin/api_views.py`）**：手動爬取任務（`crawl`）與手動推播任務（`news`）在背景執行緒中透過 `_run_discord_ephemeral_bot` 建立臨時 Discord Bot 時，Windows 預設的 `ProactorEventLoop` 因執行緒親和性限制導致 WebSocket 永久卡住（`on_ready` 從不觸發，任務停在「建立 Discord 連線 15%」無法完成）
  - **修復方式**：在 Windows（`os.name == 'nt'`）環境下改用 `asyncio.SelectorEventLoop`（基於 `select()` 系統呼叫，無執行緒親和性限制），並明確以 `loop.run_until_complete()` 執行 `_main()`；非 Windows 環境維持 `asyncio.run()` 不變
  - **影響範圍**：所有需要 Discord 連線的手動任務（爬取、推播）在 Windows 上均可正常執行
  - **驗收方式**：點擊「爬取頻道訊息」後 Log 出現「Bot 已連線，伺服器數: N」，任務正常跑完至 100%

---

## [0.5.3-alpha] - 2026-06-24

### Fixed
- **情報站控制台深色主題文字 / 顏色不隨主題切換（核心修復）**：控制台多數頁面切換到深色主題時，文字與卡片顏色未跟著轉換，導致深色背景下文字偏暗難以閱讀。根因為 `app_crawler_admin` 全部 12 個頁面（`dashboard`、`stats`、`schedule`、`history`、`pipeline`、`settings`、`youtube`、`discord`、`rag`、`live_monitor`、`data_manager`、`ai_news`）沿用設計原型的**簡寫 CSS 變數名**（`--text`、`--muted`、`--accent`、`--surface`、`--bg`、`--card` / `--card-bg`、`--border`、`--accent-muted`、`--positive`、`--negative`、`--warning` 等），但 `design-system.css` 只定義了 `--color-*` 長名 Token，導致這些簡寫變數在實際站台上**全部未定義**：
  - 背景（`background:var(--surface/--card-bg/--bg)`）→ 解析為透明，卡片 / 區塊失去主題底色。
  - 文字（`color:var(--muted/--text/--accent)`）→ 因 `color` 可繼承而退回繼承值，無法取得正確的主題化次要 / 強調色，深色主題下對比不足、不夠分明。
  - 強調 / 邊框（`var(--accent)`、`var(--accent-muted)`）→ 失去堇紫強調色。
- **修復方式（單一根因修正，一處生效全站）**：於 `static/css/design-system.css` 的 `:root` 新增一組「簡寫別名 → `--color-*` 長名」對應（`--text: var(--color-text-primary)`、`--surface: var(--color-bg-surface)`、`--accent: var(--color-accent)`…）。別名引用會隨 `[data-theme]` 覆寫的 `--color-*`，靠 CSS 變數的點求值（use-site）特性自動具備亮 / 暗主題反應性，**無需**為每頁、每變數另寫深色覆寫。
- **Bootstrap 次要文字灰字缺口**：`.form-text`、`.form-check-label`、`small.text-muted` 先前沿用 Bootstrap 預設灰（`#6c757d`），於深色卡片上對比偏低。改綁 `--color-text-secondary`，深淺主題皆可讀（影響 `settings.html` 等表單頁）。

### Notes（稽核結果）
- **稽核範圍**：`app_crawler_admin` 全部 12 個模板的 inline `style=` 與 `<style>` 區塊，共約 190 處變數引用。
- **確認無需修改**：既有「淺底 + 深字」徽章 / 標籤皆已備有 `[data-theme="dark"]` 覆寫（`rag.html` 的 `.index-ok/.index-no`、`discord.html` 的 `.pill-*` / `.btn-icon.danger:hover`）；終端機 / log 面板（`#0d1117` 底 + `#c9d1d9` 字）為刻意永遠深色設計，半透明強調底（`rgba(...,.08)`）搭配高彩度文字雙主題皆可讀，均保留。
- **規格化**：於 `SPEC/DESIGN_SPEC.md` 新增「22.6 CSS 變數命名契約」，明訂 `--color-*` 為唯一真實來源、簡寫別名只在 `:root` 定義一次且禁止另寫 dark 覆寫，以及顏色硬編碼的禁用 / 例外規範，杜絕後續復發。
- Django `python manage.py check`：0 issues。

### 影響範圍
- `static/css/design-system.css`（新增簡寫變數別名 + `.form-text` 等次要文字主題化）
- `SPEC/DESIGN_SPEC.md`（新增 §22.6）

## [0.5.2-alpha] - 2026-06-24

### Changed
- **Discord 任務面板 UI 全面翻新（`discord.html`）**：
  - **進度區塊預設可見**：`task-progress-wrap` 不再預設隱藏，頁面載入時即顯示「等待任務啟動…」佔位狀態
  - **執行中動畫**：新增黃色脈動指示點（`.task-running-dot`）與進度條 shimmer 動畫，清楚標示任務運行中
  - **彩色日誌輸出**：`✅` 開頭顯示綠色、`❌`/error 顯示紅色、`▶`/`[` 顯示藍色，一眼辨識成功/失敗/資訊
  - **日誌工具列**：新增「捲到頂部 / 底部 / 清除」按鈕，以及目前行數計數器
  - **進度條狀態顏色**：成功時綠色、失敗時紅色、取消時灰色，執行中紫色
  - **近期任務歷史**：進度區塊下方顯示最近 8 筆任務記錄（狀態徽章 + 摘要 + 百分比），點擊任一筆即可載入其日誌
  - **頁面載入自動還原**：`initTaskPanel()` 在初始化時呼叫 `api_discord_task_status`，若偵測到進行中的任務，自動附加輪詢並還原進度/日誌顯示

### Fixed
- **訊息查閱區塊空白問題**：根因為任務卡住（ProactorEventLoop bug，見 v0.4.19），爬取任務從未完成，資料庫無任何 `DiscordMessage` 記錄；Windows asyncio fix 套用後重新執行爬取即可取得資料
- **殘留「卡住中」任務自動清理**：`initTaskPanel()` 不再自動重啟殘留任務，但會自動附加顯示其日誌；DB 中 `running` 但實際執行緒已死的任務可在頁面看到狀態後手動重新觸發

**驗收方式**：
1. 頁面開啟後進度面板立即可見（不需點任何按鈕）
2. 點擊「爬取頻道訊息」後出現黃色動畫點、進度條逐步更新、日誌滾動顯示
3. 任務完成後進度條變綠、歷史記錄更新

---

## [0.5.1-alpha] - 2026-06-24

### Added
- **推播頻道設定後 Embed 確認（`app_uma_info_portal`）**：儲存推播設定時若頻道有異動，Bot 即時向該頻道發送確認 Embed，內含伺服器名稱、推播開關、語氣、Ping 身分組等資訊；Bot 離線時前端顯示「將於 Bot 上線後補發」提示
- **`POST /uma-info/api/guilds/<guild_id>/confirm-news-channel/`**：新增獨立確認端點，可手動重送確認 Embed
- **`GuildChannelCache.bot_can_read` / `bot_can_send`**：頻道快取新增兩個 Bot 實際權限欄位（`view_channel+read_message_history`、`send_messages+embed_links`），由 `run_discord_bot.py` 同步時以 `permissions_for(guild.me)` 即時計算並寫入

### Changed
- **推播頻道下拉清單限制為有發訊息權限的頻道**（`server_manage.html`）：「推播設定」面板的頻道選單改用 `sendable_channels`，無 `send_messages` 或 `embed_links` 權限的頻道不列出；「頻道讀取」面板的指定頻道與進階規則選單改用 `readable_channels`，無讀取權限的頻道不列出
- **移除 Portal 推播時程設定**（`server_manage.html`、`api_views.py`）：「推播時程」區塊（頻率 / 整點時間）已從伺服器管理頁移除；`ALLOWED_FIELDS` 不再接受 `news_frequency` / `news_hour`；頁面新增說明提示「時程由後台控制台統一管理」
- **`views.py` 傳遞分組頻道列表**：`server_manage` view 改為分別傳遞 `channels`（全部）、`readable_channels`（可讀）、`sendable_channels`（可傳訊）至模板
- **`run_discord_bot.py` 頻道同步記錄 Bot 權限**：`_sync_guild_to_db` 對每個頻道呼叫 `permissions_for(guild.me)` 並寫入 `bot_can_read` / `bot_can_send`

### Migration
- `app_uma_info_portal 0002_channel_bot_permissions`：`GuildChannelCache` 新增 `bot_can_read`、`bot_can_send` 欄位（預設 `True`，已套用）

**影響範圍**：`app_uma_info_portal`（models/views/api_views/urls/template）、`app_discord_bot/management/commands/run_discord_bot.py`
**驗收方式**：
1. 同步快取後「頻道讀取」與「推播設定」下拉僅顯示有對應權限的頻道
2. 儲存推播頻道後 Discord 該頻道收到確認 Embed
3. 推播設定面板不再顯示「推播時程」區塊

---

## [0.5.0-alpha] - 2026-06-24

### Added
- **資料管理頁 `/crawler-admin/data-manager/`（Phase 1）**：
  - 新增 `data_manager` view（`app_crawler_admin/views.py`），路由 `crawler-admin/data-manager/`。
  - Sidebar 新增「資料管理」導覽連結（`base_admin.html`）。
  - 新增 template `data_manager.html`：
    - NewsData 各來源 / 各 status 統計卡片（頁面載入自動刷新）
    - 按來源批次清除（網路來源一鍵、個別來源按鈕，Discord/YouTube 需個別確認）
    - 按日期範圍清除（可選限定來源）
    - 按 `item_id` 精確刪除單筆
    - status 重設（重設為 `raw` 或 `tokenized`，觸發重新處理）
    - 資料品質掃描（null date、空標題/內容、未標記筆數、Bilibili 舊格式 item_id 計數）
    - 操作日誌區（顯示每次操作結果）
  - 新增 6 個 REST API 端點（`api_views.py` + `urls.py`）：
    - `GET  /api/data-manager/stats/`
    - `POST /api/data-manager/clear-source/`
    - `POST /api/data-manager/clear-date/`
    - `POST /api/data-manager/delete-item/`
    - `POST /api/data-manager/reset-status/`
    - `GET  /api/data-manager/scan/`
  - 影響範圍：`app_crawler_admin`（view/api_views/urls/templates/base_admin）
  - 驗收：`python manage.py check` 無錯誤；`/crawler-admin/data-manager/` 回 200 且統計卡片顯示正確

## [0.4.29-alpha] - 2026-06-24

### Added
- **`NewsData.status` 欄位 + migration**（Phase 2a）：`app_user_keyword_db/models.py` 新增 `status` CharField（`raw/tokenized/labeled`，`db_index=True`），預設 `raw`。Migration `0003_newsdata_status.py` 已套用。
- **`TopKeyword` 模型 + migration**（Phase 2a）：`app_uma_top_keyword/models.py` 新增 `TopKeyword` 模型（`keyword`, `category`, `freq`, `source`, `window_days`, `computed_date`；`unique_together` 含 `window_days` + `computed_date`；含複合索引）。`migrations/0001_initial.py` 已套用。
- **`TopCharacter` 模型 + migration**（Phase 2a）：`app_uma_top_character/models.py` 新增 `TopCharacter` 模型（`character`, `category`, `mention_count`, `source`, `window_days`, `computed_date`；`unique_together` + 複合索引）。`migrations/0001_initial.py` 已套用。
  - 影響範圍：`app_user_keyword_db`、`app_uma_top_keyword`、`app_uma_top_character`
  - 驗收：`python manage.py check` 無錯誤；`python manage.py migrate` 回 OK

## [0.4.28-alpha] - 2026-06-24

### Added
- **`SPEC/DB_PIPELINE_MIGRATION_PLAN.md`（架構計畫新增）**：建立資料全程 DB 化遷移計畫文件，涵蓋目標架構、模型設計、腳本遷移清單、前台 views 遷移清單、分階段遷移順序及風險評估。
  - 影響範圍：SPEC 文件層（無程式碼異動）
  - 驗收方式：文件存在且各章節互相一致無矛盾

### Changed
- **`SPEC/DB_PIPELINE_MIGRATION_PLAN.md` v1.1（第一輪 SPEC Review 修訂）**：修正 7 項問題（3 高 + 2 中 + 2 低）：
  1. **架構圖狀態一致性**（高）：移除 `published`（屬 `GeneratedNewsArticle`，非 `NewsData`）；補充兩表 `status` 語意分離說明。
  2. **`--clear` 語意精確化**（高）：Phase 1 說明改為「清除網路來源（5 源），Discord/YouTube 保留」，避免執行人誤刪全部資料。
  3. **Bilibili `item_id` 穩定化**（高）：新增 §4 前置條件，說明改用 URL 頁面 slug 作為穩定鍵，並補充破壞性改動遷移步驟。
  4. **文件同步切換點**（中）：新增 §10，定義 `DESIGN_SPEC.md` 從 CSV 主流程切換為 DB 主流程的明確條件與需更新段落。
  5. **`TopKeyword`/`TopCharacter` 維度補齊**（中）：`unique_together` 補加 `window_days`、`computed_date`，防止歷史計算結果被覆寫。
  6. **計畫建立 CHANGELOG 補錄**（中）：補充本次 CHANGELOG 記錄（本條）。
  7. **`app_character_pk` 說明修正**（低）：該 app 讀取角色對戰靜態資料，非新聞資料，移出遷移範圍。
  - 影響範圍：SPEC 文件層（無程式碼異動）
  - 驗收方式：文件各章節互相一致，開放問題 §12 全數定案

## [0.4.27-alpha] - 2026-06-24

### Changed
- **`SPEC/DB_PIPELINE_MIGRATION_PLAN.md` v1.4（第三輪 SPEC Review 修訂）**：修正 4 項問題：
  1. **CHANGELOG 版本號重複修正**（高）：SPEC 建立 + v1.1 條目由 `0.4.13-alpha`（與 3D 雙臂修復重複）重新編號為 `0.4.16-alpha`，消除重複。
  2. **v1.3 計數口徑統一**（中）：SPEC 標頭改為「6 條修訂，涵蓋 11 個程式碼單元」，並補充口徑說明（SPEC 表格列數 vs 程式碼單元數 vs CHANGELOG 修訂內容項目）。
  3. **Top* 最新快照查詢契約**（中）：§6a 補充兩步查詢模式（先取 `Max(computed_date)`，再 filter），並附 graceful fallback 要求，確保前台不會混入歷史快照或因 `computed_date=None` 誤撈全部資料。
  4. **§10 文件切換點擴充**（中）：新增 Phase 2d 驗收條件；補列 `TASK_SPEC.md` 為第二個需同步更新的文件，並明確列出需更新的具體段落（Pipeline 驗收條件、分析 App 驗收條件、TopKeyword 計算任務驗收）；補充「若 SPEC 衝突以本計畫為準」的裁決規則。
  - 影響範圍：SPEC 文件層（無程式碼異動）
  - 驗收方式：`rg "## \[0\." CHANGELOG.md` 無重複版本號；§6a 查詢範例可正確取最新快照

## [0.4.26-alpha] - 2026-06-24

### Changed
- **`SPEC/DB_PIPELINE_MIGRATION_PLAN.md` v1.3（全專案 CSV 審計補完）**：執行全專案 CSV 使用點掃描，補入 v1.2 前遺漏的 14 個計畫外項目：
  1. **§3.4 新增 `UmaCharacter` 模型**：角色靜態資料（中日文名、圖示 URL）DB 化設計，取代 `uma_characters_bilingual.csv`。
  2. **§5b 角色資料爬蟲 3 支**：`crawl_uma_bilingual.py`、`crawl_uma_characters.py`、`crawl_uma_icons.py`，計畫改寫為寫入 `UmaCharacter` DB，列入 Phase 2d。
  3. **§5b 評論/PK 爬蟲 2 支**：`crawl_uma_comments.py`、`crawl_comments_extended.py`，目前依賴 `bilingual.csv`，Phase 2d 後改讀 `UmaCharacter` DB；`uma_comments_as_news.csv` 改直接寫 `NewsData`。
  4. **§5c 輔助腳本 3 支**：`recrawl_failed.py`（Phase 2c 後改 DB-based）、`preprocess_multisource.py`（Phase 2b 後廢棄）、`import_multisource_raw.py`（已完成任務，立即廢棄）。
  5. **§5d `services/news_service.py` 廢棄清單**：明確列出 Phase 4 廢棄的所有常數與函式及對應替代方案。
  6. **§6a 補入 2 個 App**：`app_user_keyword_association`、`app_correlation_analysis` 均間接依賴 CSV，列入 Phase 3 遷移，並補充「需同步改寫，不能只改 user_keyword」的注意事項。
  7. **§6b 補入 2 支 Management Command**：`app_comment_sentiment` scrape_bahamut（Phase 2c）、`app_uma_news` import_uma_data（Phase 3）。
  8. **§9 新增 Phase 2d**：角色靜態資料 DB 化完整遷移步驟。
  9. **§14 新增 POA 示範 App 處置策略**：5 支舊示範 App 明確標注「維持現狀，不列入主線遷移」。
  10. **§15 新增全專案 CSV 審計摘要表**：38+ CSV 讀寫點彙整，計畫涵蓋度一目瞭然。
  - 影響範圍：SPEC 文件層（無程式碼異動）
  - 驗收方式：§15 審計摘要表計數與實際程式碼點位一致

## [0.4.25-alpha] - 2026-06-24

### Changed
- **`SPEC/DB_PIPELINE_MIGRATION_PLAN.md` v1.2（第二輪 SPEC Review 修訂）**：修正 3 項遺漏問題：
  1. **Bilibili slug 正規化規則**：§4 補充 `/` 替換為 `_` 的正規化邏輯，並說明「若 item_id 暴露於路由則改用 SHA-1 hash」的安全策略，附修正後範例（`活動公告/2026` → `活動公告_2026`）。
  2. **計數不一致修正**：v1.1 修訂表格共 7 項，但文內及 CHANGELOG 誤寫為「5 個」；統一改為 7 項，並補列嚴重度欄。
  3. **現況問題清單狀態補標**：`--clear` 問題已於 `v0.4.9-alpha` 修復，§1 補標「✅ 已修」避免誤判為待解問題。
  - 影響範圍：SPEC 文件層（無程式碼異動）
  - 驗收方式：文件版本一致，§0 修訂說明計數與內容相符

## [0.4.24-alpha] - 2026-06-24

### Added
- **VRM 客服「成田路」靈動互動狀態機**：`static/app_dashboard/js/ai-vrm-assistant.js` 實作四態狀態機 `idle / welcoming / listening / talking`，全部骨骼/表情變化以 `THREE.MathUtils.lerp` 平滑過渡（禁止突變）。
  - **迎賓（welcoming）**：載入即右臂舉至胸前 + 正弦揮手（約 2 招）、`happy=1.0`，2.5s 後平滑放下回 idle。
  - **有機待機（idle）**：spine 呼吸 + head/neck 隨機相位微動，破除僵直。
  - **專注傾聽（listening）**：input focus/input 時頭部前傾 + 側傾、`relaxed`/`surprised` 微表情；失焦且空字串回 idle。
  - **對話偽唇形同步（talking）**：收到回覆時右手微抬解說手勢 + `aa`/`ih` 快速擺動模擬說話，時長依回覆長度估算，結束閉嘴回 idle。
- **局部座標追視（Localized LookAt）**：改以 `#ai-vrm-assistant-root` 容器中心 + 有效半徑 `400px` 為基準；半徑內頭部跟隨滑鼠、半徑外以 `lerp` 平滑回正。頭部旋轉新增 roll 軸（供傾聽側傾）。
- **預設提問藥丸 UI**：`templates/base.html` 於氣泡與輸入框之間新增 `.ai-vrm-assistant-presets`（5 顆預設問題）；`ai-vrm-assistant.css` 新增毛玻璃藥丸樣式、hover 上浮發光；點擊即填入並提問。
- **修改方案文件**：新增 `plan/3d-ai-vrm-interactive-statemachine-plan.md`。

### Changed
- **表情/姿勢改為每幀通道化套用**：以 `pose_current/target`、`expr_current/target` 通道 + lerp 取代先前一次性 `setValue`；移除舊的 `flash_expression()`（改由 talking 狀態處理）。
- **DOM 選擇器精確化**：輸入框/送出鈕改用 `.ai-vrm-assistant-chat input/button`，避免誤抓新增的預設按鈕。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 與 `ai-vrm-assistant.css` 無 lint 錯誤。
- 待人工 `Ctrl + F5` 驗證四態動畫、局部追視回正、預設按鈕提問。

## [0.4.23-alpha] - 2026-06-24

### Added
- **VRM 角色資料導出工具**：新增 `scripts/export_vrm_info.py`，解析 VRM（GLB/二進位 glTF）並導出角色全部資料到單一 `.txt`（檔案資訊、VRM Meta/授權、humanoid 骨骼對應表、表情清單、LookAt 設定、材質/網格/全部 node 名稱）。輸出 `narita-top-road-vrm-data.txt`。

### Fixed
- **3D 虛擬客服姿勢/視線長期問題的根因確認與根治（核心修復）**：由導出資料確認此模型 humanoid 對應「整體位移一節」（PMX→VRM 自動轉檔誤標）——`leftUpperArm` 槽實為肩膀 `Shoulder_L`、`leftLowerArm` 槽才是真大臂 `Arm_L`、`leftHand` 槽是真前臂 `Elbow_L`、`head` 槽被綁到緞帶彈簧骨、且無 `leftShoulder`/eye 骨。這解釋了先前所有「肩膀塌陷、手臂位移、視線追不到」的怪象（其實一直在轉錯骨頭）。
  - 站姿修正：`apply_rest_pose()` 改為「放下大臂 → 轉 `lowerArm` 槽、彎手肘 → 轉 `hand` 槽、肩膀槽不動」，根治塌陷與位移。
  - 視線修正：humanoid `head` 槽是緞帶骨、VRM bone LookAt 失效；改以 `getObjectByName('Head')` 取真實頭骨，於 `tick()` 在世界空間疊加 yaw/pitch 旋轉再換算回 local（不受 PMX local roll 影響）、`slerp` 平滑跟隨滑鼠。

### Changed
- **移除失效邏輯**：刪除指向緞帶骨的 `vrm.lookAt.target` 與相關 `look_target`/`face_pos`/`target_goal` 位移目標機制，改為直接驅動真實頭骨。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 無 lint 錯誤。
- `python scripts/export_vrm_info.py` 成功導出 521 行資料。
- 待人工於瀏覽器 `Ctrl + F5` 硬重整驗證：手臂自然下垂無塌陷、滑鼠移動時頭部跟隨。

## [0.4.22-alpha] - 2026-06-24

### Fixed
- **3D 虛擬客服「成田路」肩膀塌陷凹陷（肩部網格塌進腋下/胸腔）**：上一版以 `shoulder.rotation.z` 做肩膀補償，反而造成聳肩與腋下網格塌陷。原因是手臂下放角度過大（60°）拉扯腋下，加上 Z 軸補償破壞網格對齊。
  - 修法：`static/app_dashboard/js/ai-vrm-assistant.js` 的 `apply_rest_pose()` 採「保護模型結構」策略——大臂下放角度由 `Math.PI/3`(60°) 降為 `Math.PI/3.5`(約 51°，更自然不過度拉扯)；肩膀補償由 **Z 軸改為 Y 軸**（`shoulder.rotation.y = ±0.05`，模擬挺胸、不破壞腋下網格）；移除會疊加干擾的 upperArm 前傾 `rotation.x`。

### Changed
- **手肘/手腕線條柔化**：前臂前彎 `Math.PI/10` → `Math.PI/12`，手腕內傾同步下修，呈現更自然的手臂線條。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 無 lint 錯誤。
- 待人工於瀏覽器 `Ctrl + F5` 硬重整驗證：肩膀無塌陷、手臂自然下垂貼身。

## [0.4.21-alpha] - 2026-06-24

### Fixed
- **3D 虛擬客服「成田路」雙臂高舉而非放下（核心修復）**：待機站姿把大臂自 T-Pose 旋轉時方向相反。此模型由 PMX→VRM 轉檔，手臂骨骼 local roll 與標準 VRM 相反，原本「左臂正、右臂負」反而把手往上抬 75° 變成高舉。
  - 修法：`static/app_dashboard/js/ai-vrm-assistant.js` 的 `apply_rest_pose()` 翻轉正負號為「左臂負、右臂正」(`leftUpperArm.z = -Math.PI/2.4`、`rightUpperArm.z = +Math.PI/2.4`)，手臂正確放下。

### Changed
- **手肘自然彎曲**：前臂改以 `lowerArm.rotation.x`（繞 X 軸）前彎，取代原本的 `rotation.z`，呈現手擺在身側/腰間的自然客服姿態，不再像機械僵直。
- **光影立體感再強化**：主 `DirectionalLight` 強度 1.5 → 2.2，位置由 `(1.2,2.0,2.4)` 調為 `(2.0,2.0,2.0)`，明暗對比與輪廓更明顯。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 無 lint 錯誤。
- 待人工於瀏覽器 `Ctrl + F5` 硬重整驗證：雙臂自然下垂、手肘微彎、立體感提升。

## [0.4.20-alpha] - 2026-06-24

### Fixed
- **3D 虛擬客服相機 Box3 量測導致全黑（核心修復）**：上一版改用 `THREE.Box3` 量「世界座標全身高」推算相機距離，但此模型由 MMD/PMX 轉成 VRM，**第 0 幀 SpringBone 物理尚未穩定**，邊界框被量到極端異常巨大值，相機被推到數萬單位外 → 畫面全黑。
  - 修法：`static/app_dashboard/js/ai-vrm-assistant.js` 的 `frame_upper_body()` 徹底移除 Box3，改用「絕對安全座標 + 防呆夾擠」：`updateMatrixWorld(true)` 後取頭骨絕對高度（僅在 `0.5 < y < 2.5` 採用，否則退回安全預設 `1.4`；x/z 夾在 ±1.5），對焦 `head_y - 0.2`，採固定安全後退距離 `0.9`（不再做 FOV 反推，避免異常數值被放大）。
  - 一併移除不再使用的 `get_raw_bone_world_position()` 輔助函式。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 無 lint 錯誤。
- 待人工於瀏覽器 `Ctrl + F5` 硬重整驗證：不再全黑、半身穩定入鏡。

## [0.4.19-alpha] - 2026-06-24

### Fixed
- **3D 虛擬客服「成田路」大頭特寫 / 手臂出框（核心修復）**：上一版 `frame_upper_body()` 改用 `getNormalizedBoneNode()` 的世界座標來推算相機距離，但 normalized 骨架屬 three-vrm 內部正規化空間，頭與腰距離被壓縮，導致 FOV 距離算太近 → 臉貼螢幕、手臂被裁切。
  - 修法：改以 `THREE.Box3` 量測模型在**世界座標**中的真實全身高度（與縮放無關、穩定可靠），框出上半身約 52% 高度，並以 `getRawBoneNode('head')`（真實渲染骨骼）作為對焦與視線基準。相機距離改為「比例自適應」，避免硬寫固定距離在非真實比例模型上失準。

### Changed
- **光影立體感強化**：`static/app_dashboard/js/ai-vrm-assistant.js` 由「環境光 + 雙方向光」升級為「環境光 + 半球光 + 主光 / 補光 / 輪廓光」三點打光，讓 MToon 材質呈現接近 Live2D 的明暗與髮絲邊緣分離。
- **互動追視更明顯**：滑鼠追視位移範圍依模型尺度（`model_scale_ref`）等比放大（由 0.55/0.45 提升至 0.9/0.7×scale），眼神跟隨更直覺。
- **待機自然化**：新增上半身極小幅度「呼吸」動畫（`chest` 骨骼 sin 起伏 ±0.022 rad）；待機站姿大臂下放角度由 72° 微調為 75°、手肘略加彎；resting 微笑由 0.35 下修為 0.18，避免 joy 表情把眼睛笑瞇而看不出視線跟隨；回覆笑容峰值由 1.0 降為 0.85。

### Verified
- `ReadLints` 確認 `ai-vrm-assistant.js` 無 lint 錯誤。
- 待人工於瀏覽器 `Ctrl + F5` 硬重整驗證：半身入鏡、手臂可見、立體光影與滑鼠追視。

## [0.4.18-alpha] - 2026-06-24

### Added
- **AI 新聞自然語言輸入模式**：`app_user_keyword_llm_report/services_ai_news.py` 新增 query profile 流程，輸入可自動判斷 `keyword` / `natural_language`，並抽取 `search_terms`（jieba + POS + stopwords）作為檢索詞。
- **AI 新聞 API 回傳檢索解釋欄位**：`generate_ai_news` 回應新增 `query_mode` 與 `search_terms`，後台可直接看到系統如何理解使用者輸入。

### Changed
- **檢索策略專業化**：自然語言模式改為「先抽詞檢索、命中不足自動回退基礎範圍」的雙層策略，降低查詢過窄導致的空結果風險。
- **後台 AI 新聞管理介面文案升級**：輸入欄改為自然語言描述導向，生成成功訊息附帶解析模式與檢索詞，便於編輯快速校對生成脈絡。

## [0.4.17-alpha] - 2026-06-24

### Added
- **Pipeline Step 6：Discord 訊息整合入庫**：新增 `scripts/convert_discord_to_newsdata.py`，包裝既有 `app_discord_bot.converter.convert_discord_to_newsdata()`，以 CLI 腳本形式整合進 Pipeline。
- **Pipeline Step 7：YouTube 影片整合入庫**：新增 `scripts/convert_youtube_to_newsdata.py`，將 `YouTubeVideo` 模型增量寫入 `NewsData`（`source='youtube'`），附簡易分類邏輯（活動 / 卡池 / 競賽 / 系統 / 其他）。
- **`PIPELINE_STEPS` 擴充為 7 步**：原 5 步加入 Step 6（Discord）與 Step 7（YouTube），`PIPELINE_STEP_EST_SECONDS` 同步補上估計秒數。
- **`pipeline.html` 新增 Step 6/7 步驟卡片**：全選 / 取消全選迴圈上限升至 7，Step 5 說明文字與 confirm 對話框更新，清楚標示「僅清除網路來源」。

### Changed
- **`scripts/import_uma_data.py` 的 `--clear` 行為調整**：原本清空全部 `NewsData`，改為只清除 `source__in=['bilibili','bahamut','ettoday','gamme','udn']`，保留 `discord` 與 `youtube` 來源資料，避免 Pipeline 完整執行時誤刪 Discord/YouTube 已整合資料。

### Verified
- `python manage.py check`：0 issues。
- `python scripts/convert_discord_to_newsdata.py` 直接執行：若無待轉換訊息則輸出「新增 0 筆」並正常退出。
- `python scripts/convert_youtube_to_newsdata.py` 直接執行：若 YouTubeVideo 表為空則輸出提示訊息並正常退出。

## [0.4.16-alpha] - 2026-06-24

### Changed
- **3D 客服「待機靈魂」優化（自然站姿 + resting 微笑 + 半身骨骼框景）**，使外觀符合 `plan/3d-ai-virtual-cs-plan.md` 對客服角色的規畫：
  - **消除預設 T-Pose**：載入後以 `vrm.humanoid.getNormalizedBoneNode` 取得雙臂骨骼，將大臂自 T-Pose 放下約 72 度、手肘略內收、手掌自然內傾，形成自然待機站姿。
  - **resting 微笑**：載入即套用 `Happy = 0.35` 並 `expressionManager.update()`，靜態時就有客服親和表情；收到回覆時短暫提升至 `1.0` 再還原回 resting 值（不再歸零成無表情）。
  - **半身框景改用骨骼座標**：放棄單純 `Box3`（會被裙子/馬尾/物理剛體撐大而退太遠），改以 `head` 與 `hips`（fallback `spine`/`chest`）世界座標計算對焦點與相機距離，精準呈現半身特寫；找不到骨骼時才回退 `Box3`。
  - **視線基準對齊頭部**：`lookAt` 目標高度對齊頭骨座標，避免翻白眼或低頭。

### Verified
- `ReadLints` 檢查 `ai-vrm-assistant.js` 無 lint 錯誤。
- `python manage.py check` 通過。

## [0.4.15-alpha] - 2026-06-24

### Fixed
- **修復伺服器選擇頁「已安裝伺服器縮圖不顯示」問題**：`app_uma_info_portal/views.py` 的 `servers` view 在取出 `installed_guilds` 後，若 `DiscordGuild.icon_hash` 為空（Bot 尚未重啟重新同步），立即以同次 OAuth 登入的 Session 資料（`user_guilds_raw`）中的 icon hash 補足，並以 `bulk_update` 持久化回 DB。
  - 原因：上一個 session 清除了 2 筆格式錯誤的 `icon_hash`（完整 URL），Bot 未重啟故無法重新填值，已安裝伺服器的 `icon_hash` 因此為空。
  - 未安裝伺服器使用 Session 資料直接組 CDN 網址，不受影響（顯示正常），本次修復讓已安裝伺服器走同樣的 Session 資料來源補值。
  - `DiscordGuild.icon_url` 屬性保留相容邏輯：純 hash → 自動組 CDN 網址；`a_` 開頭 → `.gif`（動圖）；完整 URL 開頭 → 直接使用。

### Verified
- `python manage.py check` 通過。
- `ReadLints` 確認 `views.py` 無 lint 錯誤。

## [0.4.14-alpha] - 2026-06-24

### Fixed
- **修正 3D 客服「畫面全透明、看不到人」的兩個隱蔽元兇**（DevTools 確認 canvas 已存在且 `three.js r160` 已載入，研判為材質實例與視錐裁切問題）：
  - **統一 THREE 實例（雙實例 → 單實例）**：改用 `templates/base.html` 的 `<script type="importmap">` 解析 `three` / `three/addons/` / `@pixiv/three-vrm`，並將 `ai-vrm-assistant.js` 改為 bare specifier 匯入。修正先前以 `esm.sh?bundle` 造成 `three-vrm` 內建自帶一份 THREE，導致 MToon 材質在主 renderer 下無法被正確繪製。
  - **關閉 SkinnedMesh 視錐裁切**：載入後 `vrm.scene.traverse` 將所有物件 `frustumCulled = false`，避免 VRM 旋轉/縮放後 bounding sphere 未更新而被 renderer 誤剔除。

### Verified
- `ReadLints` 檢查 `ai-vrm-assistant.js` 與 `base.html` 無 lint 錯誤。
- import map 置於 module script 之前，符合瀏覽器解析順序需求。

## [0.4.13-alpha] - 2026-06-24

### Fixed
- **Pipeline Step 5「清空 DB 並重新匯入」實際未清空（核心修復）**：`PIPELINE_STEPS` 的 Step 5 原本只執行 `python scripts/import_uma_data.py`，未傳入 `--clear` 引數，導致舊資料不被清除、資料庫中殘留來自前次匯入的孤兒筆數。症狀：匯入 1902 筆 CSV 後 DB 總數顯示 2414（多出 512 筆）。
  - 修法：`PIPELINE_STEPS` 結構由 `(label, script)` 二元組改為 `(label, script, extra_args)` 三元組；Step 5 帶入 `extra_args=['--clear']`；`_pipeline_run_script` 新增 `extra_args` 參數並拼入命令列；`_pipeline_worker` 解包新結構。
  - 驗收：下次執行 Step 5 log 會先出現 `[INFO] 清除現有資料 N 筆`，匯入後 Total 與 CSV 筆數一致。

## [0.4.12-alpha] - 2026-06-24

### Fixed
- **修復 Discord 控制台手動任務無法執行問題**：`/crawler-admin/discord/` 原本 `crawl` 按鈕前端被硬性禁止，`news` 任務又以 `subprocess` 直接執行 `news_generator.py`（該檔無 CLI 入口，實際不會推播）。改為統一走可追蹤任務系統，四種任務（`crawl/classify/convert/news`）皆可由 UI 啟動並可追蹤執行結果。
- **修復 Discord 資料整合來源標記錯誤**：`app_discord_bot/converter.py` 匯入 `NewsData` 時補上 `source='discord'`，避免 Discord 文章被誤記為預設來源，導致分析儀表板來源統計失真。

### Added
- **新增 Discord 任務執行記錄模型**：`app_discord_bot.models.DiscordTaskRun`（含 `status/progress_pct/log_text/result_json/error_message`），並新增 migration `0003_discordtaskrun.py`。
- **新增 Discord 任務 API**：
  - `POST /crawler-admin/api/discord/task/start/`：啟動任務（crawl/classify/convert/news）
  - `GET /crawler-admin/api/discord/task/status/`：查任務狀態（單筆/列表）
  - `GET /crawler-admin/api/discord/task/<run_id>/log/`：增量拉取日誌
- **新增 Discord 訊息刪除 API**：`POST /crawler-admin/api/discord/messages/delete/`，支援「刪除勾選」與「刪除目前篩選結果」。
- **Discord 控制台 UI 升級**（`app_crawler_admin/templates/app_crawler_admin/discord.html`）：
  - 手動任務區新增「動態進度條 + 完整執行日誌」
  - Discord 訊息查閱區新增條件篩選（關鍵字、日期區間、伺服器、頻道、分類）、排序、每頁筆數調整、分頁與刪除整合操作

### Changed
- **Discord 訊息查詢 API 強化**：`api_discord_recent_messages` 支援條件查詢、排序、分頁與總筆數回傳，並回傳 `guild_name`、`is_converted` 等 UI 所需欄位。
- **Discord 新聞推播排程函式擴充**：`app_discord_bot/scheduler.py` 的 `_run_per_guild_news` 新增 `force_send` 模式與回傳 `{sent, failed}`，可供手動任務直接觸發與記錄。
- **資料來源統計相容 Discord**：`api_stats` / `api_source_stats` 改為回傳 `SOURCE_META + NewsData 實際來源` 聯集，讓 `discord` 可被儀表板正確識別與使用。

### Verified
- `python manage.py makemigrations app_discord_bot` 成功建立 `0003_discordtaskrun.py`。
- `python manage.py check` 通過，無新增 Django 組態錯誤。
- `ReadLints` 檢查本次異動檔案，無新 lint 錯誤。

## [0.4.11-alpha] - 2026-06-24

### Fixed
- **修正主站 3D 客服「人物不出現」核心問題（框景錯位）**：原本相機與模型位置為固定數值（`camera y=1.12`、模型下移 `y=-0.95`），導致鏡頭對到角色頭部上方的空白區，角色被推到畫面外。改為載入後以 `THREE.Box3` 量測模型實際邊界框，動態計算對焦點與相機距離，自動框出「上半身」畫面，確保不同比例模型都能正確顯示。
- **新增 `VRMUtils.rotateVRM0` 面向修正**：確保 VRM0 規格模型載入後面向鏡頭（+Z），避免只看到背面或側面。
- **視線目標改以臉部為基準計算**：滑鼠追視目標點改為相對臉部世界座標偏移，與新框景一致，避免追視方向錯亂。

### Verified
- `ReadLints` 檢查 `ai-vrm-assistant.js` 無語法與 lint 錯誤。
- 既有聊天功能（`/agent/chat/` JSON 串接）不受影響，仍可正常送出與回覆。

## [0.4.10-alpha] - 2026-06-24

### Fixed
- **修正主站 3D 客服 three-vrm 載入來源**：`static/app_dashboard/js/ai-vrm-assistant.js` 的 `@pixiv/three-vrm` 載入來源改為可解析裸模組依賴的 ESM CDN（`esm.sh`），避免瀏覽器因 `import ... from 'three'` 解析失敗而整段 3D 初始化中止。
- **補強載入失敗可視提示**：當 3D 初始化異常時，不再直接隱藏客服元件，改為在泡泡顯示「3D 模型載入失敗，請重新整理頁面」，方便前台快速判斷問題。

### Verified
- 已確認新版 `three-vrm` 載入 URL 可由瀏覽器直接解析（不需 import map）。
- `ReadLints` 檢查 `ai-vrm-assistant.js` 無語法與 lint 錯誤。

## [0.4.9-alpha] - 2026-06-24

### Added
- **主站 3D 浮動 AI 虛擬客服正式動工**：新增 `static/app_dashboard/js/ai-vrm-assistant.js` 與 `static/app_dashboard/css/ai-vrm-assistant.css`，落地右下角常駐 3D 客服容器、對話泡泡、輸入框與發送按鈕，並套用科技感毛玻璃樣式。
- **VRM 模型發布資產落地**：建立 `static/app_dashboard/vrm/1077_Narita_Top_Road.vrm`，確保前端可透過 Django static 路徑穩定載入角色模型。
- **主站模板掛載 3D 客服**：`templates/base.html` 新增全域固定客服節點 `#ai-vrm-assistant-root`，並注入客服 CSS 與 module script，主站各前台頁皆可使用。
- **API 自動化測試**：`app_agent_uma/tests.py` 新增 `/agent/chat/` JSON 請求與主站掛載點測試案例，確保客服前端依賴契約可被回歸驗證。

### Changed
- **`/agent/chat/` 支援 JSON 與表單雙模式**：`app_agent_uma/views.py` 新增 `application/json` 解析流程，與既有 `request.POST` 相容，前台 3D 客服可直接 `fetch` 送 `{"message":"..."}`。
- **回應契約強化**：`/agent/chat/` 成功回傳統一包含 `reply` 與 `message` 兩個欄位，錯誤時提供可讀錯誤訊息，便於前端泡泡顯示。
- **SPEC 同步更新為已實作狀態**：`SPEC/TASK_SPEC.md`、`SPEC/DESIGN_SPEC.md`、`SPEC/INTENT_SPEC.md` 補上 3D 客服任務、技術設計與使用者場景，避免規格與程式落差。

### Verified
- `python manage.py check` 可通過，未新增 Django 組態錯誤。
- `python manage.py test app_agent_uma.tests` 通過（JSON API + base template 掛載點）。
- `/agent/chat/` JSON 空訊息可回傳 `400`，避免無效請求進入 Agent 執行流程。

## [0.4.8-alpha] - 2026-06-24

### Added
- **AI 新聞封面圖生成（正式上線）**：`app_user_keyword_llm_report/services_ai_news.py` 新增 Gemini image 生成流程，封面圖會落地到 `media/ai_news_covers/`，並回傳可直接顯示的 `cover_image_url`。
- **圖片生成與文字模型解耦**：新增「封面圖固定走 Gemini」策略；即使後台 `provider=claude` 生成內文，封面圖仍由 Gemini image model 產生，避免 Claude 無圖像生成能力造成空封面。
- **封面 fallback 鏈**：當 Gemini 圖像生成失敗時，改採資料來源圖片 `photo_link`，再退到 `link`，降低前台無圖機率。
- **Django media 設定補齊**：`settings.py` 新增 `MEDIA_URL`、`MEDIA_ROOT`、`GEMINI_IMAGE_MODEL`；`website_configs/urls.py` 在 DEBUG 下新增 `/media/` 靜態服務。

### Changed
- **AI 新聞來源引用結構擴充**：`source_links` 新增 `photo_link` 欄位，供封面 fallback 與前台展示共用。

## [0.4.7-alpha] - 2026-06-24

### Added
- **新增主站 3D AI 虛擬客服實作計畫書**：建立 `plan/3d-ai-virtual-cs-plan.md`，完整定義「馬娘客服 成田路」在主站右下角常駐 3D 浮動客服的分階段落地計畫（場景、LookAt、聊天 UI、CSRF 串接、驗收與風險管控）。
- **新增 3D 客服技術規格文件**：建立 `SPEC/3d-ai-virtual-cs-spec.md`，明確規範 Three.js + `@pixiv/three-vrm` CDN 技術棧、VRM 靜態資產路徑、前端 DOM/CSS 契約、`POST /agent/chat/` 請求格式與錯誤處理策略。
- **補齊 VRM 模型存放契約**：文件中固定模型發布路徑為 `{% static 'app_dashboard/vrm/1077_Narita_Top_Road.vrm' %}`，並定義 `static/app_dashboard/vrm/` 為 3D 人物模型標準存放空間。

### Changed
- **SPEC 擴充前台互動能力規格**：新增「滑鼠 2D 座標轉 3D target + `vrm.lookAt.target` 跟隨」與「AI 回覆時表情 BlendShape/Expression 觸發」的可驗收技術描述，讓後續實作可直接對照驗收。

### Verified
- 路由盤點已確認 `website_configs/urls.py` 內存在 `agent/` 路由群，可對接本次規格的 `POST /agent/chat/` 需求。
- 文件內容已覆蓋使用者指定 acceptance criteria：3D 渲染、LookAt、泡泡與輸入 UI、CSRF API 串接、回覆狀態與表情互動。

## [0.4.6-alpha] - 2026-06-24

### Changed
- **Pipeline 分步執行升級為「執行中可視化」**：`app_crawler_admin/api_views.py` 的 Pipeline worker 改為增量收集子程序輸出，執行中即更新每一步 `tail`，不再只在步驟結束後才看到結果。
- **新增 Pipeline 估計進度狀態欄位**：`GET /crawler-admin/api/pipeline_status/` 新增 `progress_pct`、`estimated_remaining_s`、`running_step`，並為每一步補 `progress_pct` / `est_seconds` / `started_at` / `finished_at`，供前端呈現總進度與剩餘時間。
- **Pipeline 頁面美學化進度條**：`app_crawler_admin/templates/app_crawler_admin/pipeline.html` 新增「總進度條 + 每步 mini 進度條 + 預估剩餘時間」面板，視覺沿用現有設計系統色票與卡片語彙。
- **即時 log 顯示強化**：Pipeline log 區塊改為 `white-space: pre-wrap`，執行中、成功、失敗都顯示最近輸出摘錄，不再只有失敗時才顯示錯誤內容。

### Verified
- `POST /crawler-admin/api/run_pipeline/` 後輪詢 `GET /crawler-admin/api/pipeline_status/` 可觀察 `progress_pct` 與 `steps[].tail` 持續變化。
- Pipeline 頁面可在執行中即時看到進度條變動、目前執行步驟與估計剩餘時間。
- 既有 `run_pipeline` / `pipeline_status` 路由不變（`/crawler-admin/api/*`），前端相容既有呼叫流程。

## [0.4.5-alpha] - 2026-06-24

### Added
- **Discord Bot 啟動開關**（控制台 `/crawler-admin/discord/`）：
  - 新增 `app_discord_bot/bot_manager.py`，封裝 Bot 子行程管理邏輯：
    - `get_bot_status()` — 先查模組層級 `Popen` 參考，Fallback 讀 `discord_bot.pid` 檔確認行程存活；Windows 使用 `tasklist`，Linux/Mac 使用 `os.kill(pid, 0)`
    - `start_bot()` — 以 `subprocess.Popen` 啟動 `python manage.py run_discord_bot`，Windows 加 `CREATE_NEW_PROCESS_GROUP`，Unix 加 `start_new_session=True`；啟動後寫入 PID 檔
    - `stop_bot()` — 優先用 `Popen.terminate()` 優雅停止（10 秒逾時後 `kill`），Fallback 使用 PID 檔 + `taskkill`/`SIGTERM`；結束後清除 PID 檔
  - 新增 3 個 REST API（`app_crawler_admin/api_views.py`）：
    - `GET  /crawler-admin/api/discord/bot/status/` — 回傳 `{running, pid, source}`
    - `POST /crawler-admin/api/discord/bot/start/`  — 啟動 Bot，回傳 `{success, message}`
    - `POST /crawler-admin/api/discord/bot/stop/`   — 停止 Bot，回傳 `{success, message}`
  - `app_crawler_admin/urls.py` 新增對應三條路由
  - `discord.html` Bot 狀態卡片全新升級：
    - 大型圓形電源按鈕（⏻），綠光 = 運行中、灰色 = 已停止，Loading 旋轉動畫
    - 點擊自動切換啟動/停止，含 1.5 秒延遲後重新查詢最新狀態
    - 顯示 PID badge（運行中時）
    - 每 10 秒自動輪詢狀態，無需手動重整

### Changed
- `discord.html` 排程說明文字從「推播（每日20:00）」更新為「推播（依伺服器設定）」，對應新版 per-guild 推播邏輯

---

## [0.4.4-alpha] - 2026-06-24

### Added
- **`app_uma_info_portal` 全新應用**：建立完整的 UMA Info 官網 Portal（`/uma-info/`），包含：
  - `DiscordUser`、`DiscordGuild`、`GuildSetting`、`GuildChannelRule`、`GuildSettingAudit`、`GuildChannelCache`、`GuildRoleCache` 七個全新資料模型及對應 migration（`0001_initial.py`）
  - Discord OAuth2 登入流程（`/uma-info/auth/login/` → callback → logout），Access Token 使用 Django signing 加密入庫
  - 首頁（Hero + 統計列 + 功能介紹三段交替 + CTA），包含 Discord 訊息 mockup CSS art、設定面板 mockup
  - 伺服器選擇頁：分「已安裝」/「可邀請」兩區塊，卡片式 Grid 呈現
  - 伺服器管理頁：左側欄（Icon + 名稱 + 導覽）+ 右側主內容，含總覽/頻道讀取/推播設定/AI問答/統計/變更記錄六個分頁
  - REST API：channels、roles、settings save、channel rules CRUD、sync-cache、audits
  - 管理介面（`admin.py`）：DiscordUser、DiscordGuild、GuildSetting、GuildSettingAudit
- **`base_portal.html`**：Portal 專屬基底模板，共用 `design-system.css` 變數但有獨立 Portal Nav（Logo + 主題切換 + 用戶 chip/登入按鈕）
- **Discord Bot 重大升級**：
  - `on_guild_join` / `on_guild_remove` / `on_ready` 事件，加入/離開伺服器時自動同步 `DiscordGuild`、`GuildSetting`、`GuildChannelCache`、`GuildRoleCache` 至 DB
  - `@UMA Info` 觸發 AI 問答（Gemini 3.1 Flash Lite），支援 Discord Embed 回覆，含 RAG 情報 context 提取與 per-guild 啟用開關
  - 保留 `!channel` 指令相容性，並在回覆中引導使用官網管理
  - `get_bot_instance()` 全域方法，供 API 觸發快取同步
- **爬取架構升級（`crawler.py`）**：`crawl_all_channels` 改為逐伺服器執行，依 `GuildSetting.read_scope` 選擇頻道（all / announcements / single / advanced），保留舊版 `DiscordBotConfig` fallback
- **推播排程升級（`scheduler.py`）**：新增每小時整點 job，依各伺服器 `news_hour` 推播，支援 `ping_role_id`、`news_tone`；舊版 20:00 fallback 保留
- **`app_discord_bot` migration 0002**：為 `DiscordMessage` 及 `DiscordNewsLog` 新增 `guild_id` 欄位，`DiscordNewsLog` 新增 `pinged_role_id`
- **主站 Navbar 新增「🐴 UMA Info」連結**（`templates/base.html`）
- **`.env` 補充** `DISCORD_CLIENT_ID`、`DISCORD_CLIENT_SECRET`、`DISCORD_OAUTH_REDIRECT`、`UMA_CHAT_MODEL`

### Changed
- `settings.py`：新增 `app_uma_info_portal` 至 `INSTALLED_APPS`；`SESSION_COOKIE_AGE` 從 3600 改為 86400（Portal OAuth 需要較長 session）；新增 Discord OAuth2 及 UMA_CHAT_MODEL 設定
- `website_configs/urls.py`：新增 `/uma-info/` → `app_uma_info_portal.urls`
- `requirements.txt`：新增 `pytz>=2024.1`
- `SPEC/UMA_INFO_OVERHAUL_PLAN.md` 中所有 U1–U16 任務已實作完成

### Verified
- `python manage.py migrate` 可成功套用 `app_uma_info_portal.0001_initial` 及 `app_discord_bot.0002_add_guild_id`
- 首頁 `/uma-info/` 可正常渲染（無需登入）
- OAuth 流程需 `DISCORD_CLIENT_ID` + `DISCORD_CLIENT_SECRET` 填入 `.env` 後生效
- Bot 啟動後自動同步所有已加入伺服器的頻道/身分組快取

---

## [0.4.3-alpha] - 2026-06-24

### Fixed
- **補齊 AI 新聞資料表 migration（落地修復）**：現場檢查發現 `app_user_keyword_llm_report` 的 `0001_initial` 尚未套用，導致 `/crawler-admin/ai-news/` 可能觸發 `no such table: app_user_keyword_llm_report_generatednewsarticle`。已執行 app 專屬 migration，確保資料表存在並可正常查詢。
- **補齊測試 Client Host 白名單（落地修復）**：`.env` 的 `DJANGO_ALLOWED_HOSTS` 新增 `testserver`，避免 Django test client 預設 Host 觸發 `DisallowedHost`。
- **修正控制台內容偶發全隱形（UI 容錯修復）**：`ui-fx.js` 的捲動顯示機制原本依賴 `querySelectorAll(':scope ...')` 與完整流程成功執行；一旦在特定瀏覽器/狀態拋出例外，`reveal-ready` 仍存在而 `.main` 內容維持 `opacity: 0`，看起來像整個介面消失。已改為相容性較高的 `children` 篩選方式，並在 `setupScrollReveal/init` 加入 `try/catch` + `revealAll()` + 移除 `reveal-ready` 的保底，確保失敗時至少內容可見。

### Changed
- **移除控制台區塊淡入動效（美學精簡）**：`app_crawler_admin` 全頁不再使用「區塊淡入」捲動顯示，改為載入即顯示，降低控制台資訊操作時的視覺延遲與不必要動效干擾。
- **前台/後台動效邊界明確化**：`reveal-ready` 與 `.in-view` 僅保留前台 `#pageContent`，控制台 `base_admin.html` 不再注入 `reveal-ready`；`ui-fx.js` 觀測目標同步縮限為前台欄位。

### Notes（最小驗證）
- `python manage.py showmigrations app_user_keyword_llm_report`：`0001_initial` 顯示為已套用。
- Django test client：`GET /crawler-admin/` 回傳 200（Host=`testserver`）。
- Django test client：`GET /crawler-admin/ai-news/` 回傳 200（不再出現 `no such table` 500）。
- 手動重整控制台頁面：即使 reveal 動畫初始化失敗，也會自動移除 `reveal-ready`，內容不再整頁消失。
- 控制台頁面（`/crawler-admin/`、`/crawler-admin/pipeline/`、`/crawler-admin/history/`）載入後區塊直接顯示，不再等待淡入。
- `SPEC/DESIGN_SPEC.md` 已同步更新動效規範，與實作一致。

## [0.4.2-alpha] - 2026-06-24

### Fixed
- **Pipeline 分步執行卡住（核心修復）**：控制台「Pipeline 分步執行」按下後一直顯示「步驟在背景執行中，請稍後查看」，但實際永遠等不到結果。逐層排查後找到資料面與執行面兩個根因並全部修復：
  - **根因一：`preprocess.py` 讀取 raw CSV 直接崩潰（exit 1）**。`pandas.errors.ParserError: Error tokenizing data. C error: Expected 10 fields in line 93, saw 13` — `data/raw/bahamut_uma_raw.csv` 內容（巴哈論壇貼文）含未轉義的 `|` 與換行，且檔案混雜舊版欄位格式，導致 `pd.read_csv(sep='|')` 欄位數不一致而中斷整支前處理。
    - 修法：`pipeline/preprocess.py` 改用 `engine='python'` + `on_bad_lines='skip'` + `encoding='utf-8-sig'` 容錯讀取，遇到壞行跳過而非整支崩潰；並去除可能殘留的 BOM 欄名、缺 `content` 欄時安全跳過該來源。驗證：preprocess 由 crash 變為正常完成（exit 0），輸出 393 筆至 `data/processed/uma_combined_tokenized.csv`。
  - **根因二：執行採「射後不理」且輸出全丟棄，失敗完全不可見**。原 `api_run_pipeline` 以 `subprocess.Popen(..., stdout=DEVNULL, stderr=DEVNULL)` 平行啟動腳本後立即回傳，前端只能樂觀顯示「已啟動」，腳本在 Windows 下因未注入 UTF-8 環境列印中文崩潰、或如根因一直接報錯時，後台完全無從得知 → 表現為「卡住」。
    - 修法：重寫為**背景執行緒依序執行**，每步以 `subprocess.run(encoding='utf-8', errors='replace')` 並注入 `PYTHONIOENCODING/PYTHONUTF8=utf-8`，擷取退出碼與最後 25 行輸出；單步逾時上限 1 小時防永久卡死。狀態存於模組級 `_pipeline_state`，新增 `GET /crawler-admin/api/pipeline_status/` 供輪詢；重複觸發回 409。
    - 前端 `pipeline.html`：送出後改為每 2.5 秒輪詢狀態，逐步顯示「等待中／執行中／完成／失敗(rc)」，失敗時直接內嵌該步錯誤輸出；進頁時若已有一輪在跑會自動接續顯示進度。

### Notes（驗證）
- `preprocess.py` 直接執行：由 `ParserError` 崩潰修正為 `exit 0`，正常輸出 393 筆。
- Pipeline 端到端（Django test client，step 4 生成熱門 CSV）：`POST → started`、輪詢 `pipeline_status` → `step 4 success, rc=0`，並正確擷取腳本輸出。
- Django `python manage.py check`：0 issues。
- **資料面提醒**：`data/raw/bahamut_uma_raw.csv` 為混雜舊格式且含壞行，前處理僅保留可解析的 39 筆；建議於控制台清空後重新爬取巴哈來源以取得乾淨的統一格式資料。

### Notes（驗收）
- `python manage.py check`：0 issues。
- `python manage.py makemigrations --check --dry-run`：No changes detected（migration 已齊備）。

## [0.4.1-alpha] - 2026-06-24

### Fixed
- **修正區塊載入/重置閃爍（從無到有）**：原本捲動顯示由 `ui-fx.js` 於載入後才補上隱藏 class，導致區塊「先顯示→淡出→再淡入」。改為：
  - 隱藏初始狀態改用 CSS 選擇器表示（`#pageContent > [class*="col-"]`、`.admin-shell .main > :not(.modal)`），於首次繪製前即生效。
  - `reveal-ready` 由 `templates/base.html` 與 `base_admin.html` 的 `<head>` 內聯腳本在繪製前加到 `<html>`（僅在非 reduced-motion 且支援 IntersectionObserver 時）。
  - `static/js/ui-fx.js` 僅負責加 `.in-view`（含 `revealAll` 5 秒保險與不支援 IO 降階），不再於載入後補隱藏 class。

### Changed
- **下拉選單透明度調整（方式 A）**：`design-system.css` 為 `.dropdown-menu` 指定較不透明底色（淺色 `rgba(255,255,255,0.97)`、深色 `rgba(33,27,50,0.97)`），改善選單可讀性，alpha 可單點微調。

### Notes（驗收）
- `python manage.py check`：0 issues。
- 測試 Client 渲染 `/`、`/comment_sentiment/`、`/userkeyword_db/`、`/dashboard/announcements/?q=test`、`/crawler-admin/` 皆回傳 200。
- 預期行為：重新整理或進站時，內部區塊應「從隱藏淡入」，不應出現先完整顯示再淡出的閃爍。

## [0.4.0-alpha] - 2026-06-23

### Changed
- **前台排程/任務控制統一後台化**：將原本放在 `app_comment_sentiment/dashboard.html` 的排程啟停與手動觸發按鈕（爬蟲/分析）移出前台，改為僅保留資料檢視；控制入口統一導向 `app_crawler_admin`，避免前台誤操作造成背景任務失控。
- **`/dashboard/scheduler/` 行為調整**：`app_dashboard/views.py` 的 `scheduler_page` 改為導向 `app_crawler_admin:schedule`，避免舊前台頁面持續使用不存在的 `/api/scheduler/*` 路由。

### Fixed
- **留言情緒圖表資料鍵值對不上（核心修復）**：`app_comment_sentiment/views.py` 的 `api_data()` 原本回傳 `cheer_up` / `dumbfounded`，但前端 `dashboard.html` 讀取的是 `excited` / `disappointed`，導致六維度圓餅圖兩個維度長期顯示 0。已統一 API 鍵值為前端實際使用命名。
- **後台新增留言情感控制 API（承接前台移轉）**：`app_crawler_admin/api_views.py` 與 `urls.py` 新增 `api/comment_sentiment/*` 系列端點（狀態、啟動、停止、手動執行、歷史），由後台集中管理留言情感排程。
- **「巴哈 Article 為 0」可診斷與可操作化**：
  - `app_crawler_admin/views.py::_get_platform_stats()` 新增 `article_count_hint` / `article_count_error`，明確區分「資料尚未匯入」與「資料表讀取失敗」兩種情況。
  - `app_crawler_admin/dashboard.html` 在「💬 巴哈 Article」卡片顯示提示訊息，並新增「🕷 巴哈資料匯入」按鈕。
  - `app_crawler_admin/api_views.py` 新增 `POST /crawler-admin/api/import_bahamut/`，可在後台一鍵啟動 `manage.py scrape_bahamut`。

### Notes（驗收）
- `python manage.py check`：0 issues。
- 本地 DB 狀態檢查：`Article.objects.count() == 0`、`Comment.objects.count() == 0`，確認「巴哈 Article = 0」主因為尚未匯入資料（非統計卡壞掉）。

## [0.3.16-alpha] - 2026-06-23

### Added
- **全寬導覽列 + 站內搜尋**：`templates/base.html` 導覽改為 `header.site-nav`（背景滿版至畫面邊界、內容置中於 `.container`），尾端新增搜尋框，串接既有 `announcement_list`（GET `q`）完成前後端可用之公告全文搜尋。
- **下拉選單滑入 + 淡入動效**：於 `design-system.css` 為 `.dropdown-menu` 加入透明度與位移過渡，呈現絲滑展開體驗。
- **蘋果風捲動顯示**：`static/js/ui-fx.js` 以 `IntersectionObserver` 為各區塊（前台 `#pageContent` 直屬欄、後台 `.main` 直屬子元素）加入滑入＋淡入，含 3 秒保險顯示與 `prefers-reduced-motion` 降階。
- **圖表固定高度容器**：新增 `.chart-fixed` / `.chart-tall`，解決「大塊圖配小字、區塊互相擠壓」問題。

### Changed
- **導覽列精簡與重新分類**：移除「情報站控制台」「平台介紹」頂層項目（改置於頁尾「站台導覽」），其餘整併為 4 組（熱門分析 / 關鍵詞檢索 / 情感儀表板 / AI 功能），並縮小導覽文字。
- **主題切換鈕位置調整**：前台改置於導覽列右側 `.nav-actions`；控制台改置於側欄底部（隨 flex 流，`.sidebar` 改為 flex column），修正後台多頁面被固定按鈕覆蓋、影響操作的問題。
- **暗色模式可讀性修正**：於 `design-system.css` 補上 Bootstrap 工具類主題覆寫（`.text-dark/.text-secondary/.text-primary/.bg-white/.bg-light/.table/.list-group-item/.nav-tabs/.btn-close` 等），讓殘留深色文字隨主題切換。
- **圖表美學優化**：
  - `app_character_pk/home.html` 評論聲量折線圖：固定高度、加大字級、`lineTension` 平滑、`usePointStyle` 圖例、index tooltip。
  - `app_user_keyword_db/home.html`：版面改為「公告清單 7 + 情緒分布 5」上排、折線圖整列下排（不再擠壓）；圓餅改 doughnut、折線加漸層填色與加大字級。
- **留言情感儀表板**：移除前台「🛡️ 排程與手動控制」面板與後台入口按鈕，排程/任務控制統一回歸後台（呼應 0.3.9-alpha）。
- **公告搜尋結果頁重寫**：`app_dashboard/announcement_list.html` 改用設計系統樣式（移除已不存在的 `btn-purple`、Bootstrap Icons 依賴），確保搜尋落地頁美觀且主題一致。

### Notes（驗收）
- `python manage.py check`：0 issues。
- URL 反解測試：`announcement_list`、`dashboard`、`app_poa_introduction:introduction`、`app_course_intro:index`、`app_crawler_admin:dashboard` 等皆正常。
- 測試 Client 渲染：`/`、`/comment_sentiment/`、`/userkeyword_db/`、`/dashboard/announcements/?q=test`、`/crawler-admin/`、`/introduction/`、`/course/` 皆回傳 200。
- 本次聚焦 UI/UX 與可讀性，搜尋沿用既有 `announcement_list` 視圖，未變更 API 契約、資料模型與 migration。

## [0.3.15-alpha] - 2026-06-23

### Added
- **全站共用設計系統**：新增 `static/css/design-system.css`，建立堇紫/淺紫/金/白主題色 Token、玻璃擬態（Glassmorphism）卡片、柔和陰影、圓角與留白規範，並補齊表格/列表防重疊樣式（`word-break`、`overflow-wrap`、`table/table-responsive`）。
- **主題與動效共用腳本**：
  - `static/js/theme.js`：實作「淺色 / 深色 / 跟隨系統」三態切換，前後台共用 `uma-theme` 偏好儲存。
  - `static/js/ui-fx.js`：實作全站 Mesh Gradient 背景掛載與查詢按鈕 PWM 呼吸態（`btn-query-ready`）自動同步。

### Changed
- **前台基底全面重構**：`templates/base.html` 改為載入共用設計系統，Bootstrap 統一升級至 5.3.3 CDN，導覽列重構為語意化 dropdown，並移除舊版大量 inline CSS/JS。
- **控制台基底全面重構**：`app_crawler_admin/templates/app_crawler_admin/base_admin.html` 改為與前台共用同一設計系統與三態主題機制，視覺語彙一致化（同色票、同動效、同玻璃風格）。
- **全站馬 Emoji 清理（主要入口頁）**：移除 `base.html`、`app_character_pk/home.html`、`app_poa_introduction/platform-introduction.html`、`crawler_admin` 主要頁中的馬 emoji，符合美學規格「不要有馬的 Emoji」。
- **站內導覽 URL 正規化**：`base.html` 內既有硬寫路徑（如 `/rag-agent/`、`/langchain-agent/`）改為 `{% url %}`，降低路由維護風險。

### Notes（驗收）
- 設計系統整併後，前台與後台皆可在同一主題按鈕循環切換三態（淺色/深色/跟隨系統），並正確記憶偏好。
- Mesh Gradient 背景、卡片/按鈕 hover 過渡與 PWM 呼吸效果已在共用層生效，無需逐頁重複貼樣式。
- 本次變更聚焦 UI/UX 與可讀性，不涉及 API 契約、資料模型與 migration。

## [0.3.14-alpha] - 2026-06-23

### Added
- **AI 新聞資料模型與服務層**：在 `app_user_keyword_llm_report` 新增 `GeneratedNewsArticle`（含 migration），並新增 `services_ai_news.py`，以現專案 `NewsData` 為資料來源實作「查詢篩選 → context 建構 → Gemini/Claude 生成 → fallback → DB 持久化」完整流程。
- **AI 新聞 API（前後台共用）**：
  - `POST /userkeyword_report/api/generate_ai_news/`（生成新聞）
  - `GET /userkeyword_report/api/latest_ai_news/`（前台首頁讀取已發布新聞）
  - `GET /userkeyword_report/api/admin/news_list/`、`POST /userkeyword_report/api/admin/news/<id>/toggle/`、`POST /userkeyword_report/api/admin/news/<id>/delete/`（後台管理）
- **crawler-admin 後台新增「AI 新聞管理」頁**：新增 `/crawler-admin/ai-news/`，支援關鍵詞/類別/來源/週數/模型參數化生成，並可直接切換發布狀態與刪除。

### Changed
- **前台首頁 UX 升級（專業新聞區塊）**：`app_character_pk/home.html` 新增「AI 生成新聞精選」主卡，整合標題、副標、摘要、參考來源與封面，並補齊 `loading / empty / error` 狀態，提升首頁資訊密度與新聞閱讀體驗。
- **後台導覽與入口整合**：`app_crawler_admin/base_admin.html` 新增側欄「內容營運 / AI 新聞管理」，`dashboard.html` 快捷列新增 AI 新聞入口，統一操作路徑。

## [0.3.13-alpha] - 2026-06-23

### Fixed
- **聯合新聞網 / ETtoday 新聞雲 / 宅宅新聞觸發後一律失敗（`unrecognized arguments: --playwright`）**：當這三個來源的 `CrawlerConfig.use_playwright` 被設為 `True` 時，`runner.trigger()` 會在命令列附加 `--playwright`，但 `crawl_udn_uma.py`、`crawl_ettoday_uma.py`、`crawl_gamme_uma.py` 三支腳本的 argparse **未定義此參數**，導致啟動時即拋出 `error: unrecognized arguments: --playwright`、子程序以非 0 退出，後台狀態被記為 `failed`。
  - 根因：`--playwright` 為「保留參數（no-op）」，原本只在 `crawl_bahamut_uma.py`、`crawl_bilibili_uma.py` 兩支定義，其餘三支遺漏，造成行為不一致。
  - 修法：替 `crawl_udn_uma.py`、`crawl_ettoday_uma.py`、`crawl_gamme_uma.py` 三支補上 `parser.add_argument('--playwright', action='store_true', help='（保留參數，不作用）')`，使全部 5 支爬蟲腳本對 runner 注入的參數行為一致，無論 `use_playwright` 開關為何都不再報錯。

### Notes（驗證）
- 三支腳本直接執行：`exit 0`，正常斷點續爬。
- 經 runner 同行程觸發、且**強制 5 來源 `use_playwright=True`**（最嚴苛情況）驗證：`bilibili / bahamut / udn / ettoday / gamme` 全部 `db=success`，ETtoday 不再 `failed`。
- 測試後已將 `CrawlerConfig`（`max_pages` / `use_playwright`）還原為測試前數值；延遲參數還原為模型預設 `0.8 / 1.5`。

## [0.3.12-alpha] - 2026-06-23

### Fixed
- **爬蟲執行歷史與首頁永遠顯示「運行中」但實際沒在動（核心修復）**：後台執行歷史與儀表板出現大量永久 `running` 的紀錄（`ended_at` 為空、新增/略過/錯誤皆 0），但實際上沒有任何爬蟲程序在跑。逐層排查後找到兩個根因並全部修復：
  - **根因一（致命）：log 讀取執行緒因編碼崩潰 → 永遠無法收尾**。`app_crawler_admin/runner.py` 的 `_log_reader` 背景執行緒以 `subprocess.Popen(text=True)` 讀取子程序輸出，但未指定 `encoding`，於 Windows 繁中環境預設使用 `cp950` 解碼；爬蟲輸出的是 UTF-8 中文日誌，導致**讀到第一行中文就拋出 `UnicodeDecodeError`，整個讀取執行緒立即崩潰**，永遠走不到 `process.wait()` / `_finish_run()`，於是 `CrawlerRun` 永久停在 `running`。這正是「每一次從網頁啟動的爬蟲都變成永久運行中」的元兇。
    - 修法：`Popen` 明確加上 `encoding='utf-8', errors='replace'`；並將 `_log_reader` 的讀取迴圈包進 `try/finally`，確保**無論是否發生例外都一定執行 `process.wait()` 與 `_finish_run()` 收尾**，且單行解碼失敗不再中斷整個迴圈。
  - **根因二：伺服器 autoreload／重啟產生孤兒紀錄無人收尾**。狀態存於記憶體 `_registry`，收尾靠背景執行緒；開發伺服器 autoreload／重啟時記憶體被清空、收尾執行緒一起消失，DB 的 `running` 永遠沒人收尾。
    - 修法：新增 `runner.reconcile_stale_runs()` 執行期自我修復函式 — 凡 DB 標記為 `running` 但不在 `_active_run_ids()`（真實活躍 subprocess）中的孤兒紀錄，一律收尾為 `failed` 並補上中斷說明。已接入 `api_status_all`、`api_history`（AJAX 端點）及 `dashboard`、`history_page`、`pipeline_page`（首屏 server 端渲染），確保前台顯示永遠與真實狀態一致。
  - **強化啟動清理**：`app_crawler_admin/apps.py` 原本把孤兒清理放在 `RUN_MAIN=='true'` 的 early-return **之後**，導致真正處理請求／啟動爬蟲的 worker 子行程永遠不會清理；已將孤兒清理移到該判斷**之前**，使 worker 重載後啟動時也會自動清理（scheduler 初始化行為維持不變）。

### Notes（驗證）
- 手動執行爬蟲腳本：正常輸出、`exit 0`。
- 同行程端到端驗證：`trigger → running → 實際抓取（new=1）→ 收尾 db=success, ended=True`，狀態鏈路完整。
- `api/status/` 與 `api/history/` 經 Django test client 驗證：5 來源皆回 `idle`、`history_running=0`，不再出現假性運行中。
- Django `python manage.py check`：0 issues。

## [0.3.11-alpha] - 2026-06-23

### Fixed
- **全站前端 API 串接稽核 — 管理子頁路由前綴錯誤（核心修復）**：全面掃描所有模板的 `fetch` / `$.ajax` / `$.get` / `$.post` 呼叫並與後端實際路由逐一比對，發現 0.3.0 新增的 RAG 與 YouTube 管理子頁前端仍照舊 SPEC 使用底線前綴 `/crawler_admin/`，但實際掛載點為連字號 `/crawler-admin/`（`website_configs/urls.py`），導致這兩頁所有 AJAX 一律 404、功能完全無法使用：
  - **`app_crawler_admin/templates/app_crawler_admin/rag.html`（3 處）**：`refreshStatus()` 的 `/crawler_admin/api/rag_status/`、`rebuildIndex()` 的 `/crawler_admin/api/rebuild_rag/`、`uploadFile()` 的 `/crawler_admin/api/upload_kb/`，全部修正為 `/crawler-admin/...`。
  - **`app_crawler_admin/templates/app_crawler_admin/youtube.html`（2 處）**：`loadData()` 的 `/crawler_admin/api/youtube_quota/`、`triggerCrawl()` 的 `/crawler_admin/api/youtube_crawl/`，修正為 `/crawler-admin/...`。
  - 修復後以 Django URL resolver 驗證 5 個端點皆正確解析至對應 view（`api_rag_status` / `api_rebuild_rag` / `api_upload_kb` / `api_youtube_quota` / `api_youtube_crawl`）。
- **根因消除：SPEC 與實作路由命名不一致**：此前綴錯誤自 0.3.2（`rebuildRag`）、0.3.3（`runPipeline`）起反覆出現，根因為 `SPEC/` 文件將控制台路由記為 `/crawler_admin/`（底線），開發時照抄即埋雷。本次將 `DESIGN_SPEC.md`（26 處）、`TASK_SPEC.md`（17 處）、`INTENT_SPEC.md`（1 處）全部對齊為實作的連字號 `/crawler-admin/`，杜絕後續復發。

### Notes（稽核結果）
- **稽核範圍**：主專案所有 `templates/**/*.html`（排除 `參考專案/`）共 20+ 個含 AJAX 呼叫的頁面。
- **已確認正確、無需修改的呼叫**：
  - `dashboard.html` / `schedule.html` / `settings.html` / `history.html` / `stats.html` / `live_monitor.html` / `pipeline.html` 皆已使用連字號 `/crawler-admin/`。
  - `discord.html` → `/discord/api/stats/`、`/discord/api/trigger_news/`（對應 `app_discord_bot/urls.py`）✅。
  - `app_agent_langchain` / `app_agent_langgraph` 的 `chat.html` 使用相對路徑 `api/chat/`、`api/clear/`，於 `/langchain-agent/`、`/langgraph-agent/` 下正確解析 ✅。
  - `app_rag_agent/chat.html`、`app_comment_sentiment/dashboard.html`、`app_youtube_uma/dashboard.html` 改用 `{% url %}` 標籤動態反解，無硬碼路徑風險 ✅。
- Django `python manage.py check`：0 issues。

## [0.3.10-alpha] - 2026-06-24

### Added
- **新增 UMA Info Discord Bot 大整改計畫書**：`SPEC/UMA_INFO_OVERHAUL_PLAN.md`，規劃將既有 Discord Bot 品牌化為「UMA Info」，含三大主軸：
  - **對外 UMA Info 官網**（新 App `app_uma_info_portal`）：Discord OAuth 登入、伺服器管理員自助設定（頻道讀取範圍：全部/公告/單一/進階、推播頻道、Ping 身分組、AI 聊天開關等），首頁/伺服器選擇/單一伺服器管理三大頁面，UI 對齊主站 design-system。
  - **對內控制台保留**：AI 新聞生成、全域排程、Bot 開關等管理員專用功能維持於情報站控制台。
  - **`@UMA Info` AI 問答指令**：採最便宜的 `gemini-2.5-flash-lite`（已查證 2026-06-24 定價 $0.10/$0.40 per 1M tokens）+ NewsData/RAG 檢索。
  - 內容涵蓋資料模型設計、OAuth 流程、API-first 端點清單、Bot 端改動、安全與隱私、建議新增功能、U1–U16 任務拆解、環境變數、部署、風險緩解與待確認決策點。

### 變更目的
- 回應「將專案 Discord Bot 功能大整改、提供伺服器管理員自助介面、保留管理員進階控制於控制台、新增 AI 問答」的需求，先以完整規劃文件定義範圍與分階段驗收，再進入實作。

### 影響範圍
- 僅新增規劃文件（`SPEC/`）與本變更紀錄，尚未變更任何程式碼。

---

## [0.3.9-alpha] - 2026-06-24

### Added
- **Discord Bot 管理頁整合至情報站控制台**：`/crawler-admin/discord/` 頁面全面重寫，將所有 Discord Bot 功能視覺化整合，不再需要離開控制台進行管理。
  - **頻道設定管理（CRUD）**：新增頻道表單（inline 展開）、刪除、切換啟用狀態，完全取代跳轉至 Django Admin 的舊做法。
  - **手動任務觸發**：卡片式操作按鈕，可直接觸發「分類待分類訊息」、「轉換 NewsData」、「AI 新聞推播」三項背景任務。
  - **最近 Discord 訊息瀏覽**：表格顯示最新 20 筆 `DiscordMessage`，含頻道、作者、分類狀態、分類方式。
  - **Discord Bot 指令說明**：內嵌 `!channel` 系列指令快速參考卡片。
  - **即時統計刷新**：統計卡片可按鈕觸發 AJAX 更新，不需整頁重載。
  - **Bot 狀態與設定摘要**：顯示 Token 是否已設定、當前新聞模型、排程規則說明。
- **新增 Discord 管理 API（`/crawler-admin/api/discord/`）**：8 支新端點整合至控制台路由：
  - `GET  api/discord/stats/` — 即時統計數據
  - `POST api/discord/channels/add/` — 新增或更新頻道設定
  - `POST api/discord/channels/<pk>/delete/` — 刪除頻道設定
  - `POST api/discord/channels/<pk>/toggle/` — 切換啟用狀態
  - `POST api/discord/run_classify/` — 觸發訊息分類
  - `POST api/discord/run_convert/` — 觸發 NewsData 轉換
  - `POST api/discord/trigger_news/` — 觸發 AI 新聞推播
  - `GET  api/discord/recent_messages/` — 最近訊息列表

### Changed
- `app_crawler_admin/views.py` `discord_management()`：改傳遞 model 物件實例（而非 `.values()` dict），並補充 `news_model`、`bot_token_set`、`recent_messages` 等 context。

### 驗收方式
- 前往 `/crawler-admin/discord/`，確認六個區塊（統計、Bot 狀態、頻道管理、任務觸發、訊息瀏覽、推播歷史）正常顯示。
- 點擊「+ 新增頻道」填寫後儲存，確認頻道列表新增一筆且無跳轉至 Admin。
- 點擊「切換」與「刪除」按鈕確認即時生效。
- 點擊「分類待分類訊息」確認 Toast 顯示「已啟動（背景執行）」。
- 點擊「↻ 更新」確認最近訊息列表可重新載入。

---

## [0.3.8-alpha] - 2026-06-23

### Changed
- **Discord Bot 頻道設定改由 DB 動態管理**：移除 `.env` 中的 `DISCORD_CRAWL_CHANNEL_IDS` 與 `DISCORD_NEWS_CHANNEL_ID` 兩個環境變數，頻道來源全部改從 `DiscordBotConfig` 資料表讀取。
  - 影響模組：`app_discord_bot/scheduler.py`、`app_discord_bot/management/commands/run_discord_bot.py`、`.env`

### Added
- **Discord Bot 頻道指令**：Bot 上線後，在任意 Discord 頻道輸入以下指令即可即時管理頻道設定，無需重啟：
  - `!channel set crawl [名稱]` — 設定當前頻道為爬取頻道
  - `!channel set news [名稱]` — 設定當前頻道為推播頻道
  - `!channel list` — 列出所有頻道設定
  - `!channel remove` — 移除當前頻道設定
  - `!channel help` — 顯示指令說明
- **Discord Bot 儀表板頻道管理 UI**：`/discord-bot/` 頁面新增「⚙️ 頻道設定管理」區塊，可直接在後台新增、刪除、切換啟用狀態，不再需要進入 Django Admin。
- **頻道 CRUD API**：新增三支後端 API：
  - `POST /discord-bot/api/channels/add/` — 新增或更新頻道設定
  - `POST /discord-bot/api/channels/<pk>/delete/` — 刪除頻道設定
  - `POST /discord-bot/api/channels/<pk>/toggle/` — 切換啟用狀態
- **多推播頻道支援**：`scheduler.py` 的每日 20:00 新聞推播任務改為遍歷所有啟用的 `channel_type='news'` 頻道，支援同時推播至多個頻道。

### Removed
- `.env` 中移除 `DISCORD_CRAWL_CHANNEL_IDS` 與 `DISCORD_NEWS_CHANNEL_ID`（改用 DB 管理）。
- `.env` 中移除 `DISCORD_CRAWL_LIMIT`（保留為 `crawler.py` 預設值 1000）。

### 驗收方式
- 啟動 Bot 後，在 Discord 輸入 `!channel set crawl 測試頻道`，確認 DB 新增一筆 `DiscordBotConfig`。
- 前往 `/discord-bot/` 確認新頻道出現在列表中，且可點擊「切換」與「刪除」按鈕正常運作。
- 確認 Bot 排程每日 20:00 推播時讀取 DB 而非環境變數。

---

## [0.3.7-alpha]

### Added
- **網站日誌寫入檔案**：在 `website_configs/settings.py` 新增 `LOGGING` 設定，將 Django 請求與錯誤日誌以 `TimedRotatingFileHandler` 每日輪轉方式寫入 `logs/` 資料夾：
  - `logs/django.log`：INFO 以上的 Django 一般日誌，保留 14 天。
  - `logs/error.log`：ERROR 以上的錯誤日誌，保留 30 天。
  - 同步建立 `logs/` 資料夾（`settings.py` 啟動時自動建立，無需手動操作）。
- **驗收方式**：重啟 `runserver` 後，訪問任意頁面，確認 `logs/django.log` 有新增請求記錄；故意訪問不存在路由，確認 `logs/error.log` 有 WARNING 寫入。

---

## [0.3.6-alpha] - 2026-06-23

### Fixed
- **爬蟲系統全面排查（設定持久化 + 寫入穩定性）**：
  - `settings.html`：修正 `||` 導致 `0` 被覆蓋成預設值（重整後看似「跳回預設值」）的問題，改為 `null/undefined` 明確判斷與 `isNaN` 驗證。
  - `api_config_save`：加入輸入防呆與錯誤回傳（`delay_max < delay_min` → 400），避免非法值觸發 500。
  - `api_history` / `api_log`：查詢參數容錯，`limit=oops` / `offset=oops` 不再炸 500。
  - `api_schedule_save`：驗證 `mode` 與 `cron_expr`，防止髒資料寫入排程。

- **爬蟲設定真正生效（不只存資料庫）**：
  - `runner.py`：啟動 crawler subprocess 時注入 `CRAWLER_DELAY_MIN`、`CRAWLER_DELAY_MAX`、`CRAWLER_USER_AGENT` 環境變數。
  - `crawl_bahamut_uma.py`、`crawl_ettoday_uma.py`、`crawl_udn_uma.py`、`crawl_gamme_uma.py`：延遲區間改為可讀取後台設定（環境變數覆蓋預設值）。
  - `crawl_bilibili_uma.py` 與其他來源：`User-Agent` 改為可讀取後台設定（環境變數覆蓋預設值）。

- **控制台交互錯誤回報補齊**：
  - `schedule.html`、`dashboard.html`、`live_monitor.html` 寫入型 AJAX 補齊 `error` callback，API 失敗時可見錯誤提示，不再靜默。
- **SQLite 鎖表容錯（高併發情境）**：
  - 驗收過程捕捉到 `api/schedule/save` 在背景 Pipeline 寫入期間偶發 `database is locked`。
  - `api_views.py` 新增 `_run_with_sqlite_retry()`，對 `api_schedule_save` / `api_schedule_delete` / `api_config_save` 的 DB 寫入操作做短重試；重試後仍失敗則回傳 `503` + 可讀錯誤訊息（不再拋 500）。

### Changed
- `SPEC/TASK_SPEC.md`：新增 `G2 — 爬蟲設定持久化與 API 防呆` 任務（含驗收條件，已完成）。
- `SPEC/DESIGN_SPEC.md`：新增 `14.14 爬蟲設定與排程 API 防呆` 契約段落，明確定義錯誤行為與參數容錯。

## [0.3.5-alpha] - 2026-06-23

### Added
- **G1 — 情報站控制台「資料清理」功能**：在 Pipeline 執行頁 (`/crawler-admin/pipeline/`) 新增「🧹 資料清理」卡片，解決重複 / 舊格式檔案佔用空間問題（盤點發現約 36.7 MB 重複資料），含三項功能：
  - **各來源 raw CSV 格式檢查表**：即時顯示 5 來源 `data/raw/*_uma_raw.csv` 是否符合統一規格（`item_id|source|date|category|title|content|link|photo_link`），舊格式以 `⚠️ 舊格式` 標示、統一格式以 `✅ 統一格式` 標示，並列出大小、更新時間、實際表頭。
  - **重複 / 舊格式檔案清理**：列出可安全刪除的 11 個重複 / 殘留檔案（含類別徽章：`duplicate_raw` 路徑遷移殘留、`stale_intermediate` 舊中間檔、`duplicate_dataset` 重複資料集、`stale_app_copy` 各 app 過時分散副本），可勾選後一鍵刪除並顯示釋放空間。
  - **清空資料庫 NewsData**：可選擇單一來源或全部，清空後提示需重跑 Pipeline 步驟 2–5。
- 新增後端 API（`app_crawler_admin/api_views.py`）：
  - `GET /crawler-admin/api/data_inventory/` — 資料盤點（raw 格式狀態 + 可清理檔案清單，唯讀不刪除）
  - `POST /crawler-admin/api/cleanup_files/` — 刪除指定檔案，僅允許 `_stale_file_specs()` 白名單路徑，並含路徑越界二次防護（解析後路徑須仍位於專案目錄內）
  - `POST /crawler-admin/api/clear_db/` — 清空 NewsData（支援 `{"source": "udn"}` 或 `"all"`）

### Fixed
- **`pipeline.html` — 執行 Pipeline URL typo**：`runPipeline()` 的 AJAX 路徑誤用底線 `/crawler_admin/api/run_pipeline/`，修正為連字號 `/crawler-admin/api/run_pipeline/`（與 0.3.2 的 `rebuildRag` 為同類錯誤）。

### Changed
- **`app_crawler_admin/urls.py`**：新增 3 條資料清理 API 路由（`api/data_inventory/`、`api/cleanup_files/`、`api/clear_db/`）。

### Notes（資料現況診斷）
- **舊格式殘留原因**：控制台「觸發爬蟲」(`runner.py`) 只執行 `crawl_*.py` 產生 raw CSV，**不會**自動跑 preprocess → label → import；且 P1/P2 修好爬蟲格式後尚未用新爬蟲重跑，故 `data/raw/bilibili_uma_raw.csv`、`data/raw/bahamut_uma_raw.csv` 仍停留在舊格式（5/27）。
- **UI 爬蟲 ≠ 進資料庫**：完整資料鏈為「爬蟲 → preprocess → label_sentiment → import」，後三步需於 Pipeline 執行頁手動觸發（步驟 2–5），或待新爬蟲重跑後執行。
- **過時分散副本非執行期 bug**：查證 `app_user_keyword_sentiment/views.py` 引用 `dataset/uma_news_preprocessed.csv` 的程式碼位於 docstring 註解區塊內，執行期實際向 `app_user_keyword` 借用 `df`（走 `services.news_service` 正典來源），故情感頁顯示的是正典資料；各 app `dataset/` 副本為無用殘留，已列入清理白名單。

## [0.3.4-alpha] - 2026-06-23

### Fixed
- **爬蟲設定頁持久化錯誤（核心修復）**：`app_crawler_admin/templates/app_crawler_admin/settings.html` 原先使用 `||` 套預設值，導致合法數值 `0`（如 `max_pages=0`）在渲染與送出時被覆蓋成預設值，重整後看起來「跳回預設值」。本次改為 `null/undefined` 明確判斷，並在儲存時使用 `isNaN` 驗證，確保 `0` 可正確保存與顯示。
- **爬蟲 API 全面防呆**：`app_crawler_admin/api_views.py` 新增 `_parse_int` / `_parse_float` / `_parse_bool`，並強化以下端點：
  - `api_config_save`：支援安全轉型、限制範圍、`delay_max >= delay_min` 驗證、回傳最新 `config`（前端可直接回填）
  - `api_schedule_save`：驗證 `mode` 與 `cron_expr`
  - `api_history` / `api_log`：查詢參數容錯（非法字串不再觸發 500）
- **控制台操作錯誤提示補全**：`schedule.html`、`dashboard.html`、`live_monitor.html` 的寫入/控制 AJAX 補上 `error` callback，當 API 失敗時可見錯誤提示，不再靜默失敗。

### Changed
- **SPEC 同步更新（符合本次修復）**：
  - `SPEC/TASK_SPEC.md`：新增 `G2 — 爬蟲設定持久化與 API 防呆` 任務與驗收條件（已完成）
  - `SPEC/DESIGN_SPEC.md`：新增 `14.14 爬蟲設定與排程 API 防呆` 契約，明確定義 `config/save`、`schedule/save` 錯誤行為與查詢參數容錯

## [0.3.3-alpha] - 2026-06-23

### Fixed
- **控制台爬蟲無法執行（核心修復）**：情報站控制台「爬蟲來源監控」觸發後爬蟲立即失敗或卡死，定位並修復四個根因：
  - **`runner.py` — Windows UTF-8 編碼崩潰**：subprocess 啟動環境繼承系統 CP950（Big5）編碼，bilibili 爬蟲 `print()` 輸出含 CP950 字集外的繁體字（如「決」`\u51b3`）時拋出 `UnicodeEncodeError: 'cp950' codec can't encode character`，導致每次觸發都在 1 秒內 `failed`。於 subprocess 環境變數加入 `PYTHONIOENCODING='utf-8'`。修復後 bilibili 連續執行 35 秒以上不再崩潰（先前約 1 秒即失敗）。
  - **`apps.py` — 孤兒 `running` 記錄殘留**：Django StatReloader 重啟或伺服器中途停止時，log reader thread 隨之終止，`_finish_run()` 永不被呼叫，`CrawlerRun` 記錄永久卡在 `running` 狀態，造成儀表板狀態錯亂與無法重新觸發。於 `AppConfig.ready()` 啟動時自動將殘留的 `running` 記錄標記為 `failed`（含 `ended_at`）。
  - **`crawl_bahamut_uma.py` / `crawl_bilibili_uma.py` — 忽略後台 `max_pages` 設定**：兩支腳本缺少 `argparse`，`runner.py` 傳入的 `--max-pages` 參數被靜默忽略；bahamut 永遠使用硬碼的 293 頁（耗時數小時）。為兩者補上 `argparse`，正確接受 `--max-pages` / `--max-articles` / `--playwright`。
  - **`dashboard.html` — 重建 RAG URL typo**：`rebuildRag()` 內 AJAX 路徑誤用底線 `/crawler_admin/api/rebuild_rag/`，修正為連字號 `/crawler-admin/api/rebuild_rag/`。
- **多重伺服器佔用 port 8000**：偵測到 4 個 Django `runserver` 實例同時 listen 127.0.0.1:8000 互相搶佔，造成請求落到舊版未修復的程式碼。清理全部重複行程並重啟單一乾淨實例，確保上述修復生效。

## [0.3.2-alpha] - 2026-06-23

### Fixed
- **爬蟲設定頁面：儲存後重置頁面恢復預設值（`settings.html`）**：根本原因為 JavaScript `||` 運算子將所有 falsy 值（包含合法的 `0`）替換成預設值，導致兩個問題同時存在：
  1. `renderAll()` 中 `c.max_pages||50`、`c.delay_min||0.8`、`c.delay_max||1.5`——當資料庫存 `0` 時顯示錯誤的預設值
  2. `saveConfig()` 中 `parseInt(...)||50`、`parseFloat(...)||0.8`——當使用者輸入 `0` 時送出錯誤的預設值給伺服器
  - 修正方案：以 `def(val, fallback)` 函式取代 `||`（使用 `!== undefined && !== null` 判斷），確保 `0` / `false` 等合法值不被覆蓋
  - 同步修正：`user_agent` 等欄位加入 `esc()` HTML 特殊字元轉義，防止含引號的值破壞 HTML 結構
  - 新增 `loadAll()` 錯誤回調：若任一來源設定 API 請求失敗，顯示明確錯誤提示而非卡在「載入中…」
  - 新增 `saveConfig()` 錯誤回調：AJAX 失敗時顯示「✗ 儲存失敗（HTTP N）」訊息，不再靜默失敗
  - 所有寫入 AJAX 加入 `X-CSRFToken` header（防未來 csrf_exempt 移除後失效）
  - 儲存成功後同步更新本地 `configs[source]` 快取，避免不重新載入 API 時渲染到舊值

- **排程管理頁面：AJAX 寫入操作缺乏錯誤處理（`schedule.html`）**：`toggleSched()`、`saveSchedule()`、`deleteSched()` 三個操作均無 `error:` 回調，失敗時使用者看不到任何反應。新增 `error:` handler 顯示 HTTP 狀態碼，並統一補上 `X-CSRFToken` header。

## [0.3.1-alpha] - 2026-06-23

### Fixed
- **全專案 Gemini 模型名稱過時修正**：依照 `INTENT_SPEC.md` 技術選型規範（`gemini-3.5-flash` 為唯一核准模型），掃描並修正主專案內 11 個程式碼檔案及 4 個文件檔中的過時模型字串：
  - `pipeline/label_sentiment.py`：`MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]` → `["gemini-3.5-flash"]`；同步移除已無法使用的 lite fallback
  - `app_agent_uma/agent_core/agent.py`：`gemini-3.1-flash-lite` → `gemini-3.5-flash`（此為唯一 `gemini-3.1` 系列殘留）
  - `app_agent_langgraph/graph_core/graph_agent.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_agent_langchain/views.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_discord_bot/news_generator.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_discord_bot/classifier.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_discord_bot/scheduler.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_youtube_uma/jobs.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_rag_agent/views.py`：`GEMINI_MODEL = 'gemini-2.5-flash'` → `'gemini-3.5-flash'`
  - `app_rag_uma/views.py`：`gemini-2.5-flash` → `gemini-3.5-flash`
  - `app_comment_sentiment/llm_client.py`：`MODEL_NAME = 'gemini-2.5-flash'` → `'gemini-3.5-flash'`
  - `app_course_intro/templates/.../api_introduction.html`：移除 `gemini-1.5-pro`（已停服）、`gemini-2.5-flash` → `gemini-3.5-flash`
  - `knowledge_base/uma_platform_faq.md`、`app_agent_uma/docs/phase1_genaisdk.md`、`phase2_langchain.md`、`第一階段說明.md`：文件中 `gemini-2.5-flash` → `gemini-3.5-flash`
- **嵌入模型 `gemini-embedding-001` 確認有效**：`app_rag_uma/build_index.py`、`app_rag_uma/views.py`、`app_rag_agent/views.py` 的嵌入向量呼叫經 SPEC 確認繼續使用 `gemini-embedding-001`（768 維），不需修改。
- **`參考專案/` 教學素材不納入修正範圍**：課程參考專案內的過時模型名稱僅為歷史紀錄，不影響本專案運行。

## [0.3.0-alpha] - 2026-06-23

### Added
- **A1 — 情報站控制台重命名**：`app_crawler_admin` 全站 UI 由「爬蟲後台」更名為「🛡️ 情報站控制台」，`base_admin.html` 側邊欄品牌、頁面標題，以及 `templates/base.html` Navbar 入口均同步更新。

- **A2 — 平台健康儀表板（控制台首頁改版）**：`app_crawler_admin` 儀表板首頁 (`/crawler-admin/`) 新增「平台資料健康總覽」卡片區塊，即時顯示：NewsData 總筆數、巴哈 Article 數量、YouTube 影片數量、Discord 訊息總數及馬娘相關訊息數、今日 YouTube API 配額進度條、RAG 索引狀態（大小/向量數/是否存在）、知識庫文件數、Discord 今日推播次數，以及快速操作按鈕（YouTube 管理 / Discord 管理 / RAG 知識庫 / Pipeline 執行 / 重建 RAG 索引）。後端 `_get_platform_stats()` 統一收集全平台數據。

- **A3 — 控制台側邊欄導航重整**：新增「社群資料」、「知識庫」兩個側邊欄分區，包含 YouTube API 管理、Discord Bot 管理、RAG 知識庫、Pipeline 執行四個快速入口。

- **B1 — `YouTubeQuotaLog` 模型**：在 `app_youtube_uma/models.py` 新增 `YouTubeQuotaLog` ORM 模型，記錄每日 YouTube Data API v3 配額使用量（`date`, `units_used`, `units_limit`, `last_crawl_at`, `videos_added`）；含 `percent` property；`unique=True` 防止同一天重複建立；執行 migration `0002_youtubequotalog`。

- **B2–B5 — YouTube API 管理頁**：新增 `/crawler-admin/youtube/` 完整管理頁，功能包含：今日配額 SVG 圓環圖（動態 stroke-dasharray）+ 進度條、統計卡片（影片總數/平均情感/今日配額）、最近 20 部影片清單表格（縮圖/標題/頻道/觀看數/情感標籤/發布時間）、手動觸發爬取按鈕（AJAX POST → `api/youtube_crawl/`）、配額 AJAX 動態刷新（`api/youtube_quota/`）。

- **C-AD — 統一資料儀表板 API**：新增兩支 REST API：
  - `GET /crawler-admin/api/source_stats/` — 各來源 NewsData 筆數（用於長條圖）
  - `GET /crawler-admin/api/sentiment_stats/` — 全資料庫 Positive/Neutral/Negative 比例（用於圓餅圖）
  - `GET /crawler-admin/api/platform_stats/` — 全平台健康統計（供儀表板 AJAX 刷新）

- **D-AD — Discord Bot 管理頁**：新增 `/crawler-admin/discord/` 管理頁，功能包含：統計卡片（訊息總數/馬娘相關/待分類/今日推播）、Bot 狀態顯示（含 Docker 指令說明）、`DiscordBotConfig` 頻道設定表格（類型/狀態/備注）、`DiscordNewsLog` 最近 10 筆推播歷史表格（時間/頻道/模型/內容摘要/狀態）、環境變數設定說明區塊、手動觸發新聞推播按鈕（AJAX POST → `/discord/api/trigger_news/`）。同時新增 `app_discord_bot/views.py` 的 `api_trigger_news` 端點，以 subprocess 非同步啟動 `news_generator.py`。

- **E1–E2 — RAG 知識庫管理頁**：新增 `/crawler-admin/rag/` 管理頁，功能包含：索引狀態徽章（正常/不存在）、統計卡片（向量數量/索引大小/最後建立時間/知識庫文件數）、`knowledge_base/` 文件清單（圖示/名稱/大小）、一鍵重建索引按鈕（AJAX POST → `api/rebuild_rag/`，非同步啟動 subprocess）、知識庫文件上傳表單（`api/upload_kb/`）、索引建立流程說明區塊。新增後端 API：
  - `GET /crawler-admin/api/rag_status/` — 索引狀態 + 知識庫文件清單
  - `POST /crawler-admin/api/rebuild_rag/` — 非同步重建
  - `POST /crawler-admin/api/upload_kb/` — 上傳 .md/.txt/.pdf 到 knowledge_base/

- **F1 — Pipeline 分步執行頁**：新增 `/crawler-admin/pipeline/` 管理頁，功能包含：5 個 Pipeline 步驟的勾選卡片（全選/取消全選，步驟 2/3 預設已勾）、各步驟描述與預估時間、執行結果即時 log 面板（顯示啟動成功/失敗訊息）、最近 15 筆 `CrawlerRun` 執行記錄表格（來源/狀態/觸發方式/時間/新增數/錯誤數）。新增後端 API：
  - `POST /crawler-admin/api/run_pipeline/` — 接受 `{"steps": [2,3]}` 以 subprocess 非同步逐步執行

### Changed
- **`app_crawler_admin/views.py`**：新增 `_get_platform_stats()` 平台健康收集函式；新增 `youtube_management()`、`discord_management()`、`rag_management()`、`pipeline_page()` 四個視圖函式；`dashboard()` 改為傳入 `platform_stats` context。
- **`app_crawler_admin/api_views.py`**：新增 `api_source_stats`、`api_sentiment_stats`、`api_platform_stats`、`api_rag_status`、`api_rebuild_rag`、`api_youtube_quota`、`api_youtube_crawl`、`api_run_pipeline`、`api_upload_kb` 共 9 支新 API。
- **`app_crawler_admin/urls.py`**：新增 4 個頁面路由 + 9 個 API 路由，共增加 13 條 URL pattern。
- **`app_discord_bot/views.py`**：新增 `api_trigger_news` 視圖。
- **`app_discord_bot/urls.py`**：新增 `api/trigger_news/` 路由。
- **`app_youtube_uma/models.py`**：新增 `YouTubeQuotaLog` 模型（置於 `YouTubeVideo` 之前）。

## [0.1.3-alpha] - 2026-06-23

### Added
- **O1 — `app_rag_agent`（Agentic RAG 助理）**：結合 FAISS 語意搜尋工具（`search_uma_announcements`）+ DB 精確查詢工具（`list_announcements_by_category`）的 Agentic RAG，由 Gemini 動態決定工具呼叫順序；Session 保存對話歷史（最近 10 輪）；回答引用公告 ID 與來源連結。路由：`/rag-agent/`。
- **O2 — `app_agent_langchain`（LangChain ReAct Agent）**：使用 LangChain 1.3.x + langchain-google-genai 4.x 建構 ReAct Agent；三工具（search_announcements、list_by_category、get_announcement_detail）；ReAct Thought→Action→Observation 推理循環，最多 6 輪迭代。路由：`/langchain-agent/`。
- **O3 — `app_agent_langgraph`（LangGraph 狀態圖 Agent）**：使用 LangGraph 建構顯式 StateGraph；`graph_core/state.py`（`AgentState` TypedDict）+ `graph_core/graph_agent.py`（call_model → should_continue → call_tools 三節點圖）；內建工具呼叫次數限制（最多 8 次），避免無限迴圈。路由：`/langgraph-agent/`。
- **O4 — `app_course_intro`（平台技術說明）**：兩個靜態說明頁，`api-introduction`（Gemini/Claude/YouTube/Discord API 說明卡片）+ `course-introduction`（課程功能架構 timeline）。路由：`/course/`。
- **O5 — `app_youtube_uma`（YouTube 影片情感分析）**：`YouTubeVideo`/`YouTubeComment` 模型 + migration；`crawl_youtube` management command（支援 `--max-videos`/`--max-comments` 參數）；APScheduler 每 6 小時爬取、每日 03:00 批次情感標記；`dashboard` + `api/videos/` + `api/stats/` 視圖；`pipeline/crawl_youtube_uma.py` 獨立爬蟲腳本。路由：`/youtube/`。
- **D1–D8 — `app_discord_bot`（Discord Bot 完整系統）**：
  - D1: 三個 ORM 模型（`DiscordMessage`/`DiscordBotConfig`/`DiscordNewsLog`）+ Django Admin 整合
  - D2: `run_discord_bot` management command（discord.py 2.4.0 UmaBot）
  - D3: `crawler.py` 頻道歷史增量爬取，`bulk_create(ignore_conflicts=True)` 防重複
  - D4: `classifier.py` 雙層篩選（關鍵字層 + Gemini Batch 50 則一組分類層）
  - D5: `converter.py` DiscordMessage → NewsData 轉換整合（category="Discord"）
  - D6: `news_generator.py` AI 週報生成（支援 Gemini / Claude 切換）+ `split_for_discord()` 長文切分
  - D7: `scheduler.py` AsyncIOScheduler 5 個排程任務（爬取60min/分類2h/轉換01:00/推播20:00）
  - D8: `docker-compose.yml` 新增 `discord-bot` 服務（共用 app volume，`restart: unless-stopped`）
  - 路由：`/discord/`

### Changed
- **`website_configs/settings.py`**：INSTALLED_APPS 新增 `app_rag_agent`、`app_course_intro`、`app_agent_langchain`、`app_agent_langgraph`、`app_youtube_uma`、`app_discord_bot`（共 6 個 App）
- **`website_configs/urls.py`**：新增 `/rag-agent/`、`/course/`、`/langchain-agent/`、`/langgraph-agent/`、`/youtube/`、`/discord/` 6 條路由
- **`templates/base.html`**：Navbar「AI 功能」下拉選單新增 Agentic RAG/LangChain/LangGraph 連結；新增「社群資料」下拉選單（YouTube + 平台說明）
- **`requirements.txt`**：新增 `langchain>=1.3.0`、`langchain-google-genai>=4.2.0`、`langgraph>=0.2.0`、`discord.py==2.4.0`
- **`.env.example`**：新增 `YOUTUBE_API_KEY`、Discord Bot 相關環境變數
- **`feature-completion-plan.html`**：`DEFAULT_CHECKS` 新增 O1–O5（`to1`–`to5`）與 D1–D8（`td1`–`td8`）全部打勾

## [0.1.2-alpha] - 2026-06-23

### Added
- **H2 完整修復 — `Article`/`Comment`/`ArticleEmotion` 模型**：在 `app_comment_sentiment/models.py` 新增三個模型，對齊計畫規格：`Article`（哈啦板貼文，含 sentiment 欄位）、`Comment`（留言，含 upvotes/downvotes）、`ArticleEmotion`（六維度情緒 OneToOne，欄位：cheer_up, happy, mixed, dumbfounded, angry, sad）；執行 migration `0002_article_articleemotion_comment`。
- **H2 完整修復 — `scrape_bahamut` 改存 Article/Comment**：`scrape_bahamut.py` 完整重寫，匯入目標從 `GameAnnouncement` 改為 `app_comment_sentiment.Article`；新增 `--fetch-comments` 選項，可在匯入時同步抓取各文章留言存入 `Comment`；保留 `--crawl / --pages / --csv / --limit` 原有參數。
- **H2 完整修復 — `api_data` 視圖改用 Article 模型**：`app_comment_sentiment/views.py` 的 `api_data` 改從 `Article` 查詢（原為 `GameAnnouncement`），回傳欄位對齊計畫規格（含 `comments_count`、`emotion` 六維度）。
- **H3 補全 — `knowledge_base/uma_characters.md`**：從 `pipeline/uma_characters_bilingual.csv` 轉換產生，收錄 119 筆角色的繁/簡中文名、皮膚別名、常用關鍵字，Agent `read_local_document` 工具現可正確回應角色查詢；`knowledge_base/` 現有 3 份 `.md` 文件。

## [0.1.1-alpha] - 2026-06-23

### Added
- **H2 — `scrape_bahamut` management command**：新增 `app_comment_sentiment/management/commands/scrape_bahamut.py`，支援 `--crawl`（先執行爬蟲再匯入）、`--pages`（限制頁數）、`--csv`（自訂路徑）、`--limit`（筆數上限）參數，自動對應論壇標籤→標準分類，以 `source_url` 去重，執行 `python manage.py scrape_bahamut` 即可。
- **`pipeline/PIPELINE_GUIDE.md`**：新增完整資料管線執行指引（P6 文件化），含 6 個執行步驟、各來源預期筆數、驗收指標與常見 FAQ。

### Fixed
- **P1 — bilibili 爬蟲輸出格式修復**：`pipeline/crawl_bilibili_uma.py` 輸出路徑改為 `data/raw/bilibili_uma_raw.csv`；新增 `source` 欄位；在爬蟲端完成日期解析（`2025年3月8日` → `2025-03-08`）及簡→繁體轉換；`CSV_COLUMNS` 對齊統一規格（`item_id, source, date, category, title, content, link, photo_link`）。
- **P2 — bahamut 爬蟲輸出格式修復**：`pipeline/crawl_bahamut_uma.py` 輸出路徑改為 `data/raw/bahamut_uma_raw.csv`；新增論壇標籤→標準分類對應表（`CATEGORY_MAP`）；新增 `parse_date_bahamut()` 函式清理「`2022-03-23 00:04:57 編輯`」後綴；調整 `CSV_COLUMNS`（標準欄位在前，Bahamut 獨有欄位在後，保留 `raw_category`）。
- **P3 — ETtoday / UDN / Gamme 欄位順序統一**：`crawl_ettoday_uma.py`、`crawl_udn_uma.py`、`crawl_gamme_uma.py` 的 `CSV_COLUMNS` 由 `['item_id', 'title', 'date', ...]` 改為 `['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']`，`source` 移至第二欄對齊統一規格。
- **P5 — `preprocess.py` 精簡化**：完整重寫，移除逐欄補缺失欄位的 patch 迴圈、複雜多格式日期容錯（已在各爬蟲端處理）、全欄 OpenCC 轉換（改為只對 `content` 做一次備用防護）；保留核心邏輯：多來源合併 → 去重 → 日期容錯補丁 → content OpenCC → jieba 斷詞；輸出路徑統一為 `data/processed/uma_combined_tokenized.csv`。

## [0.1.0-alpha] - 2026-06-23

### Added
- **C1 — 留言情感儀表板**：新增 `/comment_sentiment/` 路由，`app_comment_sentiment` 補實完整 `dashboard` 視圖與 Template，包含公告情緒統計卡片、公告列表（可搜尋）、六維情緒圓餅圖 Modal（Chart.js）、排程狀態顯示與手動觸發按鈕。
- **H3 — 知識庫目錄**：建立 `knowledge_base/` 目錄，新增 `uma_game_introduction.md`（遊戲基本介紹、玩法、角色列表、活動類型）及 `uma_platform_faq.md`（平台功能 FAQ、資料來源說明）。
- **H1 — RAG 預建索引腳本**：新增 `app_rag_uma/build_index.py`，從 `knowledge_base/` 讀取所有 `.md/.txt` 文件，向量化後存至 `app_rag_uma/index/uma_knowledge.faiss` + `uma_knowledge_texts.pkl`，支援分批 Embedding。
- **docs 說明文件**：新增 `app_agent_uma/docs/phase1_genaisdk.md`、`phase2_langchain.md`、`phase3_langgraph.md`，詳細記錄三階段 AI Agent 技術架構。

### Fixed
- **C1 修復 — `/comment_sentiment/` 路由缺失**：`website_configs/urls.py` 原將 `app_comment_sentiment.urls` 掛在 `api/scheduler/` 下，現改為 `comment_sentiment/`，並在 `app_comment_sentiment/urls.py` 補齊 `app_name`、`dashboard`、`api/data/` 等路由。
- **C2 修復 — Navbar 缺少 AI/RAG/情感/介紹入口**：`templates/base.html` 移除所有「開發中」佔位連結，加入「💬 留言情感」、「AI 功能」下拉選單（AI 報告 / Agentic AI 助理 / RAG 知識庫）、「📖 平台介紹」及右側「📊 公告儀表板」連結。
- **M1 修復 — `poa_agent_introduction` 引用不存在目錄**：`app_agent_uma/views.py` 的 `poa_agent_introduction` 原引用 `app_agent_genaisdk`、`app_agent_langchain`、`app_agent_langgraph` 三個不存在的目錄；修正為讀取 `app_agent_uma/docs/` 內的說明文件，並將 template 路徑從 `app_agent_genaisdk/poa_agent_introduction.html` 修正為 `app_agent_uma/poa_agent_introduction.html`。
- **H1+M3 修復 — RAG 持久化索引 + 錯誤 model 名稱**：`app_rag_uma/views.py` 完整重寫，啟動時自動嘗試從磁碟載入 FAISS 索引，上傳 PDF 後同步寫回磁碟；修正 `gemini-3.1-flash-lite`（不存在）→ `gemini-2.5-flash`；新增「重新載入索引」操作。
- **P4 修復 — `label_sentiment.py` 硬寫路徑與舊版 API**：移除 `CONFIG_PATH = "/workspaces/8_10_emi/google_ai_config.json"` 硬寫路徑，改由 `.env` 讀取 `GEMINI_API_KEY`；棄用 `requests.post` 直接 HTTP 呼叫，改用 `google-genai` SDK（`client.models.generate_content`）；新增 `--source` CLI 參數支援 5 個資料來源。

### Changed
- **M2 — entrypoint.sh 增加 RAG 索引建立步驟**：`docker-files-poa/entrypoint.sh` 新增第 4 步驟，若 `app_rag_uma/index/uma_knowledge.faiss` 不存在則自動執行 `python app_rag_uma/build_index.py`；資料初始化由 `db_initialized.flag` 改為查詢 `NewsData.objects.count()`，更加健壯；啟動步驟由 5 步擴充為 6 步。
- **RAG 向量庫架構升級**：`app_rag_uma/views.py` 支援預建索引（磁碟）與使用者上傳 PDF 共存，上傳後自動持久化；向量維度確認為 3072（gemini-embedding-001）。

## [0.0.3-alpha] - 2026-06-22

### Fixed
- **LLM 報告 / 聲量分析：圖表資料載入失敗（500）**
  - **根因 1 — `df.date.max()` TypeError**：合併多來源資料（ettoday、bahamut）後，`uma_news_preprocessed.csv` 的 `date` 欄位存在 4 筆 `NaN`（float），混入字串型別。`filter_dataFrame` 呼叫 `df.date.max()` 時，numpy 嘗試比較 `str` 與 `float(NaN)`，引發 `TypeError`。
    - 修正：`app_user_keyword/views.py` 改用 `df.date.dropna().max()`，並在日期條件加入 `.notna()` 過濾。
  - **根因 2 — `count_keyword` KeyError**：`news_categories` 只含 bilibili 原有的 5 個類別（活動、卡池、競賽、系統、其他），ettoday/bahamut 資料帶有完全不同的類別名稱（情報、問題、繪圖…），導致 `cate_occurrence[row.category]` 拋出 `KeyError`，被外層 `try/except` 吞掉後回傳錯誤訊息。
    - 修正：`count_keyword` 對不在 `news_categories` 中的類別自動歸入「其他」，並對 `NaN` 內容欄位進行防護。

### Changed
- **多來源資料類別完整支援**：將 `news_categories`（`app_user_keyword/views.py`）從 6 項擴充為 18 項，涵蓋 bilibili（活動、卡池、競賽、系統）及 bahamut（情報、心得、討論、攻略、公告、問題、閒聊、繪圖、繪畫、史實、整理、小說）所有類別；其餘偶發類別（討論串等）仍歸入「其他」。
- **類別篩選 UI 改為下拉選單**：`app_user_keyword` 及 `app_user_keyword_llm_report` 兩個頁面的「公告類別」由 radio button 改為 `<select>` 下拉選單，並以 `<optgroup>` 依來源分組（bilibili / 巴哈姆特），提升可讀性與可擴展性。

## [0.0.2-alpha] - 2026-06-22

### Fixed
- **爬蟲後台所有頁面：modal 被半透明灰色 backdrop 遮蔽，無法操作表單（真正根本原因）**
  - 根本原因（最終確認）：`schedule.html`、`history.html`、`live_monitor.html` 的 modal HTML 位於 `{% block content %}` 內，亦即在 `<main class="main">` 之中。Bootstrap 的 `.modal-backdrop` 被 `appendChild` 至 `<body>` 直屬，而 modal 本身卻在 `<main>` 的渲染上下文裡。`body { display: flex }` 加上 `<main>` 的 flex item 特性（含 `overflow-y: auto`、`animation` 等屬性），使兩者的 `z-index` 無法在同一個 stacking context 中正確比較，導致 backdrop 視覺上覆蓋 modal。
  - 修正方案：在 `base_admin.html` 的 `</main>` 之後、`<script>` 之前新增 `{% block modals %}{% endblock %}` 掛載點，讓 modal 元素成為 `<body>` 的直接子項，與 Bootstrap 自動追加的 `.modal-backdrop` 同層比較 z-index（backdrop: 1049 < modal: 1055），遮蔽問題根除。
  - 同步修正 `schedule.html`、`history.html`、`live_monitor.html` 三個有 modal 的頁面，將 modal 區塊移至 `{% block modals %}`。

## [0.0.1-alpha] - 2026-06-22

### Fixed
- **爬蟲後台排程頁面：輔助修復（z-index 明確化、backdrop 清理、動畫 stacking context）**
  - `base_admin.html` 進場動畫最終 keyframe 改 `transform: none`，避免意外建立 stacking context。
  - 新增 `body.modal-open { padding-right: 0 !important }` 防止 flex body 被 Bootstrap scrollbar 補償位移。
  - 新增 `hidden.bs.modal` 事件清理殘留 `.modal-backdrop`，防止多次開關後疊加不透明遮罩。
  - `setCronInput()` 加防護：modal 已顯示時不重複呼叫 `show()`。
  - 明確設定 `.modal-backdrop { z-index: 1049 }` 與 `.modal { z-index: 1055 }`。

## [0.0.0-alpha] - 2026-06-22

### Added
- 建立此紀錄檔案。
