# 任務規格（Task Spec）

> 回答「分幾步做」。
> 每個任務有明確的輸入、輸出、驗收條件（Acceptance Criteria）。
>
> 最後更新：2026-06-23（依據 feature-completion-plan.html + admin-platform-plan.html 補全）

---

## 任務優先級總覽

| 優先級 | 任務 | 說明 | 預估工時 | 狀態 |
|--------|------|------|---------|------|
| 🚨 **緊急** | C1 | 新增 `/comment_sentiment/` 頁面（阻礙 T18 驗收） | 2–3h | ✅ 完成 |
| 🚨 **緊急** | C2 | Navbar 補全所有已實作 App 入口連結 | 1h | ✅ 完成 |
| 🔥 **高優先** | H1 | 建立 RAG 持久化知識庫（build_index.py） | 2–3h | ✅ 完成 |
| 🔥 **高優先** | H2 | 新增 scrape_bahamut management command | 1–2h | ✅ 完成 |
| 🔥 **高優先** | H3 | 建立 knowledge_base/ 目錄與馬娘知識文件 | 0.5h | ✅ 完成 |
| 🔧 **管線** | P1 | 修復 bilibili 爬蟲輸出格式 | 0.5h | ✅ 完成 |
| 🔧 **管線** | P2 | 修復 bahamut 爬蟲輸出格式 | 0.75h | ✅ 完成 |
| 🔧 **管線** | P3 | 統一 ETtoday/UDN/Gamme 欄位順序 | 0.33h | ✅ 完成 |
| 🔧 **管線** | P4 | 修復 label_sentiment.py（核心斷點） | 0.75h | ✅ 完成 |
| 🔧 **管線** | P5 | 簡化 preprocess.py（移除 patch 邏輯） | 0.5h | ✅ 完成 |
| 🔧 **管線** | P6 | 執行完整 Pipeline 並重建 DB | 1–2h | ✅ 完成 |
| ⚡ **中優先** | M1 | 修正 poa_agent_introduction 視圖 | 0.5h | ✅ 完成 |
| ⚡ **中優先** | M2 | 更新 entrypoint.sh 加入 RAG 建立步驟 | 0.5h | ✅ 完成 |
| ⚡ **中優先** | M3 | RAG 改為支援預建索引 + 使用者上傳並存 | 1h | ✅ 完成 |
| 💡 **選用** | O1 | 移植 app_rag_agent（Agentic RAG） | 3–4h | ✅ 完成 |
| 💡 **選用** | O2 | 移植 app_agent_langchain（LangChain） | 3–4h | ✅ 完成 |
| 💡 **選用** | O3 | 移植 app_agent_langgraph（LangGraph） | 4–5h | ✅ 完成 |
| 💡 **選用** | O4 | 移植 app_course_intro（API 介紹頁） | 1–2h | ✅ 完成 |
| 💡 **選用** | O5 | 整合 YouTube Data API v3 | 6–8h | ✅ 完成 |
| 💡 **Discord** | D1–D8 | Discord Bot 自動新聞推播系統 | 8–10h | ✅ 完成 |
| 🛡️ **後台** | A1 | 爬蟲後台重命名為「情報站控制台」 | 0.5h | 待實作 |
| 🛡️ **後台** | A2 | 平台健康儀表板（全平台統計卡片） | 2–3h | 待實作 |
| 🛡️ **後台** | A3 | 控制台 Navbar 入口更新 | 0.5h | 待實作 |
| 📊 **後台** | B1 | YouTubeQuotaLog 模型 + 配額圓環圖 | 1–2h | 待實作 |
| 📊 **後台** | B2 | YouTube 搜尋關鍵字管理（新增/刪除） | 1h | 待實作 |
| 📊 **後台** | B3 | YouTube 影片清單管理頁 | 1–2h | 待實作 |
| 📊 **後台** | B4 | YouTube 情感趨勢折線圖 | 1h | 待實作 |
| 📊 **後台** | B5 | YouTube 手動觸發爬取按鈕 | 0.5h | 待實作 |
| 📈 **後台** | C-AD | 統一資料儀表板（多來源比較 + 情感分布） | 2–3h | 待實作 |
| 🤖 **後台** | D-AD | Discord Bot 管理頁（狀態 + 設定 + 歷史） | 2–3h | 待實作 |
| 🧠 **後台** | E1 | RAG 索引狀態顯示 + 知識庫文件清單 | 1h | 待實作 |
| 🧠 **後台** | E2 | RAG 一鍵重建索引 + 文件上傳 | 1–2h | 待實作 |
| ⚙️ **後台** | F1 | Pipeline 分步執行頁 + 執行歷史 | 3–4h | 待實作 |

---

## 2026-06-23 補充修正（前後台職責分離）

### X1 — 前台排程控制移轉至後台（完成）

**目標：** 將前台頁面的排程與任務觸發控制集中到 `crawler-admin`，避免前台誤觸背景任務。

**實作內容：**
1. `app_comment_sentiment/dashboard.html`
   - 移除前台「啟動/停止排程」與「觸發爬蟲/分析」按鈕
   - 改為導向後台 `app_crawler_admin:dashboard` / `app_crawler_admin:schedule`
2. `app_crawler_admin/api_views.py` + `app_crawler_admin/urls.py`
   - 新增 `api/comment_sentiment/status|start|stop|run_task|history/`
3. `app_crawler_admin/dashboard.html`
   - 新增「留言情感排程控制（後台統一）」區塊
4. `app_dashboard/views.py`
   - `scheduler_page` 改為 redirect 到 `app_crawler_admin:schedule`

**驗收條件：**
- [x] 前台 `comment_sentiment` 頁不再可直接啟停排程或觸發背景任務
- [x] 後台可查詢並控制留言情感排程狀態
- [x] 舊 `/dashboard/scheduler/` 入口導向後台排程頁，不再打不存在 API

### X2 — 留言情感圖表資料契約修正（完成）

**目標：** 修正前端六維度圖表與後端 JSON 鍵值不一致問題。

**實作內容：**
1. `app_comment_sentiment/views.py::api_data()`
   - `cheer_up` → `excited`
   - `dumbfounded` → `disappointed`

**驗收條件：**
- [x] `comment_sentiment` 六維度圓餅圖可正確顯示六個維度數值
- [x] 不再出現因鍵值錯置導致的維度長期為 0

### X3 — 「巴哈 Article = 0」診斷與一鍵匯入（完成）

**目標：** 明確區分「尚未匯入資料」與「資料表讀取錯誤」，並提供後台操作入口。

**實作內容：**
1. `app_crawler_admin/views.py::_get_platform_stats()`
   - 新增 `article_count_hint` / `article_count_error`
2. `app_crawler_admin/dashboard.html`
   - 在巴哈 Article 卡片顯示提示與錯誤說明
   - 新增「巴哈資料匯入」按鈕
3. `app_crawler_admin/api_views.py`
   - 新增 `POST /crawler-admin/api/import_bahamut/`（背景啟動 `manage.py scrape_bahamut`）

**驗收條件：**
- [x] 當 `Article=0` 時，後台顯示可判讀原因，不是單純 0
- [x] 可由後台直接啟動巴哈匯入任務

---

## 前置確認

| 項目 | 確認方式 |
|------|---------|
| w12 專案路徑可存取 | `參考專案/w12/w12-5-HW.../umamusume-llm-report/` 存在 |
| w13 專案路徑可存取 | `參考專案/w13/w13-2-Yahoo comment analysis and background shedule/` 存在 |
| w16 專案路徑可存取 | `參考專案/w16/w16-2-Our POA deployment佈署使用Docker/websit-poa-docker-compose/` 存在 |
| Python 環境 | `python --version` ≥ 3.12 |
| Gemini API 金鑰 | 已取得，格式 `AIza...` |
| Anthropic API 金鑰 | 已取得，格式 `sk-ant-...` |
| Docker Desktop | `docker --version` 已安裝且 Engine 執行中 |
| 專案基底已建立 | `manage.py`、`website_configs/settings.py` 存在 |

---

## 階段一：建立專案基底（Phase 1）— 已完成

---

### T1 — 建立工作目錄與複製 w12 基底

**輸入：** `參考專案/w12/w12-5-HW.../umamusume-llm-report/`

**輸出：** `umamusume-information-platform/`（工作根目錄，已有 w12 內容）

**步驟：**
1. 確認工作目錄 `umamusume-information-platform/` 已建立（即本倉庫）
2. 將 w12 `umamusume-llm-report/` 全部內容複製進來
   - 排除：`.venv/`、`__pycache__/`、`db.sqlite3`、`.env`
3. 確認 `manage.py` 與 `website_configs/settings.py` 存在

**驗收條件：**
- [ ] `manage.py` 存在於專案根目錄
- [ ] `website_configs/settings.py` 存在
- [ ] `app_user_keyword_llm_report/views.py` 存在
- [ ] `pipeline/crawl_bilibili_uma.py` 存在

---

### T2 — 設定 Python 環境與安裝初始套件

**步驟：**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install django==5.2.15
pip install python-dotenv django-cors-headers
pip install pandas jieba requests beautifulsoup4
```

**驗收條件：**
- [ ] `python -c "import django; print(django.VERSION)"` 顯示 `(5, 2, 15, ...)`
- [ ] `python manage.py check` 無 Error（初始狀態）

---

### T3 — 建立 .env 金鑰檔案

**輸出：** `.env`

**內容：**
```
GEMINI_API_KEY=你的Gemini金鑰（格式：AIzaSy...）
ANTHROPIC_API_KEY=你的Claude金鑰（格式：sk-ant-api03-...）
DJANGO_SECRET_KEY=隨機生成的長字串
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
# YOUTUBE_API_KEY=（選用 O5 時填入）
```

**驗收條件：**
- [ ] `.env` 存在，兩組 API 金鑰已填寫
- [ ] `.gitignore` 含 `.env` 行

---

### T4 — 執行資料庫遷移與資料匯入

**步驟（依序執行）：**
```bash
python manage.py makemigrations
python manage.py migrate
python scripts/import_uma_data.py
python scripts/generate_topkey_csv.py
python scripts/generate_top_character_csv.py
```

**驗收條件：**
- [ ] `migrate` 完成無 Error
- [ ] `scripts/import_uma_data.py` 印出 `Done. Total: NNN rows`（NNN > 100）
- [ ] `app_uma_top_keyword/dataset/uma_topkey_with_category.csv` 存在
- [ ] `python manage.py shell -c "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())"` 印出 > 100

---

### T5 — 升級 Gemini SDK 並修改 LLM Prompt

> ⚠️ 關鍵：`google-generativeai` 已棄用，必須改用 `google-genai 2.9.0`；`gemini-2.0-flash` 已停服，必須改用 `gemini-3.5-flash`。

**步驟：**
```bash
pip uninstall google-generativeai -y
pip install google-genai==2.9.0
```

**修改 `app_user_keyword_llm_report/views.py`：**
```python
# 舊（刪除）
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# 新
from google import genai
from google.genai import types as genai_types
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
```

**驗收條件：**
- [ ] `pip show google-genai` 顯示 `Version: 2.9.0`
- [ ] `import google.generativeai` 不再被使用
- [ ] 報告字數 ≥ 500 字，模型為 `gemini-3.5-flash`

---

### T6 — 新增 Claude 雙模型支援

```bash
pip install anthropic==0.111.0
```

**驗收條件：**
- [ ] 選擇 Gemini → 呼叫 `gemini-3.5-flash`，成功取得報告
- [ ] 選擇 Claude → 呼叫 `claude-sonnet-4-6`，成功取得報告
- [ ] 兩者均能在 40 秒內取得 ≥ 500 字 Markdown 報告
- [ ] `ANTHROPIC_API_KEY` 未設定時，選 Claude 回傳清楚的錯誤訊息

---

### T7 — 更新 settings.py 與 urls.py 加入所有 app

**目標 INSTALLED_APPS：** 見 DESIGN_SPEC.md § 4

**目標 urls.py：** 見 DESIGN_SPEC.md § 5

**驗收條件：**
- [ ] `python manage.py check` 無任何 Error 或 Warning
- [ ] 存取 `http://127.0.0.1:8000/` → 首頁角色 PK
- [ ] 所有 navbar 連結均可存取，無 404

---

## 階段二：緊急修復（Critical Fixes）

---

### C1 — 新增 /comment_sentiment/ 頁面（留言情感儀表板）

> 🚨 **T18 驗收測試 #8 阻礙項目**：`http://localhost/comment_sentiment/` 必須顯示「巴哈貼文列表 + 情緒六維度圓餅圖」，但目前此 URL 完全不存在。

**根本原因：** 目前 `app_comment_sentiment` 只有排程 API 端點，沒有任何頁面視圖與 templates。

**步驟：**
1. 在 `app_comment_sentiment/views.py` 補充頁面視圖：`dashboard()` + `api_data()`（詳見 DESIGN_SPEC.md § 9.2）
2. 建立 `app_comment_sentiment/templates/app_comment_sentiment/` 目錄
3. 新增 `dashboard.html`（文章列表 + 情緒圓餅圖，參考 w13 設計，使用 Chart.js 4.x）
4. 在 `app_comment_sentiment/urls.py` 加入頁面路由：
   ```python
   path('', views.dashboard, name='dashboard'),
   path('api/data/', views.api_data, name='api_data'),
   ```
5. 在 `website_configs/urls.py` 加入：
   ```python
   path('comment_sentiment/', include('app_comment_sentiment.urls')),
   ```

**驗收條件：**
- [ ] 存取 `/comment_sentiment/` 回應 200
- [ ] 頁面顯示文章列表（即使無資料也不崩潰，顯示「尚無資料」提示）
- [ ] 有情緒資料的文章顯示六維度圓餅圖（Chart.js）
- [ ] `/comment_sentiment/api/data/` 返回合法 JSON
- [ ] T18 測試案例 #8 通過

---

### C2 — Navbar 補全所有已實作 App 的入口連結（T13）

> 🚨 **T18 驗收阻礙**：已實作的 `/agent/`、`/rag/`、`/dashboard/`、`/comment_sentiment/`、`/introduction/` 在 Navbar 中完全找不到，大量選單顯示「開發中」。

**目前 Navbar 缺少的連結：**
- AI助理 → `/agent/`（app_agent_uma）
- RAG知識庫 → `/rag/`（app_rag_uma）
- 留言情感儀表板 → `/comment_sentiment/`（C1 完成後）
- 公告儀表板 → `/dashboard/`（app_dashboard）
- 平台介紹 → `/introduction/`（app_poa_introduction）

**建議 Navbar 選單結構（`templates/base.html`）：**
```html
<!-- AI 功能下拉 -->
<div class="btn-group">
  <button class="btn dropdown-toggle" data-bs-toggle="dropdown">AI 功能</button>
  <div class="dropdown-menu">
    <a class="dropdown-item" href="{% url 'app_user_keyword_llm_report:home' %}">
      📝 AI 分析報告（Gemini / Claude）
    </a>
    <a class="dropdown-item" href="{% url 'app_agent_uma:chat' %}">
      🧠 Agentic AI 助理
    </a>
    <a class="dropdown-item" href="{% url 'app_rag_uma:rag_demo' %}">
      🔍 RAG 知識庫問答
    </a>
  </div>
</div>

<!-- 留言情感 -->
<a class="nav-link" href="{% url 'app_comment_sentiment:dashboard' %}">
  💬 留言情感儀表板
</a>

<!-- 平台介紹 -->
<a class="nav-link" href="{% url 'app_poa_introduction:introduction' %}">
  📖 平台介紹
</a>
```

**驗收條件：**
- [ ] Navbar 可直接到達 AI 助理（`/agent/`）
- [ ] Navbar 可直接到達 RAG 知識庫（`/rag/`）
- [ ] Navbar 可直接到達留言情感儀表板（`/comment_sentiment/`）
- [ ] Navbar 可直接到達平台介紹頁（`/introduction/`）
- [ ] 無「開發中」灰色佔位連結（改為真實連結或移除）
- [ ] T13 驗收條件全部通過

---

## 階段三：Feature Apps（Phase 2）

---

### T8 — 移植 app_comment_sentiment（巴哈留言情感排程）

**輸入：** `參考專案/w13/website-news-analysis-v13-ai-comment-sentiment/app_comment_sentiment/`

**步驟：**
1. 複製 `app_comment_sentiment/` 整個目錄
2. 安裝依賴：
   ```bash
   pip install APScheduler==3.11.2 django-apscheduler==0.7.0
   ```
3. **替換爬蟲目標**：
   - 將 `scrape_yahoo.py` 改為 `scrape_bahamut.py`（見 DESIGN_SPEC.md § 9.4）
4. **保留不改動**：
   - `models.py`（Article / Comment / ArticleEmotion）
   - `management/commands/analyze_sentiment.py`（或 `analyze_comments.py`）
   - `scheduler_manager.py`（APScheduler 設定）
5. 在 `settings.py` 加入 `'django_apscheduler'`、`'app_comment_sentiment'`
6. 執行 `python manage.py makemigrations app_comment_sentiment && migrate`
7. 設定排程（DESIGN_SPEC.md § 9.1）：爬蟲每 60 分鐘、情感標記每日 02:00

**驗收條件：**
- [ ] `python manage.py migrate` 無 Error
- [ ] Article / Comment / ArticleEmotion 三張表建立完成
- [ ] 手動執行爬蟲，成功寫入 ≥ 5 筆 Article 到 DB
- [ ] `python manage.py analyze_sentiment`（或 `analyze_comments`）能呼叫 Gemini 情感標記
- [ ] 存取 `http://127.0.0.1:8000/comment_sentiment/` → 顯示儀表板頁面（需先完成 C1）

---

### T9 — 確認 app_uma_top_keyword 與 app_uma_top_character

**驗收條件：**
- [ ] 存取 `/uma_top_keyword/`，選「卡池」，Top-10 → 長條圖 + 詞彙清單正確顯示
- [ ] 存取 `/uma_top_character/`，選「活動」，Top-10 → 角色排行長條圖正確顯示
- [ ] 類別選單含「活動 / 卡池 / 競賽 / 系統 / 其他」5 類

---

### T10 — 更新 app_poa_introduction（介紹頁）

**需改造內容：**
- 標題：改為「賽馬娘 Pretty Derby 輿情分析平台」
- 資料來源：改為巴哈姆特馬娘版（bsn=34421）+ Bilibili BWIKI + ETtoday + UDN + Gamme
- 功能說明：更新為本專案所有 app 截圖與說明
- AI 協助說明：加入「本頁說明使用 Gemini 3.5 Flash 協助撰寫」
- 技術架構圖：根據 DESIGN_SPEC.md § 1 重繪

**驗收條件：**
- [ ] 存取 `/introduction/` → 正確顯示介紹頁面
- [ ] 頁面標題明確顯示「賽馬娘」主題
- [ ] 頁面含 5 個資料來源說明
- [ ] 頁面含技術架構圖或功能截圖
- [ ] 頁面不含舊專案（台灣選舉、Yahoo 新聞）遺留文字

---

## 階段四：高優先修復（High Priority）

---

### H1 — 建立 RAG 持久化知識庫（build_index.py + FAISS 索引）

> 🔥 **T12 驗收要求**：`app_rag_uma/index/uma_knowledge.faiss` 必須存在；目前 RAG 是「記憶體暫存，重啟後清空」。

**步驟：**
1. 建立 `app_rag_uma/build_index.py`：
   - 讀取 `data/processed/uma_news_preprocessed.csv`（Bilibili 部分）+ `knowledge_base/` 文件
   - 切分 chunk（size=512, overlap=64）
   - 呼叫 `gemini-embedding-001` 生成 768 維嵌入向量（google-genai 2.9.0 新式 SDK）
   - 建立 `FAISS.IndexFlatIP` 並存儲
   ```python
   # app_rag_uma/build_index.py（關鍵片段）
   from google import genai
   client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
   resp = client.models.embed_content(model='gemini-embedding-001', contents=chunks)
   vectors = np.array([e.values for e in resp.embeddings], dtype=np.float32)
   index = faiss.IndexFlatIP(vectors.shape[1])
   index.add(vectors)
   faiss.write_index(index, str(INDEX_DIR / 'uma_knowledge.faiss'))
   ```
2. 確認 `app_rag_uma/index/` 目錄存在（自動建立）
3. 修改 `app_rag_uma/views.py` 啟動時載入索引（DESIGN_SPEC.md § 8.2）
4. 在 Docker `entrypoint.sh` 加入索引建立步驟（M2）

**驗收條件：**
- [ ] `python app_rag_uma/build_index.py` 執行成功
- [ ] `app_rag_uma/index/uma_knowledge.faiss` 存在
- [ ] `app_rag_uma/index/uma_knowledge_texts.pkl` 存在
- [ ] 存取 `/rag/` 無需上傳 PDF 即可直接提問
- [ ] 回答明確標示引用來源（Bilibili / knowledge_base 文件名）
- [ ] 伺服器重啟後知識庫仍然存在

---

### H2 — 新增 scrape_bahamut management command

> 🔥 目前 `app_comment_sentiment/management/commands/` 只有 `analyze_comments.py`，缺少爬蟲指令。

**步驟：**
1. 建立 `app_comment_sentiment/management/commands/scrape_bahamut.py`
2. 抓取 `https://forum.gamer.com.tw/B.php?bsn=34421` 熱門貼文
3. 將貼文存入 `Article`，留言存入 `Comment`（含 upvotes / downvotes）
4. 更新 `app_comment_sentiment/views.py` 的 `api_run_task`，加入 `task == 'scraper'` 分支

**驗收條件：**
- [ ] `python manage.py scrape_bahamut` 執行無報錯
- [ ] 成功寫入 ≥ 5 筆 Article 到 DB
- [ ] 留言情感儀表板能顯示這些文章（C1 完成後）

---

### H3 — 建立 knowledge_base/ 目錄並加入馬娘知識文件

> 🔥 `app_agent_uma/agent_core/tools.py` 的 `read_local_document()` 工具從 `knowledge_base/` 讀取文件。此目錄目前**不存在**，Agent 呼叫此工具時一定報錯。

**步驟：**
1. 在專案根目錄建立 `knowledge_base/` 目錄
2. 加入至少一份馬娘知識文件（例如：`uma_characters.md`、`uma_gacha.md`）
3. 可從 `pipeline/uma_characters_bilingual.csv` 轉換生成 Markdown：
   ```python
   import pandas as pd
   from pathlib import Path
   df = pd.read_csv('pipeline/uma_characters_bilingual.csv')
   kb_dir = Path('knowledge_base')
   kb_dir.mkdir(exist_ok=True)
   with open(kb_dir / 'uma_characters.md', 'w', encoding='utf-8') as f:
       f.write('# 賽馬娘角色列表\n\n')
       for _, row in df.iterrows():
           f.write(f"## {row.get('name_tw', row.get('name', ''))}\n")
           f.write(f"- 日文名：{row.get('name_jp', '')}\n")
           f.write(f"- 英文名：{row.get('name_en', '')}\n\n")
   ```
4. 確認 Agent 的 `read_local_document` 工具能正確讀取並返回內容

**驗收條件：**
- [ ] `knowledge_base/` 目錄存在且含 ≥ 1 份 `.md` 文件
- [ ] Agent 詢問「介紹停鐘阿玲」→ 正確呼叫 `read_local_document` 並回應
- [ ] 不存在 `knowledge_base/` 時，工具回傳「找不到知識庫」而非崩潰

---

## 階段五：進階 AI 功能（Phase 3）

---

### T11 — 建立 app_agent_uma（Agentic AI 馬娘助理）

**輸入：** `參考專案/w16/.../app_agent_genaisdk/`

**步驟：**
1. 複製參考 app，重命名為 `app_agent_uma`
2. **定義 6 種工具函數**（DESIGN_SPEC.md § 7.1）：
   - `get_keyword_volume`、`get_keyword_sentiment`、`search_articles`
   - `get_top_characters`、`get_top_keywords`、`read_local_document`
3. **建立 Agent 對話頁** `/agent/`（Bootstrap 5.3 ChatGPT 風格，顯示工具呼叫 badge）
4. 在 `urls.py` 加入 `app_agent_uma.urls`

**驗收條件：**
- [ ] 存取 `/agent/` → 顯示對話頁面
- [ ] 輸入「最近卡池公告玩家反應如何？」→ AI 自動呼叫工具 + 回傳分析結果
- [ ] 工具呼叫次數 ≥ 2 次（頁面顯示工具名稱 badge）
- [ ] 回覆為繁體中文，字數 ≥ 100 字
- [ ] 模型顯示為 `gemini-3.5-flash`

---

### T12 — 建立 app_rag_uma（RAG 馬娘知識庫）

**輸入：** `參考專案/w16/.../app_rag_basic/`

**步驟：**
1. 複製參考 app，重命名為 `app_rag_uma`
2. 安裝依賴：`pip install faiss-cpu==1.14.2`
3. 建立 `app_rag_uma/build_index.py`（詳見 H1）
4. 預載知識庫文件（`knowledge_base/*.md`）
5. 執行 `python app_rag_uma/build_index.py` 建立索引
6. 建立 RAG 查詢 views（DESIGN_SPEC.md § 8.2）
7. 在 `urls.py` 加入 `app_rag_uma.urls`

**驗收條件：**
- [ ] `app_rag_uma/index/uma_knowledge.faiss` 存在
- [ ] 存取 `/rag/` → 顯示 RAG 問答頁面
- [ ] 輸入問題 → 取得含引用來源的回答
- [ ] 不存在索引時，API 回傳清楚錯誤訊息

---

### T13 — 更新 base.html（確保所有 app 的 navbar 一致）

**步驟：**
1. 確認 `templates/base.html` 為雙主題設計系統版本
2. Navbar 連結更新（含 C2 的所有補充連結）：
   ```
   首頁（角色PK）| 聲量觀測站 | 情感分析 | DB搜尋 | AI功能▾ | 留言情感 | 熱門關鍵詞 | 熱門角色 | 爬蟲後台 | 平台介紹
   AI功能▾ → AI 分析報告、Agentic AI 助理、RAG 知識庫問答
   ```
3. Footer 更新資料來源：
   ```
   資料來源：Bilibili BWIKI · 巴哈姆特（bsn=34421）· ETtoday · UDN · Gamme ·
   Gemini 3.5 Flash · Claude Sonnet 4.6
   ```

**驗收條件：**
- [ ] 全站 Navbar 含所有已實作 app 連結
- [ ] 右下角日/夜切換按鈕正常運作，`localStorage` 保留狀態
- [ ] Footer 含「巴哈姆特」及「5 來源」資料來源說明
- [ ] 不含任何舊專案遺留連結

---

## 階段六：資料管線修復（Pipeline Repair P1–P6）

---

### P1 — 修復 bilibili 爬蟲輸出格式

**修改 `pipeline/crawl_bilibili_uma.py` 四處：**

1. **輸出路徑遷移**：
   ```python
   ROOT_DIR = Path(__file__).parent.parent
   OUT_CSV  = ROOT_DIR / 'data' / 'raw' / 'bilibili_uma_raw.csv'
   ```

2. **調整 `CSV_COLUMNS`**（新增 `source`，對齊統一規格）：
   ```python
   CSV_COLUMNS = ['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']
   ```

3. **日期解析移至爬蟲端**：在 `crawl_article()` 中呼叫 `parse_date_bilibili()`，直接輸出 `YYYY-MM-DD`：
   ```python
   import re
   def parse_date_bilibili(raw: str) -> str:
       m = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', raw)
       if m:
           y, mo, d = m.groups()
           return f"{y}-{int(mo):02d}-{int(d):02d}"
       return '2024-01-01'
   ```

4. **簡體→繁體移至爬蟲端**（`category`、`title`、`content` 存檔前轉換）：
   ```python
   return {
       "item_id":    f"bilibili_{idx}",
       "source":     "bilibili",
       "date":       parse_date_bilibili(time_text),
       "category":   cc.convert(classify_title(entry['title'])),
       "title":      cc.convert(title),
       "content":    cc.convert(content),
       "link":       entry["url"],
       "photo_link": img_link,
   }
   ```

**驗收條件：**
- [ ] 輸出至 `data/raw/bilibili_uma_raw.csv`
- [ ] 第一行含 `source` 欄位
- [ ] `date` 欄位為 `YYYY-MM-DD` 格式
- [ ] `category` 欄位為繁體中文（活動/卡池/競賽/系統/其他）

---

### P2 — 修復 bahamut 爬蟲輸出格式

**修改 `pipeline/crawl_bahamut_uma.py`：**

1. **輸出路徑遷移**：
   ```python
   OUT_CSV    = ROOT_DIR / 'data' / 'raw' / 'bahamut_uma_raw.csv'
   FAILED_CSV = ROOT_DIR / 'data' / 'raw' / 'bahamut_uma_failed.csv'
   ```

2. **論壇標籤 → 標準分類對應表**（保留原始標籤至 `raw_category`）：
   ```python
   CATEGORY_MAP = {
       '活動': '活動', '系統': '系統', '攻略': '系統',
       '公告': '其他', '情報': '其他', '討論': '其他',
       '閒聊': '其他', '問題': '其他', '心得': '其他',
       '整理': '其他', '史實': '其他', '繪圖': '其他',
       '繪畫': '其他', '小說': '其他',
   }
   def normalize_category(raw_cat: str) -> str:
       return CATEGORY_MAP.get(raw_cat, '其他')
   ```

3. **日期格式清理**（去掉 `編輯` 後綴）：
   ```python
   def parse_date_bahamut(raw: str) -> str:
       raw = re.sub(r'\s*編輯\s*$', '', str(raw)).strip()
       m = re.match(r'(\d{4}-\d{2}-\d{2})', raw)
       return m.group(1) if m else '2024-01-01'
   ```

4. **更新 `CSV_COLUMNS`**（標準欄位優先，Bahamut 獨有欄位跟在後面）：
   ```python
   CSV_COLUMNS = [
       'item_id', 'source', 'date', 'category', 'title', 'content',
       'link', 'photo_link',
       'raw_category', 'author', 'gp', 'reply_count', 'view_count',
   ]
   ```

**驗收條件：**
- [ ] 輸出至 `data/raw/bahamut_uma_raw.csv`
- [ ] `category` 欄位只含「活動/卡池/競賽/系統/其他」5 種值
- [ ] `date` 欄位為純 `YYYY-MM-DD`
- [ ] 原始論壇標籤保存於 `raw_category` 欄位
- [ ] `photo_link` 欄位存在（可為空字串）

---

### P3 — 統一 ETtoday / UDN / Gamme 欄位順序

**三個檔案各修改一行**（`source` 移至第二欄，對齊統一規格）：

```python
# pipeline/crawl_ettoday_uma.py（以及 crawl_udn_uma.py, crawl_gamme_uma.py 同步修改）
# 修改前：
CSV_COLUMNS = ['item_id', 'title', 'date', 'category', 'content', 'link', 'photo_link', 'source']

# 修改後：
CSV_COLUMNS = ['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']
```

> 這三個爬蟲的 `classify_title()` 已使用繁體中文分類關鍵字、日期已是 `YYYY-MM-DD`，**不需要其他修改**。

**驗收條件：**
- [ ] 三個 CSV 的第二欄均為 `source`
- [ ] `preprocess.py` 讀取時無需逐欄補丁

---

### P4 — 修復 label_sentiment.py（核心 Pipeline 斷點修復）

> 🚨 **這是讓 UDN/Gamme 進入系統的最關鍵修復**。目前有三個硬編碼錯誤：
> (1) 讀取 `pipeline/bilibili_uma_tokenized.csv`（忽略其他來源）；
> (2) `CONFIG_PATH` 指向 `/workspaces/8_10_emi/` 另一環境；
> (3) 使用舊式 `requests.post` 呼叫 Gemini（非 `google-genai` SDK）。

**修改步驟：**

1. **修正輸入路徑**：
   ```python
   # 修改前
   IN_CSV      = os.path.join(DIR, "bilibili_uma_tokenized.csv")
   CONFIG_PATH = "/workspaces/8_10_emi/google_ai_config.json"

   # 修改後
   _ROOT   = Path(__file__).parent.parent
   IN_CSV  = _ROOT / 'data' / 'processed' / 'uma_combined_tokenized.csv'
   OUT_CSV = _ROOT / 'data' / 'processed' / 'uma_news_preprocessed.csv'
   ```

2. **改用 `.env` 讀取 API Key**：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   API_KEY = os.getenv('GEMINI_API_KEY')
   if not API_KEY:
       raise ValueError("GEMINI_API_KEY 未設定，請檢查 .env 檔案")
   ```

3. **更新 Gemini 呼叫為 `google-genai 2.9.0` 新式 SDK**：
   ```python
   from google import genai
   from google.genai import types as genai_types
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
   ```

4. **增量標記支援**（已有 sentiment 值的列跳過）：
   ```python
   for i, row in df.iterrows():
       existing = row.get('sentiment')
       if existing is not None and str(existing) not in ('', 'nan', 'None'):
           continue
       # ... 呼叫 Gemini 標記 ...
   ```

**驗收條件：**
- [ ] 執行 `python pipeline/label_sentiment.py` 無報錯啟動
- [ ] 讀取 `data/processed/uma_combined_tokenized.csv`（多來源合併版）
- [ ] 輸出 `data/processed/uma_news_preprocessed.csv` 含 UDN/Gamme 來源的列
- [ ] 使用 `gemini-3.5-flash`（非已棄用的 2.0-flash）
- [ ] 不再依賴 `CONFIG_PATH` 硬編碼路徑

---

### P5 — 簡化 preprocess.py（移除 patch 邏輯 + 對齊統一規格）

完成 P1–P3 後，`preprocess.py` 原本用來處理各來源格式差異的補丁邏輯可大幅精簡。

**可移除的補丁邏輯（P1-P3 完成後不再需要）：**
- 每個來源逐欄補缺失欄位的迴圈（`for c in cols: if c not in df_src.columns: ...`）
- OpenCC 對 `category` 和 `title` 的轉換（P1 已在爬蟲端完成）
- 複雜的 `parse_date()` 多格式容錯（各爬蟲已統一輸出 `YYYY-MM-DD`）

**保留的核心邏輯：**
- 合併多來源 DataFrame（`pd.concat(frames)`）
- 依 `link` 去重複
- jieba 斷詞 + 詞性標注 + Top-15 關鍵字頻率
- 對 `content` 做 OpenCC 簡→繁（防止 bilibili 內文漏網之魚）
- 輸出 `data/processed/uma_combined_tokenized.csv`

**驗收條件：**
- [ ] 執行 `python pipeline/preprocess.py` 成功完成，無 KeyError
- [ ] 輸出 `data/processed/uma_combined_tokenized.csv`
- [ ] UDN、Gamme 筆數出現在輸出統計中

---

### P6 — 執行完整 Pipeline 並重建 DB（5 來源完整資料入庫）

P1–P5 完成後執行完整資料管線：

```bash
# Step 1: 重新爬取（若 raw 資料需要更新）
python pipeline/crawl_bilibili_uma.py
python pipeline/crawl_bahamut_uma.py
python pipeline/crawl_ettoday_uma.py
python pipeline/crawl_udn_uma.py
python pipeline/crawl_gamme_uma.py

# Step 2: 多來源合併前處理
python pipeline/preprocess.py

# Step 3: Gemini 情感標記（約 14 分鐘/1,000 筆）
python pipeline/label_sentiment.py

# Step 4: 生成熱門 CSV
python scripts/generate_topkey_csv.py
python scripts/generate_top_character_csv.py

# Step 5: 清空 DB 並重新匯入
python scripts/import_uma_data.py --clear
```

**預期執行後資料量：**

| 來源 | 預期 DB 筆數（下限） |
|------|-------------------|
| bilibili | ≥ 150 筆 |
| bahamut | ≥ 500 筆 |
| ettoday | ≥ 200 筆 |
| udn | ≥ 150 筆（現況 0） |
| gamme | ≥ 30 筆（現況 0） |
| **合計** | **≥ 1,000 筆**（現況 344） |

**驗收條件：**
- [ ] `uma_news_preprocessed.csv` 含 5 個 source 值
- [ ] DB `NewsData` 總筆數 ≥ 1,000
- [ ] 搜尋 UDN 來源有結果回傳
- [ ] 搜尋 Gamme 來源有結果回傳
- [ ] 熱門關鍵字與熱門角色 CSV 已更新

---

## 階段七：中優先修復（Medium Priority）

---

### M1 — 修正 poa_agent_introduction 視圖

> `app_agent_uma/views.py` 的 `poa_agent_introduction()` 嘗試讀取 `app_agent_genaisdk`、`app_agent_langchain`、`app_agent_langgraph` 三個**不存在的目錄**中的 Markdown 文件，導致顯示三個 "Cannot find" 錯誤。

**快速方案（M1-A，推薦）**：

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

同時在 `app_agent_uma/urls.py` 加入此視圖的路由。

**驗收條件：**
- [ ] 存取 `/agent/introduction/`（或對應 URL）不顯示 "Cannot find" 錯誤
- [ ] 正確渲染 `第一階段說明.md` 內容

---

### M2 — 更新 entrypoint.sh 加入 RAG 索引建立步驟

完成 H1 後，更新 `docker-files-poa/entrypoint.sh`：

```bash
#!/bin/bash
set -e

python manage.py migrate

COUNT=$(python manage.py shell -c \
  "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())" \
  2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
    echo "初始化資料..."
    python scripts/import_uma_data.py
    python scripts/generate_topkey_csv.py
    python scripts/generate_top_character_csv.py
fi

if [ ! -f "app_rag_uma/index/uma_knowledge.faiss" ]; then
    echo "建立 RAG 知識庫索引..."
    python app_rag_uma/build_index.py || echo "RAG 索引建立失敗（跳過）"
fi

exec gunicorn website_configs.wsgi:application \
    --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

**驗收條件：**
- [ ] 第一次 `docker compose up`：DB 匯入 + RAG 索引均自動建立
- [ ] 第二次 `docker compose up`：不重複匯入（idempotent 保護）
- [ ] RAG 索引已存在時跳過建立步驟

---

### M3 — RAG 改為支援預建索引 + 使用者上傳並存

修改 `app_rag_uma/views.py`：
- 啟動時從磁碟載入預建 FAISS 索引
- 使用者上傳 PDF 後的向量**疊加**到已存在的索引上（非覆蓋）

詳見 DESIGN_SPEC.md § 8.2。

**驗收條件：**
- [ ] 伺服器啟動時自動從磁碟載入預建索引
- [ ] 上傳 PDF 後，新向量疊加到預建索引，不清空已有知識庫
- [ ] 同時查詢預建知識庫和上傳文件的內容，均能正確回答

---

## 階段八：Docker 部署（Phase 4）

---

### T14 — 建立 requirements.txt（版本釘牢）

詳見 DESIGN_SPEC.md § 12。

**驗收條件：**
- [ ] `pip install -r requirements.txt` 完成無衝突
- [ ] `requirements.txt` 不含 `google-generativeai`（已棄用）
- [ ] `requirements.txt` 不含 `openai`（不再用於呼叫 Gemini）
- [ ] 含 `markdown>=3.5`（M1 需要）

---

### T15 — 建立 Dockerfile

詳見 DESIGN_SPEC.md § 11.3。

**驗收條件：**
- [ ] `docker build -t umamusume-platform .` 成功完成（無報錯）
- [ ] 映像大小合理（< 2 GB）

---

### T16 — 建立 docker-compose.yml 與 Nginx 設定

詳見 DESIGN_SPEC.md § 11.1 / 11.4。

**環境變數：** `web-poa` 與 `discord-bot` 的 `env_file` 指向專案根目錄 `./.env`（與本機開發共用，不需另建 `docker-files-poa/.env`）。

**驗收條件：**
- [ ] `docker compose build` 成功
- [ ] `docker compose up -d` 後，`http://localhost` 可正常存取首頁
- [ ] Nginx 正確服務靜態檔案
- [ ] Django 後端不暴露到 80 以外

---

### T17 — 資料初始化 Docker 腳本（entrypoint.sh）

詳見 DESIGN_SPEC.md § 11.2 與 M2。

**驗收條件：**
- [ ] `docker compose up` 後，首頁有資料（DB 已初始化）
- [ ] 第二次 `docker compose up`，不重複匯入
- [ ] `/admin/` 可登入

---

## 階段九：驗收與繳交（Phase 5）

---

### T18 — 端對端功能驗收

**步驟：**
1. `docker compose up -d`
2. 開啟瀏覽器 `http://localhost`

**完整測試案例：**

| # | 測試項目 | 操作 | 預期結果 |
|---|---------|------|---------|
| 1 | 首頁角色 PK | 選 2 個角色，點擊比較 | 角色卡片 + 比較圖表，無 error |
| 2 | 日/夜主題切換 | 點擊右下角 ☀/🌙 | 全站配色正確切換，重整後保留狀態 |
| 3 | 聲量分析 | 輸入「卡池」，週數 12 | 長條圖 + 折線圖正確顯示 |
| 4 | 情感分析 | 輸入「限定」 | 圓餅圖 + 正/負趨勢圖正確顯示 |
| 5 | DB 版查詢 | 輸入「活動」 | 公告連結清單（≤10 筆）+ 統計圖 |
| 6 | LLM 報告（Gemini） | 輸入「卡池」，選 Gemini，生成報告 | ≤40 秒取得 ≥500 字 Markdown 報告 |
| 7 | LLM 報告（Claude） | 同上，改選 Claude Sonnet 4.6 | ≤40 秒取得 ≥500 字 Markdown 報告 |
| 8 | 留言情感儀表板 | 開啟 `/comment_sentiment/` | 顯示巴哈貼文列表 + 情緒圓餅圖 |
| 9 | 熱門關鍵詞 | 選「卡池」，Top-10 | 長條圖 + 詞彙清單正確顯示 |
| 10 | 熱門角色 | 選「活動」，Top-10 | 角色排行長條圖正確顯示 |
| 11 | Agentic AI | 輸入「最近卡池反應如何？」 | 自動工具呼叫 ≥2 次 + 繁中分析結果 |
| 12 | RAG 問答 | 輸入馬娘相關問題（無需上傳 PDF） | 含引用來源的正確回答 |
| 13 | 介紹頁面 | 開啟 `/introduction/` | 完整平台說明、無舊專案遺留文字 |
| 14 | 查無結果 | 輸入「zzzzz」 | 顯示「查無結果」提示，不 crash |
| 15 | Admin | `/admin/` superuser 登入 | 能瀏覽 NewsData、Article 列表 |
| 16 | Navbar 完整性 | 點擊所有 Navbar 連結 | 無「開發中」佔位，無 404（C2） |
| 17 | 資料量確認 | 管理後台查看 NewsData 筆數 | ≥ 1,000 筆（P6 完成後） |

**驗收條件：**
- [ ] 所有 17 個測試案例通過（原 15 個 + 新增 2 個）
- [ ] `docker compose logs web` 無未捕獲的 Python Exception
- [ ] Nginx `docker compose logs nginx` 無 upstream 連接失敗

---

### T19 — 整理作業繳交檔案

**截圖清單（整理至 PDF）：**
- 首頁（角色 PK 比較圖）
- 聲量分析（長條圖 + 折線圖）
- 情感分析（圓餅圖）
- DB 版查詢結果
- AI 報告（Gemini 版 Markdown 渲染後）
- AI 報告（Claude 版對比）
- 留言情感儀表板（含情緒圓餅圖）
- Agentic AI 對話（含工具呼叫 badge）
- RAG 問答（含引用來源）
- 介紹頁面

**驗收條件：**
- [ ] PDF 報告存在，含所有截圖
- [ ] `zip` 解壓縮後，依 README 步驟可重現執行
- [ ] zip 檔案大小合理（< 100 MB）

---

## 階段十：選用加分項（Optional O1–O5）

---

### O1 — 移植 app_rag_agent（Agentic RAG + DB 知識庫）

**預估工時：** 3–4 小時

**說明：** 參考 w15 的 `app_rag_agent`，結合 RAG 語意搜尋工具 + DB 精確查詢工具 + 計算工具，由 Agent 動態決定呼叫哪個工具。

**驗收條件：**
- [ ] 存取對應 URL → 顯示 Agentic RAG 頁面
- [ ] 提問時 Agent 自動在 RAG 語意搜尋與 DB 精確查詢間切換
- [ ] 回答附引用新聞 ID + 連結

---

### O2 — 移植 app_agent_langchain（LangChain ReAct Agent）

**預估工時：** 3–4 小時

```bash
pip install langchain==1.3.1 langchain-core==1.4.0 \
  langchain-google-genai==4.2.2 langgraph==1.2.0
```

**說明：** 完成後 M1 問題（`poa_agent_introduction` 缺少第二階段說明文件）也可一併解決。

---

### O3 — 移植 app_agent_langgraph（LangGraph 狀態圖 Agent）

**預估工時：** 4–5 小時

**說明：** 三階段 Agentic AI 系列的最終章（GenAI SDK → LangChain → LangGraph），完整展示平台教學價值。

---

### O4 — 移植 app_course_intro（API 介紹與課程說明頁）

**預估工時：** 1–2 小時

**說明：** 改造為「賽馬娘平台技術說明 + 使用手冊」。

---

### O5 — 整合 YouTube Data API v3（app_youtube_uma）

**預估工時：** 6–8 小時

**環境設定：**
- 在 Google Cloud Console 啟用 YouTube Data API v3，取得 API Key
- 在 `.env` 加入 `YOUTUBE_API_KEY=AIzaSy...`

**實作步驟：**
1. 建立 `app_youtube_uma/` 目錄（DESIGN_SPEC.md § 2 目錄結構）
2. 建立 `models.py`（`YouTubeVideo` / `YouTubeComment`，見 DESIGN_SPEC.md § 3.6）
3. 建立 `pipeline/crawl_youtube_uma.py`（`requests` 呼叫 YouTube Data API v3）
4. 建立 `management/commands/crawl_youtube.py`（`python manage.py crawl_youtube`）
5. 建立 `views.py`（儀表板 + JSON API）與 `urls.py`
6. 建立 `jobs.py`（APScheduler 排程：每6h爬取、每日03:00情感標記）
7. 建立 `apps.py`（`AppConfig.ready()` 初始化排程）
8. 在 `settings.py` 加入 `'app_youtube_uma'`
9. 在 `urls.py` 加入 `path('youtube/', include('app_youtube_uma.urls'))`
10. 執行 `python manage.py makemigrations app_youtube_uma && migrate`

**Quota 使用估算：**
- 搜尋 1 次 = 100 units
- 影片清單 50 筆 = 50 units
- 每 6 小時排程：約消耗 500–700 units
- 每日總計 < 3,000 units（遠低於 10,000 free quota）

**驗收條件：**
- [ ] `python manage.py crawl_youtube` 執行成功，寫入 ≥ 10 部影片
- [ ] 存取 `/youtube/` → 顯示影片列表 + 情感儀表板
- [ ] `/youtube/api/videos/` 返回含 sentiment 的 JSON
- [ ] APScheduler 排程：每6h爬取、每日03:00情感標記（不衝突巴哈的02:00）
- [ ] 留言關閉的影片（HTTP 403）正確跳過，不崩潰

---

## 任務相依圖

```
[緊急修復（可立即執行）]
C1（/comment_sentiment/ 頁面）
C2（Navbar 補全）

[已完成基底（T1–T7）]
  ├── T8（app_comment_sentiment 移植）→ C1（補頁面）
  ├── T9（Top keyword/character 確認）
  ├── T10（app_poa_introduction 改造）
  │
  ├── T11（app_agent_uma）→ H2（scrape_bahamut command）
  │                       → H3（knowledge_base/ 建立）→ M1（poa_agent_intro 修正）
  │
  ├── T12（app_rag_uma）→ H1（build_index.py）→ M2（entrypoint.sh）
  │                                           → M3（預建索引 + 上傳並存）
  │
  ├── T13（base.html）→ C2（Navbar）
  │
  ├── [P1–P3（爬蟲格式統一）]→ P5（preprocess.py 簡化）
  │         ↓
  │         P4（label_sentiment.py 修復）→ P6（完整 Pipeline 執行）
  │
  ├── T14（requirements.txt）→ T15（Dockerfile）→ T16（docker-compose + nginx）
  │                                               → T17（entrypoint.sh）→ M2
  │                                                     ↓
  └──────────────────────────────────────────────── T18（端對端驗收）→ T19（繳交）

[選用（獨立，不影響主線）]
O1 ← (H1 + T12 完成後)
O2 + O3 ← (T11 完成後，可平行推進)
O4 ← (任何時候)
O5 ← (T8 完成後，複用 APScheduler 架構)
```

**執行優先序建議：**
1. **立即**：C1 → C2（修復 T18 阻礙，約 3–4 小時）
2. **接著**：H1 → H2 → H3（完整度提升，約 4–5 小時）
3. **管線**：P1 → P2 → P3 → P4 → P5 → P6（資料擴充，約 4–5 小時，含 API 等待）
4. **品質**：M1 → M2 → M3（約 2 小時）
5. **驗收**：T18 → T19
6. **加分**：O5（YouTube，最易實作且最有展示價值）

---

## 階段十一：資料管理中心重構（Admin Platform — admin-platform-plan.html）

> 依據 `admin-platform-plan.html` 規劃，將 `app_crawler_admin`（原爬蟲後台）擴充為「情報站控制台」，增加 YouTube API 管理、統一儀表板、Discord Bot 管理、RAG 知識庫管理、Pipeline 一鍵執行等模組。

---

### A1 — 爬蟲後台重命名（UI 更新）

**目標：** 將 Navbar 中「爬蟲後台」更名為「🛡️ 情報站控制台」，控制台頁面標題同步更新。

**步驟：**
1. 修改 `templates/base.html`：爬蟲後台連結文字改為「情報站控制台」
2. 修改 `app_crawler_admin/templates/app_crawler_admin/dashboard.html`：頁面標題更新
3. 可選：更新 `app_crawler_admin/apps.py` 的 `verbose_name`

**驗收條件：**
- [ ] Navbar 顯示「🛡️ 情報站控制台」
- [ ] `/crawler-admin/` 頁面標題顯示「情報站控制台」
- [ ] 功能不受影響

---

### A2 — 平台健康儀表板（控制台首頁改版）

**目標：** 控制台首頁顯示全平台統計卡片，提供即時狀態一覽。

**步驟：**
1. 更新 `app_crawler_admin/views.py` 的 `dashboard` 視圖，新增 context：
   - `NewsData.objects.count()`
   - `Article.objects.count()` / `Comment.objects.count()`
   - `YouTubeVideo.objects.count()`
   - `DiscordMessage.objects.count()`
   - FAISS 索引狀態（讀取 `app_rag_uma/index/uma_knowledge.faiss`）
   - Discord Bot 今日推播次數（`DiscordNewsLog`）
2. 更新 `dashboard.html`：以 Bootstrap 5 卡片展示上述數據
3. 加入快速操作按鈕（AJAX）：觸發爬蟲、重建 RAG、手動推播

**驗收條件：**
- [ ] 控制台首頁顯示 5 來源 NewsData 總筆數
- [ ] 顯示 YouTubeVideo 與 DiscordMessage 筆數
- [ ] 顯示 FAISS 索引狀態（存在/不存在 + 向量數量）
- [ ] 快速操作按鈕可用

---

### B1–B5 — YouTube API 管理頁

**目標：** 在 `/crawler-admin/youtube/` 提供 YouTube API 配額監控與管理。

**步驟（B1：YouTubeQuotaLog 模型）：**
```python
# app_crawler_admin/models.py（或 app_youtube_uma/models.py）
class YouTubeQuotaLog(models.Model):
    date          = models.DateField(auto_now_add=True, unique=True)
    units_used    = models.IntegerField(default=0)
    units_limit   = models.IntegerField(default=10000)
    last_crawl_at = models.DateTimeField(null=True, blank=True)
    videos_added  = models.IntegerField(default=0)
```

**步驟（B2–B5：管理頁面）：**
1. 新增 `app_crawler_admin/views.py` → `youtube_management()` 視圖
2. 新增 `app_crawler_admin/templates/app_crawler_admin/youtube.html`：
   - 配額圓環圖（Chart.js Doughnut）
   - 影片清單分頁表格
   - 情感趨勢折線圖
   - 手動爬取按鈕
3. 新增 URL：`path('youtube/', views.youtube_management, name='youtube_management')`
4. 新增 AJAX API：`/crawler-admin/api/youtube_quota/`、`/crawler-admin/api/youtube_crawl/`

**驗收條件：**
- [ ] `/crawler-admin/youtube/` 回應 200
- [ ] 配額圓環圖正確顯示今日用量
- [ ] 手動觸發爬取按鈕執行後顯示結果
- [ ] `YouTubeQuotaLog` 表建立完成（makemigrations + migrate）

---

### C-AD — 統一資料儀表板

**目標：** 在控制台首頁加入多來源資料量比較圖表。

**步驟：**
1. 新增 API：`GET /crawler-admin/api/source_stats/` 返回各來源 NewsData 筆數
2. 新增 API：`GET /crawler-admin/api/sentiment_stats/` 返回 Positive/Neutral/Negative 比例
3. 在 `dashboard.html` 加入兩個 Chart.js 圖表（長條圖 + 圓餅圖）

**驗收條件：**
- [ ] `/crawler-admin/api/source_stats/` 返回 5 個來源數量
- [ ] 控制台首頁顯示多來源資料量長條圖
- [ ] 控制台首頁顯示情感分布圓餅圖

---

### D-AD — Discord Bot 管理頁

**目標：** 在 `/crawler-admin/discord/` 或 `/discord/` 提供 Bot 狀態監控與管理。

**步驟：**
1. 更新 `app_discord_bot/views.py` → `dashboard()` 視圖，新增 Bot 狀態 context
2. 更新 `app_discord_bot/templates/app_discord_bot/dashboard.html`：
   - Bot 在線/離線狀態指示燈
   - 今日爬取訊息數 / 馬娘相關訊息數
   - `DiscordBotConfig` 設定顯示（Token 遮罩）
   - `DiscordNewsLog` 最近 10 筆推播記錄
3. 新增手動觸發新聞生成按鈕（AJAX）

**驗收條件：**
- [ ] `/discord/` 回應 200
- [ ] 頁面顯示今日 DiscordMessage 筆數
- [ ] 顯示最近 10 筆 DiscordNewsLog 記錄
- [ ] 手動觸發按鈕可用

---

### E1–E2 — RAG 知識庫管理頁

**目標：** 在 `/crawler-admin/rag/` 提供 RAG 索引狀態查看與重建功能。

**步驟（E1：狀態顯示）：**
1. 新增 `app_crawler_admin/views.py` → `rag_management()` 視圖
2. 讀取 `app_rag_uma/index/uma_knowledge.faiss`：存在 Y/N、大小、修改時間
3. 讀取 `knowledge_base/` 目錄：列出所有 `.md` / `.txt` 文件
4. 新增 API：`GET /crawler-admin/api/rag_status/`

**步驟（E2：重建索引 + 文件上傳）：**
1. 新增 API：`POST /crawler-admin/api/rebuild_rag/`（以 subprocess 非同步執行 `python app_rag_uma/build_index.py`）
2. 新增文件上傳 API：`POST /crawler-admin/api/upload_kb/`（接受 `.md` / `.txt` 文件，儲存至 `knowledge_base/`）

**驗收條件：**
- [ ] `/crawler-admin/rag/` 回應 200
- [ ] 頁面顯示 FAISS 索引向量數量
- [ ] 頁面列出 `knowledge_base/` 所有文件
- [ ] 重建索引 API 可用（非同步，立即回應 `{"status": "started"}`）

---

### F1 — Pipeline 分步執行頁

**目標：** 在 `/crawler-admin/pipeline/` 提供資料管線的可視化分步執行。

**步驟：**
1. 新增 `app_crawler_admin/views.py` → `pipeline_page()` 視圖
2. 新增 `app_crawler_admin/templates/app_crawler_admin/pipeline.html`：
   - 5 個 Step 的勾選框（可選擇性執行）
   - 每個 Step 的描述與預估時間
   - 執行歷史表格（最近 10 次，含 Step、時間、結果）
3. 新增 API：`POST /crawler-admin/api/run_pipeline/`（Body: `{"steps": [2, 3, 4]}`）
4. `CrawlerSchedule` 或 `CrawlerRun` 模型擴充，記錄 Pipeline 執行歷史

**驗收條件：**
- [ ] `/crawler-admin/pipeline/` 回應 200
- [ ] 可選擇 Step 2（preprocess）單獨執行
- [ ] 執行後顯示成功/失敗狀態
- [ ] 執行中可看到每一步增量 log（非結束後一次性顯示）
- [ ] 顯示總進度條（`progress_pct`）與預估剩餘時間（`estimated_remaining_s`）
- [ ] 每個 Step 顯示 mini 進度條（`steps[].progress_pct`）

---

### G2 — 爬蟲設定持久化與 API 防呆（2026-06-23 追加修復）

**目標：** 修復控制台 `settings` 頁「儲存後重整仍回預設值」問題，並同步補強 crawler-admin API 在非法輸入時的穩定性，避免 500 導致前端誤判為已儲存。

**步驟：**
1. `app_crawler_admin/templates/app_crawler_admin/settings.html`
   - 移除 `||` 造成的 falsy 覆蓋（`0` 被改成預設值）
   - 改為明確 `null/undefined` 判斷
   - `saveConfig()` / `loadAll()` / `resetConfig()` 補齊 AJAX 錯誤處理
2. `app_crawler_admin/api_views.py`
   - 新增 `_parse_int` / `_parse_float` / `_parse_bool` 解析工具
   - `api_config_save`：加入欄位驗證（`max_pages>=0`、`delay_max>=delay_min`）與結構化回傳 `config`
   - `api_log` / `api_history`：對查詢參數做安全轉型，避免 `int()` 例外 500
   - `api_schedule_save`：驗證 `mode` 與 `cron_expr`，避免髒資料入庫
3. `schedule.html` / `dashboard.html` / `live_monitor.html`
   - 針對寫入/控制類 API 增加 `error` callback，失敗時顯示明確錯誤訊息

**驗收條件：**
- [x] 設定 `max_pages=0` 後重整頁面，仍顯示 `0`（不再回到 `50`）
- [x] `delay_min > delay_max` 時 API 回傳 `400` 與錯誤訊息，不發生 500
- [x] `history?limit=oops` / `log?offset=oops` 不會炸裂，仍回 200（自動套安全預設）
- [x] 排程/停止/全部啟動 API 失敗時，前端有可見錯誤提示

---

### H4 — AI 生成新聞整合（首頁 + 後台操作介面）

**目標：** 參考 `umamusume-news-analysis-v1` 的 AI 新聞功能，改以本專案資料契約（`NewsData`）實作，並整合進前台首頁與 crawler-admin 後台架構。

**步驟：**
1. `app_user_keyword_llm_report/models.py`
   - 新增 `GeneratedNewsArticle` 模型（查詢條件、內文、來源引用、發布狀態、建立者）
   - 建立對應 migration
2. `app_user_keyword_llm_report/services_ai_news.py`
   - 建立服務層：資料檢索、context 建構、模型生成、fallback、DB 持久化
   - 新增封面圖生成：圖片一律 Gemini image model（不受 `provider` 影響）
   - 新增封面圖 fallback：`photo_link` → `link`
3. `app_user_keyword_llm_report/views.py` + `urls.py`
   - 新增 5 支 API：生成、前台最新、後台清單、狀態切換、刪除
4. `app_character_pk/templates/app_character_pk/home.html`
   - 新增首頁 AI 新聞精選模組（專業新聞排版 + loading/error/empty 狀態）
5. `app_crawler_admin`
   - 新增 `ai_news_management` 頁面與路由：`/crawler-admin/ai-news/`
   - 新增後台 UI：參數輸入、生成、發布切換、刪除、清單刷新
   - `base_admin.html` 與 `dashboard.html` 補 AI 新聞入口
6. `website_configs/settings.py` + `website_configs/urls.py`
   - 新增 `MEDIA_URL` / `MEDIA_ROOT`
   - 開發模式提供 `/media/` 檔案服務，讓封面圖可直接顯示

**驗收條件：**
- [x] `python manage.py check` 通過
- [x] `python manage.py makemigrations --check --dry-run` 無待建立 migration
- [x] 首頁可透過 API 顯示最新已發布 AI 新聞（無資料時顯示 placeholder）
- [x] 後台可生成 AI 新聞，並可切換發布狀態與刪除
- [x] 後台選擇 Claude 生成內文時，封面圖仍可正常生成

---

### H5 — AI 新聞改為自然語言輸入模式（優化）

**目標：** 將 AI 新聞生成由「關鍵詞輸入」升級為「自然語言輸入優先」，並提升檢索命中率與生成品質穩定性。

**步驟：**
1. `app_user_keyword_llm_report/services_ai_news.py`
   - 新增 query profile：`query_mode`（`keyword`/`natural_language`）與 `search_terms` 自動抽取
   - 新增自然語言檢索容錯：抽詞檢索命中不足時自動回退到基礎範圍檢索
   - 生成結果補回 `query_mode` 與 `search_terms` 給前台/後台顯示
2. `app_crawler_admin/templates/app_crawler_admin/ai_news.html`
   - 將輸入欄改為自然語言導向文案
   - 生成成功提示顯示模式與抽取詞，讓操作員可快速驗證檢索品質

**驗收條件：**
- [x] 可直接輸入自然語言需求句生成新聞（不需人工拆關鍵詞）
- [x] API 回傳含 `query_mode` 與 `search_terms`
- [x] 後台生成提示可顯示解析模式與檢索詞

---

### H6 — AI 新聞模型動態選單 + Discord 批次推播（優化）

**目標：**  
AI 新聞管理中心提供 Gemini/Claude 各三款模型（含屬性/成本標籤）且由後端 API 動態下發；同時新增「勾選多篇新聞批次推播至全部伺服器」能力。

**步驟：**
1. `app_user_keyword_llm_report/services_ai_news.py`
   - 新增文字模型目錄（model catalog）解析：`id/provider/model/label/attrs/cost_label`
   - 新增 `resolve_ai_news_text_model`，生成時改以 `model_id` 決定文字模型
   - 回傳 `text_model` 與 `image_model`（明確標示封面圖固定 Gemini）
2. `app_user_keyword_llm_report/views.py` + `urls.py`
   - 新增 `GET /api/model_options/`
   - `generate_ai_news` 支援 `model_id`（保留舊 `provider` 相容）
3. `app_crawler_admin/templates/app_crawler_admin/ai_news.html`
   - 模型下拉改為呼叫 `model_options` API 動態載入
   - 顯示模型屬性 / 成本小標籤（`pill` 膠囊樣式，非純文字提示）
   - 新聞清單新增勾選框與「批次推播勾選新聞」
4. `app_crawler_admin/api_views.py` + `urls.py`
   - 新增 `POST /api/ai-news/discord-push-articles/`
   - `news` 任務新增 `articles` 批次模式，單一任務內依序推播多篇文章
5. `website_configs/settings.py`
   - 新增 `AI_NEWS_TEXT_MODELS` / `AI_NEWS_DEFAULT_TEXT_MODEL` 設定入口（環境變數可覆蓋）

**驗收條件：**
- [x] `/crawler-admin/ai-news/` 模型選單由 API 載入，非前端硬編碼
- [x] 可看到 Gemini/Claude 各三款模型，且以膠囊標籤顯示屬性/成本
- [x] 生成新聞可帶 `model_id`，回傳包含 `text_model` 與 `image_model`
- [x] 勾選多篇新聞可一次啟動批次推播任務
- [x] `python manage.py check` 通過

---

## 套件版本快速參考（2026-06-22 查證）

| 套件 | 推薦版本 | 安裝指令 |
|------|---------|---------|
| Django | `5.2.15` | `pip install Django==5.2.15` |
| google-genai | `2.9.0` | `pip install google-genai==2.9.0` |
| anthropic | `0.111.0` | `pip install anthropic==0.111.0` |
| faiss-cpu | `1.14.2` | `pip install faiss-cpu==1.14.2` |
| APScheduler | `3.11.2` | `pip install APScheduler==3.11.2` |
| django-apscheduler | `0.7.0` | `pip install django-apscheduler==0.7.0` |
| markdown | `≥3.5` | `pip install markdown` |

> **常見陷阱**：
> - `pip install google-generativeai` → ❌ 已棄用
> - `model="gemini-2.0-flash"` → ❌ 已停服（2026/6/1）
> - `APScheduler==4.0.0a6` → ❌ alpha 版，不穩定
> - `Django==6.0.6` → ⚠️ 非 LTS，2026/8 截止主流支援
> - `label_sentiment.py` 硬編碼 `bilibili_uma_tokenized.csv` → ❌ P4 必須修復
> - `label_sentiment.py` 硬編碼 `/workspaces/8_10_emi/` → ❌ P4 必須修復

---

## 階段十二：主站 3D 浮動 AI 虛擬客服（2026-06-24）

### V1 — 「馬娘客服 成田路」前端落地（完成）

**目標：** 在主站提供常駐右下角 3D 虛擬客服，使用 `1077_Narita_Top_Road.vrm`，並串接 `POST /agent/chat/`。

**實作內容：**
1. 建立模型與前端資產目錄  
   - `static/app_dashboard/vrm/1077_Narita_Top_Road.vrm`  
   - `static/app_dashboard/js/ai-vrm-assistant.js`  
   - `static/app_dashboard/css/ai-vrm-assistant.css`
2. `templates/base.html`  
   - 新增固定定位客服容器（canvas 區、回覆泡泡、輸入框、發送按鈕）  
   - 注入客服樣式與 module script
3. `static/app_dashboard/js/ai-vrm-assistant.js`  
   - Three.js Scene/Camera/Renderer（`alpha: true`）  
   - `GLTFLoader + VRMLoaderPlugin` 載入 VRM  
   - 全域 `mousemove` → 2D 轉 3D target → `vrm.lookAt.target` 跟隨  
   - fetch 串接 `/agent/chat/`（含 `X-CSRFToken`）  
   - loading / success / error 泡泡狀態  
   - 回覆成功觸發表情（Happy → Neutral）
4. `app_agent_uma/views.py`  
   - `/agent/chat/` 同時支援 `application/json` 與既有表單 POST  
   - 統一回傳 `{"reply": "...", "message": "..."}`，並補齊錯誤訊息
5. `app_agent_uma/tests.py`  
   - 新增 JSON API 與主站掛載點自動化測試

**驗收條件：**
- [x] 右下角可看到常駐 3D 客服，背景透明  
- [x] 滑鼠移動時頭部/眼睛跟隨  
- [x] 發送問題時顯示「思考中...」  
- [x] `/agent/chat/` 請求攜帶 CSRF 並成功回覆  
- [x] AI 回覆顯示於模型上方泡泡  
- [x] 回覆時觸發模型表情互動  
- [x] `/agent/chat/` JSON 空訊息可回傳 400，不崩潰

---

## 階段十三：Discord 控制台任務可觀測性與整合（2026-06-24）

### D-OPS-1 — 手動任務可執行化（完成）

**目標：** 修復 `crawler-admin/discord` 手動任務「看得到按鈕但無法可靠執行」問題，四類任務統一由後端任務執行器處理。

**實作內容：**
1. `app_crawler_admin/api_views.py`
   - 新增 `api_discord_task_start` / `api_discord_task_status` / `api_discord_task_log`
   - 新增可執行 `crawl/classify/convert/news` 的背景任務 worker
   - `crawl/news` 改為可在後端建立短生命週期 Discord 連線完成任務，不再依賴前端提示「不可執行」
2. 相容保留舊端點：
   - `api_discord_run_classify`
   - `api_discord_run_convert`
   - `api_discord_trigger_news`
   - 新增 `api_discord_run_crawl`

**驗收條件：**
- [x] 四個任務皆可由控制台啟動
- [x] 任務啟動回傳 run id，可供後續輪詢
- [x] 同類任務執行中時不會重複建立第二個 run

### D-OPS-2 — 任務完整日誌與進度估計（完成）

**目標：** 手動任務執行時，前端可查看完整日誌、即時狀態與進度條，不再僅有「已啟動」訊息。

**實作內容：**
1. `app_discord_bot/models.py`
   - 新增 `DiscordTaskRun`（status/progress/log/result/error）
2. `app_discord_bot/migrations/0003_discordtaskrun.py`
   - 建立任務執行記錄資料表
3. `app_crawler_admin/templates/app_crawler_admin/discord.html`
   - 任務區加入「總進度條 + 日誌視窗」
   - 前端以 polling 輪詢 status/log API，動態更新畫面

**驗收條件：**
- [x] 任務執行中可看到日誌持續追加
- [x] 任務完成/失敗後有明確狀態與摘要
- [x] 進度條會隨狀態更新（非固定假值）

### D-OPS-3 — Discord 訊息查閱增強與刪除整合（完成）

**目標：** 訊息查閱區支援更高操作自由度：筆數控制、排序、日期/伺服器/頻道條件檢視與刪除整合。

**實作內容：**
1. `api_discord_recent_messages`
   - 新增 `keyword/date_from/date_to/guild_id/channel_id/classify/sort_by/sort_dir/limit/page`
   - 回傳 `total/total_pages` 與 `guild_name`
2. 新增 `api_discord_delete_messages`
   - 支援刪除勾選訊息
   - 支援依目前篩選條件批次刪除
3. `discord.html`
   - 新增篩選表單、排序選項、每頁筆數、分頁控制、勾選刪除

**驗收條件：**
- [x] 可依條件查詢且分頁顯示
- [x] 可刪除勾選訊息
- [x] 可刪除目前篩選結果

### D-OPS-4 — Discord 文章融入專案分析鏈（完成）

**目標：** Discord 來源資料可被全站統計與分析鏈辨識，不再被歸入預設來源。

**實作內容：**
1. `app_discord_bot/converter.py`
   - `NewsData` 匯入時補上 `source='discord'`
2. `app_crawler_admin/api_views.py`
   - `api_stats` / `api_source_stats` 回傳來源聯集（`SOURCE_META + NewsData 實際來源`）

**驗收條件：**
- [x] 新匯入 Discord 資料在 `NewsData.source` 為 `discord`
- [x] 統計 API 可回傳 `discord` 來源
