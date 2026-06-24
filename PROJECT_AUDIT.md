# 專案健檢報告 — umamusume-information-platform

> 檢查日期：2026-06-24　範圍：全專案掃描（已排除 `參考專案/` 內的課程範例）
> 技術棧：Django 5.2 + SQLite + APScheduler + Discord Bot + 多個爬蟲管線 + RAG/LLM

整體而言，功能面相當完整且持續迭代中（CHANGELOG 達 148KB）。主要風險集中在**安全性／權限控管**與**正式環境部署設定**；另有不少可清理的死碼與待優化項目。以下依嚴重度分級。

---

## 🔴 高風險（建議優先處理）

| # | 問題 | 位置 | 說明 |
|---|------|------|------|
| H1 | **全站零身分驗證** | 全專案（`login_required` 出現 0 次） | 沒有任何 view 受登入保護。 |
| H2 | **crawler-admin 後台完全公開且含破壞性操作** | `app_crawler_admin/urls.py`、`api_views.py` | `api/clear_db/`、`data-manager/clear-source`、`delete-item`、`discord/messages/delete`、啟停 Discord Bot 等端點任何人都能呼叫，可清空資料庫。 |
| H3 | **71 個 `@csrf_exempt`** | 全專案（含上述破壞性 API） | 大量 POST 端點關閉 CSRF 保護，配合無驗證等同對外開放寫入。 |
| H4 | **正式環境預設不安全** | `website_configs/settings.py` | `DEBUG` 預設 `True`(L17)、`SECRET_KEY` 有硬編碼 fallback(L15)、`ALLOWED_HOSTS` 預設 `*`(L19)、`CORS_ORIGIN_ALLOW_ALL=True`(L157)，且完全沒有 `SECURE_*` / `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` 設定。 |
| H5 | **死碼中使用 `eval()`** | `app_scchen/views.py:13`、`app_taipei_mayor/views.py:13`、`app_top_keyword/views.py:16`、`app_top_ner/views.py:78`、`app_top_person/views.py:25`、`app_top_person_db/views.py:106` | `eval()` 直接執行字串內容，屬任意程式碼執行風險。這些 app 未在 `INSTALLED_APPS`，建議連同 H8 一併刪除；若要保留請改用 `ast.literal_eval`。 |
| H6 | **無版本控管、機密暴露** | 專案根目錄 | 不是 git repo 且無 `.gitignore`。`.env`（含 Gemini／Anthropic／Discord 真實金鑰）、`db.sqlite3`(57MB) 等敏感檔皆裸放。建議 `git init` + 完整 `.gitignore`，並在洩漏風險下輪替金鑰。 |

---

## 🟠 中風險（部署／正確性）

| # | 問題 | 位置 | 說明 |
|---|------|------|------|
| M1 | **SQLite 多進程共寫** | `docker-compose.yml` | `web-poa`、`discord-bot` 各自掛載 `.:/app` 共用同一個 `db.sqlite3`，加上 APScheduler 排程同時寫入，高機率出現 `database is locked`。建議正式環境換 PostgreSQL。 |
| M2 | **正式環境 media 無法服務** | `nginx/nginx.conf`、`website_configs/urls.py:64` | Django 僅在 `DEBUG=True` 時掛載 `MEDIA_URL`，而 nginx 只設了 `/static/` 沒有 `/media/`。一旦 `DEBUG=False`，上傳圖片／生成圖表會 404。 |
| M3 | **反向代理 SSL 設定缺失** | `settings.py` / `nginx.conf` | nginx 只聽 80、未配 HTTPS，Django 也未設 `SECURE_PROXY_SSL_HEADER`。若對外服務需補上 TLS 與相關標頭。 |
| M4 | **錯誤被無聲吞掉** | 全專案 | 3 處裸 `except:`（`app_correlation_analysis/views.py:64`、`app_top_person_db/models.py:17`、`app_user_keyword_sentiment/views.py:126`）＋約 30 處 `except ...: pass`，會掩蓋真實錯誤、增加除錯難度。 |

---

## 🟡 低風險（清理／程式品質）

| # | 問題 | 位置 | 說明 |
|---|------|------|------|
| L1 | **7 個死 app 資料夾** | `app_scchen`、`app_taipei_mayor`、`app_top_keyword`、`app_top_ner`、`app_top_person`、`app_top_person_db`、`app_top_person_sqlalchemy_db` | 皆未列入 `INSTALLED_APPS`／`urls.py`，疑為課程遺留。建議移除（同時解決 H5）。 |
| L2 | **根目錄殘留暫存檔** | `Untitled`(0B)、`_changelog_debug.txt`(0B)、`_tmp_cats.json`、`narita-top-road-runtime-config.txt`、`narita-top-road-vrm-data.txt` | 臨時／除錯產物，建議清理或移入專屬資料夾。 |
| L3 | **超大單一檔案** | `app_crawler_admin/api_views.py`（約 92KB／2300+ 行） | 難維護，建議依功能（status／trigger／schedule／data-manager／discord）拆分模組。 |
| L4 | **`print()` 除錯殘留** | 約 25 個 views／api 檔 | 正式碼應改用既有 `LOGGING` 設定的 logger，而非 `print()`。 |
| L5 | **幾乎沒有測試** | 全專案僅 4 個 `def test_`（集中在 `app_agent_uma/tests.py`） | 缺乏自動化測試，重構與改版易回歸。建議至少為核心 API 與爬蟲轉換邏輯補測試。 |
| L6 | **巨型二進位檔放在專案根** | `1077_Narita Top Road.vrm`(79MB)、`data/`(78MB) | 若日後納入 git 會讓 repo 暴漲，建議以 `.gitignore` 排除或改用 Git LFS／外部儲存。 |
| L7 | **CHANGELOG 過大** | `CHANGELOG.md`(148KB) | 可考慮依版本切分歸檔（如 `CHANGELOG/2026-Q2.md`）。 |

---

## 🔌 API 串接與 SPEC 規格落差（2026-06-24 補充）

> 依需求補查：前後端 API 連接錯誤、SPEC 規格與實際程式碼差異。

### 前後端 API 串接：大致正確，但有脆弱寫法

整體串接健康——逐一比對前端 `fetch()` 與後端路由：`crawler-admin` 的 10 個 API（`clear_db`、`rebuild_rag`、`run_pipeline`、`youtube_quota`…）與 `uma-info` 的 6 個 Guild API（`settings/save`、`sync-cache`、`rules/add`、`rules/<pk>/delete`…）**全部對得上後端 `urls.py`，未發現呼叫不存在端點的情況**。

| # | 問題 | 位置 | 說明 |
|---|------|------|------|
| A1 | **相對路徑 fetch（脆弱）** | `app_agent_langchain/templates/.../chat.html:145,163`、`app_agent_langgraph/templates/.../chat.html:109,127` | 使用 `fetch('api/chat/')`、`fetch('api/clear/')` 相對路徑，僅在頁面 URL 維持結尾斜線時才正確解析；一旦少了斜線或頁面被巢狀路由載入即會 404。建議改用 `{% url %}`。 |
| A2 | **URL 多為硬編碼** | 各前端模板 | 全站 `fetch()` 中僅 6 處用 `{% url %}`、26 處硬編碼路徑。路由一改動前端即斷，建議統一改 `{% url %}`。 |

### SPEC 規格 vs 實際程式碼

| # | 問題 | 嚴重度 | 位置 | 說明 |
|---|------|:---:|------|------|
| S1 | **Discord Bot 仍用已棄用且未安裝的舊 SDK** | 🔴 | `app_discord_bot/management/commands/run_discord_bot.py:444-455` | `_generate_ai_answer()`（Bot 站內 AI 問答）用 `import google.generativeai` + `genai.configure()` + `GenerativeModel()`，但 SPEC 與 `requirements.txt` 明文「勿使用 google-generativeai（已棄用）」且**未安裝該套件**。執行時會丟 `ModuleNotFoundError`，被外層 `except Exception` 吞掉，使用者永遠只收到「😅 AI 目前無法回應」。其餘 10 個 Gemini 模組皆已正確改用新版 `google-genai`（`genai.Client`），唯獨此處遺漏。**修正**：改用 `from google import genai; client = genai.Client(...)`。 |
| S2 | **`db.sqlite3` 疑似截斷／損壞** | 🟠 | `db.sqlite3` | 檔案標頭宣稱 18196 頁 × 4096B ≈ 74.5MB，實際檔案僅 53MB；`PRAGMA integrity_check` 回報 `database disk image is malformed`，連 `sqlite_master` 都讀不全（兩次讀取 md5 一致，排除讀取中被寫入）。若屬實則 SPEC 的資料完整性指標（NewsData ≥1000、5 來源…）無法驗證，且與 M1（多進程共寫 SQLite）風險相符。**注意**：本專案資料夾為掛載磁碟，建議在使用者本機原生環境再跑一次 `sqlite3 db.sqlite3 "PRAGMA integrity_check;"` 確認；若確損壞，用 `sqlite3 db.sqlite3 ".recover" \| sqlite3 db_fixed.sqlite3` 嘗試救回。 |
| S3 | **相依套件版本與 SPEC 不一致／未鎖定** | 🟡 | `requirements.txt` vs `SPEC/INTENT_SPEC.md` §技術選型 | SPEC 寫 `langchain==1.3.1`、`langgraph==1.2.0`，`requirements.txt` 卻是 `langchain>=1.3.0`、`langgraph>=0.2.0`（下限 0.2.0 與 SPEC 的 1.2.0 矛盾）。多數套件用 `>=` 未鎖版，環境重現性差。建議與 SPEC 對齊並 pin 版本。 |
| S4 | **模型字串漂移** | 🟡 | `app_uma_info_portal/views.py:41-44`、`settings.py:232`（`gemini-2.5-flash-image-preview`） | SPEC 標準文字模型為 `gemini-3.5-flash`，但程式多處仍出現 `gemini-2.5-flash`、`gemini-3.1-flash-lite` 等字串（多為前台標籤對照表，非實際呼叫，影響較小）。建議統一集中管理避免混淆。 |

### 已比對確認「規格與程式相符」的項目（無須處理）

- `app_comment_sentiment`：SPEC 曾標註「缺 views + templates」，現已補齊 `dashboard` view、`dashboard.html` 與完整路由（C1 已修）。
- `scrape_bahamut` / `analyze_comments` management commands 皆存在。
- `entrypoint.sh` 存在且已在 `docker-files-poa/Dockerfile` 正確掛載（`ENTRYPOINT`）。
- 11 個 Gemini 模組中 10 個已正確使用新版 `google-genai`（僅 S1 例外）。

---

## 建議處理順序

1. **立即**：為 `crawler-admin` 與所有破壞性／寫入 API 加上 `@staff_member_required`／`login_required`（H1–H3）。
2. **部署前**：建立正式環境設定檔，強制 `DEBUG=False`、移除 `SECRET_KEY` fallback、收斂 `ALLOWED_HOSTS`／CORS、補 `SECURE_*`（H4）；補 nginx `/media/`（M2）。
3. **盡快**：`git init` + `.gitignore`，並評估金鑰輪替（H6）。
4. **規劃**：SQLite → PostgreSQL（M1）。
5. **功能修復**：修好 Discord Bot AI 問答的舊 SDK 引用（S1）；原生環境確認並修復 `db.sqlite3`（S2）。
6. **清理**：刪除 7 個死 app（連帶 `eval`）、清除暫存檔、拆分 `api_views.py`、對齊／鎖定相依版本（H5、L1–L4、S3–S4）。
7. **前端**：把硬編碼 `fetch()` 改為 `{% url %}`（A1–A2）。
8. **長期**：補測試、處理無聲例外（M4、L5）。

---

*備註：本報告為靜態程式碼掃描結果，未實際執行專案。部分項目需依實際部署環境再行確認：金鑰是否已外洩、是否已有外層反向代理處理 TLS／驗證、以及 `db.sqlite3` 是否真損壞（因專案位於掛載磁碟，建議於本機原生環境再跑一次 `PRAGMA integrity_check`）。*
