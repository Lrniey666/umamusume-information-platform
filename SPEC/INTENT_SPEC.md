# 意圖規格（Intent Spec）

> 回答「為什麼做」與「做什麼」。
> 描述使用者看得見的行為與價值，不涉及技術實作細節。
>
> 最後更新：2026-06-23（依據 feature-completion-plan.html + admin-platform-plan.html 補全）

---

## 問題陳述

課程期末專案要求以**公眾輿論分析（Public Opinion Analysis, POA）**為主題，建立一套完整的分析平台，並於第18週課堂進行約5分鐘的展示（同儕互評計分）。

本專案以先前作業成果 **umamusume-llm-report（w12）** 為基底，選用**賽馬娘 Pretty Derby** 的巴哈姆特哈啦板（bsn=34421）、Bilibili BWIKI 官方公告、ETtoday 遊戲新聞、UDN 遊戲版、Gamme 遊戲電影以及 YouTube 影片留言作為自訂輿情資料集，將其打造為一個涵蓋基本分析、留言情感排程、Agentic AI、RAG 知識庫、以及 Docker 部署的完整輿情平台。

期末專案須同時達到以下兩個層次：
1. **技術完整性**：涵蓋課程 w12–w16 所有核心技術（LLM 報告、留言分析、Agentic AI、RAG、Docker 部署）
2. **主題一致性**：全站以馬娘遊戲輿情為核心，資料集、分析邏輯、AI prompt 均圍繞遊戲社群討論

---

## 專案現況（截至 2026-06-23）

依據 `feature-completion-plan.html` 比對，目前已完成 **28 個** App / 功能模組（含 O1-O5、D1-D8）：

| 已完成項目 | 說明 |
|-----------|------|
| `app_character_pk` | 首頁角色人氣 PK 站 |
| `app_user_keyword` | 自訂關鍵詞聲量分析（CSV） |
| `app_user_keyword_association` | 全文關聯分析 |
| `app_user_keyword_sentiment` | 關鍵詞情感分析 |
| `app_user_keyword_db` | 全文 DB 搜尋（ORM） |
| `app_user_keyword_llm_report` | 雙模型 AI 報告（Gemini + Claude） |
| `app_uma_top_keyword` | 熱門關鍵詞排行（5 類別） |
| `app_uma_top_character` | 熱門角色排行（5 類別） |
| `app_crawler_admin` | 爬蟲後台（即將改版為「情報站控制台」） |
| `app_uma_news` | 遊戲公告資料模型 |
| `app_uma_comments` | 巴哈留言資料模型 |
| `app_dashboard` | 公告列表儀表板（DB 搜尋） |
| `app_comment_sentiment` | 留言情感排程儀表板 + APScheduler |
| `app_agent_uma` | Agentic AI（6 種 function calling） |
| `app_rag_uma` | RAG + FAISS（預建持久化索引） |
| `app_poa_introduction` | 平台介紹頁（已改造） |
| `app_correlation_analysis` | 關鍵詞相關性分析 |
| Docker + Nginx | docker-compose.yml + nginx.conf + discord-bot 服務 |
| 日/夜主題切換 | base.html 雙主題設計系統 |
| `app_rag_agent`（O1） | Agentic RAG（RAG + DB 雙工具 Agent） |
| `app_agent_langchain`（O2） | LangChain ReAct Agent |
| `app_agent_langgraph`（O3） | LangGraph StateGraph Agent |
| `app_course_intro`（O4） | 課程技術說明頁 |
| `app_youtube_uma`（O5） | YouTube Data API v3 影片情感儀表板 |
| `app_discord_bot`（D1-D8） | Discord Bot 自動新聞推播系統 |

### 待規劃與實作：資料管理中心（Admin Platform）

| 任務 | 說明 | 規格文件 |
|------|------|---------|
| A1–A3 | 控制台重命名 + 健康儀表板 + Navbar 更新 | DESIGN_SPEC.md § 18.1 |
| B1–B5 | YouTube API 配額管理頁 | DESIGN_SPEC.md § 18.2 |
| C-AD | 統一資料儀表板（多來源比較） | DESIGN_SPEC.md § 18.3 |
| D-AD | Discord Bot 管理頁 | DESIGN_SPEC.md § 18.4 |
| E1–E2 | RAG 知識庫管理頁 | DESIGN_SPEC.md § 18.5 |
| F1 | Pipeline 分步執行頁 | DESIGN_SPEC.md § 18.6 |

---

## 使用者場景

### 場景 0：首頁 — 角色人氣 PK（Feature App #2）
使用者進入網站首頁，看到馬娘角色卡片牆，多選角色後點擊比較，頁面以雷達圖與長條圖呈現各角色在巴哈版的「討論聲量 × 正負面情緒」多維對比，直觀感受不同角色的玩家社群熱度。

### 場景 1：關鍵字聲量觀測站
使用者在聲量頁面輸入感興趣的關鍵字（如「卡池」、「活動」、「限定」），選擇類別（活動 / 卡池 / 競賽 / 系統 / 其他）與時間範圍（最近 N 週），查詢後以長條圖與折線圖展示該關鍵字在各類別中的出現次數及時間趨勢。

### 場景 2：情緒分析
使用者在情緒頁查看特定關鍵字相關公告的情感分布（正面 / 負面 / 中性比例）及每日趨勢折線圖，了解玩家社群對遊戲更新的整體態度是否因特定事件（如強力限定卡池）而改變。

### 場景 3：AI 多模型分析報告（核心功能 / 要求8）
使用者輸入關鍵字，**選擇 AI 模型**（Gemini 3.5 Flash 或 Claude Sonnet 4.6），按下「生成分析報告」，系統自動整合聲量與情感數據組成 prompt，呼叫對應 LLM，在 30 秒內回傳一份至少 500 字、以 Markdown 排版的繁體中文分析報告，涵蓋摘要、關鍵詞、趨勢分析、建議與總結。

### 場景 4：巴哈留言情感分析儀表板（Feature App #1 / 要求5）
使用者開啟留言情感儀表板（`/comment_sentiment/`），看到最新爬取的巴哈馬娘版貼文列表，以及每篇貼文的 AI 分析結果——包含文章情感分數（正/負/中性）與留言情緒六維度（歡呼 / 開心 / 混亂 / 傻眼 / 憤怒 / 難過）的圓餅圖，讓使用者直觀感受玩家對每則遊戲公告的真實反應。

### 場景 5：自動排程背景爬取
管理員或進階使用者開啟排程管理頁，看到目前排程狀態（爬蟲每1小時、情感分析每日02:00）。可手動觸發單次執行，或啟動/停止定期排程，確保平台資料持續更新而無需人工介入。

### 場景 6：Agentic AI 馬娘分析助理（要求3）
使用者進入 Agentic AI 對話頁（`/agent/`），以自然語言提問——如「這週哪隻馬娘在巴哈討論最熱？」或「最近的卡池公告玩家反應如何？」——系統呼叫 Gemini 3.5 Flash，由 AI 自動調用工具（查詢角色聲量、情感分析、搜尋巴哈貼文、讀取本地知識庫文件）來組合答案，進行多輪工具呼叫後回傳完整分析結論。

### 場景 7：RAG 馬娘知識庫問答（要求4）
使用者在 RAG 問答頁（`/rag/`）無需上傳檔案即可直接提問（預建索引常駐），或選擇上傳馬娘角色介紹 PDF / Markdown 文件追加到知識庫，輸入問題（如「特別週的固有技能是什麼？」、「哪位馬娘適合長距離賽道？」），系統從知識庫檢索相關段落，以 Gemini 嵌入向量進行相似度搜尋，回傳含引用來源的精確答案；重啟伺服器後知識庫持久存在。

### 場景 8：各類公告熱門關鍵詞排行
使用者在熱門關鍵詞頁選擇公告類別與 Top-K 數量，系統從預處理詞頻資料中提取該類別高頻詞彙，以橫式長條圖呈現排行，協助使用者快速掌握不同類型公告的核心用語。

### 場景 9：各類公告熱門角色排行
使用者選擇公告類別，系統統計各類公告中被提及最多次的馬娘角色，以長條圖呈現排行，讓使用者了解哪些角色在特定類型（如卡池、競賽）中的曝光度最高。

### 場景 10：專題介紹頁（要求6）
使用者（或評審同學）進入介紹頁（`/introduction/`），看到平台的完整說明——包含主題動機、資料來源（巴哈姆特 bsn=34421、Bilibili BWIKI、ETtoday、UDN、Gamme）、技術架構圖、所有功能截圖與簡介，以及使用 AI 協助撰寫的分析說明，讓初次造訪的同學快速理解整個平台的設計理念。

### 場景 11：情報站控制台（app_crawler_admin 改版）
管理員進入情報站控制台（`/crawler-admin/`），一覽全平台健康狀態——包含各資料來源筆數統計卡片、YouTube API 今日配額使用進度條、Discord Bot 在線狀態與今日推播次數、RAG 索引向量數量，以及快速操作入口（觸發爬蟲、重建 RAG 索引、手動 Discord 推播）。子頁面提供 YouTube API 管理、Discord Bot 設定、RAG 知識庫管理、Pipeline 分步執行等深入功能。

### 場景 12：YouTube 影片情感儀表板（O5 已實作）
使用者進入 YouTube 儀表板（`/youtube/`），查看系統自動抓取的賽馬娘相關 YouTube 影片列表，包含每部影片的觀看數、按讚數、留言情感分數，以及週維度的聲量趨勢折線圖，讓使用者跨平台掌握遊戲社群在 YouTube 上的輿論動態。

### 場景 13：Agentic RAG 多工具問答（O1）
使用者在 Agentic RAG 頁面（`/rag-agent/`）提問，Agent 根據問題性質自動選擇「語意搜尋 RAG 工具」或「資料庫精確查詢工具」，回答附引用新聞 ID 與連結，比傳統單一 RAG 更靈活。

### 場景 14：LangChain ReAct Agent（O2）
使用者在 LangChain Agent 頁面（`/langchain-agent/`）提問，系統使用 LangChain ReAct 框架與 Gemini 互動，展示標準 Agent 推理迴圈（Thought → Action → Observation）的完整過程。

### 場景 15：LangGraph 狀態圖 Agent（O3）
使用者在 LangGraph Agent 頁面（`/langgraph-agent/`）提問，系統使用 LangGraph StateGraph 管理 Agent 狀態轉換，展示複雜多步驟 Agentic AI 的最新框架。

### 場景 16：Discord Bot 自動新聞（D1-D8）
Discord 伺服器管理員設定 Bot Token 與監聽頻道後，Bot 每 30 分鐘爬取頻道訊息，以雙層篩選（關鍵字 + Gemini 確認）過濾馬娘相關訊息，每日早上 08:00 由 Gemini 彙整成一篇新聞推播回 Discord 頻道，並在管理頁（`/discord/`）查看推播歷史記錄。

---

## 業務目標（對應期末需求）

| 期末要求 | 目標描述 | 對應功能 |
|---------|---------|---------|
| 要求 1 | 以期中成果為基礎繼續延伸 | w12 umamusume-llm-report 直接作為基底 |
| 要求 2 | 使用自己的資料集完成基本POA Apps | 巴哈馬娘資料取代政治新聞，保留所有基礎分析頁；5 來源資料集（Bilibili / Bahamut / ETtoday / UDN / Gamme） |
| 要求 3 | Agentic AI | `app_agent_uma`：馬娘專屬 Function Calling Agent（6 種工具） |
| 要求 4 | RAG 或 Agentic RAG | `app_rag_uma`：馬娘知識庫 FAISS 向量檢索（持久化） |
| 要求 5 | 1–2 個 Feature App 特色功能 | Feature #1 留言情感排程儀表板（`/comment_sentiment/`）、Feature #2 角色人氣PK（首頁） |
| 要求 6 | 撰寫介紹頁面 | `app_poa_introduction`：完整平台說明頁 |
| 要求 8 | 大型語言模型資料分析 | `app_user_keyword_llm_report`：雙模型（Gemini 3.5 Flash / Claude Sonnet 4.6）報告生成 |
| 部署 | Docker Compose Production 部署 | Nginx + Gunicorn + Django 容器化，`entrypoint.sh` 自動初始化資料 |
| 要求 7 | 前端框架加分（選做） | Bootstrap 5.3 為主，有餘力可加 React 元件 |
| 要求 9 | ML Classification（選做） | 預留 Jupyter Notebook 範例，不列入主線 |
| 加分 | YouTube 社群資料 | `app_youtube_uma`：YouTube Data API v3，每日 quota ≤ 3,000 units ✅ |
| 加分 | LangChain/LangGraph Agent | O2/O3：完整三階段 Agentic AI 教學系列 ✅ |
| 加分 | Discord Bot 自動推播 | D1-D8：馬娘相關訊息爬取 + AI 新聞生成 + 自動推播 ✅ |
| 後台 | 情報站控制台（計畫中）| 全平台管理中心，整合 YouTube/Discord/RAG/Pipeline 管理 |

---

## 成功指標

### 核心功能（T18 端對端驗收）

- [ ] `docker compose up` 後網站可正常存取（`http://localhost`）
- [ ] 首頁顯示馬娘角色 PK 卡片，可選角色生成比較圖表
- [ ] 輸入「卡池」、「活動」、「限定」等關鍵字，聲量分析頁正確回傳圖表
- [ ] 情感分析頁正確顯示正/負/中性比例與趨勢圖
- [ ] 選擇 Gemini 3.5 Flash 或 Claude Sonnet 4.6，均可在 40 秒內取得 500 字以上 Markdown 報告
- [ ] `/comment_sentiment/` 回應 200，顯示巴哈貼文列表 + 情緒六維度圓餅圖
- [ ] Agentic AI 對話頁可完成至少 3 輪工具呼叫的問答，包括 `read_local_document` 工具
- [ ] RAG 頁面無需上傳 PDF 即可直接提問，回答附引用段落，重啟後知識庫持久存在
- [ ] 介紹頁面完整展示平台說明，不含舊專案遺留文字
- [ ] Navbar 可直接存取 AI助理、RAG知識庫、留言情感儀表板、平台介紹

### 資料完整性

- [ ] `uma_news_preprocessed.csv` 含 5 個 source 值（bilibili / bahamut / ettoday / udn / gamme）
- [ ] DB `NewsData` 總筆數 ≥ 1,000（現況 344 筆，修復管線後達標）
- [ ] Bahamut 原始 5,951 筆中至少 500 筆入庫（現況僅 91 筆）
- [ ] UDN（191 筆 raw）與 Gamme 完全進入分析管線（現況 0 筆）
- [ ] `knowledge_base/` 目錄存在且含 ≥ 1 份馬娘知識文件（`.md` 或 `.txt`）
- [ ] `app_rag_uma/index/uma_knowledge.faiss` 預建索引存在

### 部署與品質

- [ ] `docker compose build && docker compose up -d` 可無錯誤完成
- [ ] Nginx 正確服務靜態檔案，Django 後端不直接暴露
- [ ] `entrypoint.sh` 具備 idempotent 保護（第二次啟動不重複匯入）
- [ ] `entrypoint.sh` 自動建立 RAG 索引（如不存在）
- [ ] APScheduler 排程在容器啟動後自動運作（或可從 UI 手動觸發）
- [ ] 全站 `python manage.py check` 無 Error
- [ ] `label_sentiment.py` 使用 `google-genai 2.9.0`（非棄用的 `requests.post`）

---

## 專案範圍（Scope）

### 包含（In-scope）

#### 直接複製使用（From w12）
- `app_character_pk`：角色人氣 PK 比較圖（首頁）
- `app_user_keyword`：關鍵字聲量分析（CSV 版）
- `app_user_keyword_sentiment`：情感分析（CSV 版）
- `app_user_keyword_db`：Django ORM 全文搜尋
- `app_uma_top_keyword`：各類別熱門關鍵詞
- `app_uma_top_character`：各類別熱門角色排行
- `pipeline/`：巴哈爬蟲腳本

#### 移植並改造（From w13）
- `app_comment_sentiment`：
  - 替換爬蟲：`scrape_yahoo.py` → **`scrape_bahamut.py`**（巴哈 API）
  - 新增儀表板頁面（目前只有排程 API，缺 views + templates）
  - 保留：`Article / Comment / ArticleEmotion` 模型
  - 保留：`analyze_sentiment` management command
  - 保留：`scheduler_manager.py`（APScheduler）
  - 新增：`scrape_bahamut` management command（`python manage.py scrape_bahamut`）
- `app_correlation_analysis`：關鍵詞相關性分析
- `app_poa_introduction`：改寫介紹內容為馬娘主題

#### 移植並改造（From w16）
- `app_user_keyword_llm_report`：**新增 Claude Sonnet 4.6 雙模型選擇**
- `app_agent_uma`（改自 `app_agent_genaisdk`）：馬娘專屬工具函數（含 `read_local_document`）
- `app_rag_uma`（改自 `app_rag_basic`）：馬娘知識庫 FAISS 向量檢索，改為預建持久化索引
- Docker Compose + Nginx + Gunicorn 部署架構

#### 本專案新增
- `app_crawler_admin`：爬蟲後台（5 來源即時監控）
- `app_uma_news`：遊戲公告資料模型
- `app_uma_comments`：巴哈留言資料模型
- `app_dashboard`：公告列表儀表板（DB 搜尋）
- `app_user_keyword_association`：全文關聯分析
- `knowledge_base/`：馬娘知識文件目錄（供 RAG + Agent 使用）
- `data/raw/` + `data/processed/`：統一資料管線目錄結構

#### 資料管線修復（P1–P6）
- 統一 5 爬蟲輸出至 `data/raw/{source}_uma_raw.csv`（Canonical Raw CSV 規格）
- 修復 `pipeline/label_sentiment.py`：移除硬編碼路徑、改用 `google-genai 2.9.0`、支援多來源輸入
- 簡化 `pipeline/preprocess.py`：移除多來源 patch 邏輯，輸出 `data/processed/uma_combined_tokenized.csv`

### 已實作選用項（O1-O5、D1-D8）

- `app_rag_agent`（O1）：Agentic RAG（DB 知識庫 + 語意搜尋雙工具）✅
- `app_agent_langchain`（O2）：LangChain ReAct Agent ✅
- `app_agent_langgraph`（O3）：LangGraph 狀態圖 Agent ✅
- `app_course_intro`（O4）：API 介紹與課程說明頁 ✅
- `app_youtube_uma`（O5）：YouTube Data API v3 影片情感儀表板 ✅
- `app_discord_bot`（D1-D8）：Discord Bot 自動新聞推播系統 ✅

### 後台改版（Admin Platform，待實作）

- 情報站控制台（A1-A3）：控制台重命名 + 全平台健康儀表板
- YouTube API 管理（B1-B5）：配額圓環圖 + 搜尋關鍵字管理 + 手動觸發
- 統一資料儀表板（C-AD）：多來源比較 + 情感分布
- Discord Bot 管理（D-AD）：Bot 狀態 + 設定 + 推播歷史
- RAG 知識庫管理（E1-E2）：索引狀態 + 一鍵重建 + 文件上傳
- Pipeline 分步執行（F1）：可視化管線執行 + 歷史記錄

### 不包含（Out-of-scope）

- 即時爬取（爬蟲為離線或排程執行，不在 request 週期中觸發）
- 多使用者帳號系統與權限管理
- React.js / Vue.js 前端重構（要求7，若時間允許再加）
- BERT / GPT 深度學習文本分類（要求9，選做）
- 繁體中文 NER 命名實體識別（依賴 CKIP，暫不實作）
- LangGraph 多 Agent 協作（O3 選做，不在必做主線內）
- 付費 API 用量計費與限流機制
- Facebook / Instagram / X（Twitter）社群爬蟲（Meta 封鎖 / X 需付費，不可行）

---

## 技術選型備註（已查證 2026-06-22）

| 項目 | 選定值 | 選定原因 |
|------|--------|---------|
| Django | **5.2.15 LTS** | LTS 支援至 2028 年 4 月，相較 6.0.6 更穩定；6.0 非 LTS 且 2026 年 8 月即結束主流支援 |
| Python | **3.12** | Django 5.2 LTS 相容 3.10–3.14；3.12 有最長支援期且套件相容性最廣 |
| Gemini SDK | **google-genai 2.9.0** | `google-generativeai` 已正式棄用，`google-genai` 已 GA（穩定版） |
| Gemini 模型 | **gemini-3.5-flash** | ⚠️ `gemini-2.0-flash` 已於 2026/6/1 **停止服務**，必須升級 |
| Claude SDK | **anthropic 0.111.0** | 截至 2026/6/18 最新版，MIT 授權 |
| Claude 模型 | **claude-sonnet-4-6** | 生產量產首選（$3/$15 per M tokens），平衡效能與成本 |
| APScheduler | **APScheduler 3.11.2** | APScheduler 4.x 仍為 alpha，3.x 為穩定量產版 |
| django-apscheduler | **0.7.0** | 最新版（2024/9），已知可搭配 Django 5.x |
| faiss-cpu | **1.14.2** | 截至 2026/5 最新穩定 PyPI 版（MIT 授權） |
| Docker base | **python:3.12-slim-bookworm** | 官方 slim 映像，體積小、持續維護 |
| 前端圖表 | **Chart.js 4.x**（CDN） | 現行最新穩定版，API 與 2.x 不同，需注意 |
| CSS 框架 | **Bootstrap 5.3**（CDN） | LTS 支援，官方維護中 |
| YouTube API | **YouTube Data API v3** | 每日 10,000 free quota；每 6h 排程消耗 < 3,000 units |
| LangChain（選用） | **langchain==1.3.1** + **langgraph==1.2.0** | O2/O3 選做功能，不強制 |

---

## 補充場景（2026-06-24）：主站 3D 浮動 AI 客服

### 場景 17：馬娘客服「成田路」即時互動

使用者在主站任何前台頁面瀏覽時，右下角可看到常駐的 3D 虛擬客服「馬娘客服 成田路」。當使用者移動滑鼠時，角色會自然轉頭與視線跟隨游標；當使用者在輸入框提問後，客服先顯示「思考中...」，再把 AI 回覆以頭上泡泡方式呈現，並短暫露出微笑表情，讓 AI 互動從傳統聊天室提升為更具臨場感的角色陪伴體驗。

**使用者價值：**
- 降低使用門檻：不需切換到獨立聊天頁，主站即可提問。
- 強化沉浸感：3D 角色追視與表情回饋讓互動更自然。
- 提升即時性：保留既有 Agentic AI 能力，同步提供前台輕量問答入口。
