"""
pipeline/label_sentiment.py  (P4 修復版 + Phase 2b DB 化)

T3: Gemini API 情緒標記
輸入:  pipeline/bilibili_uma_tokenized.csv（或透過 --source 指定其他來源）
       Phase 2b 新增：--db 旗標可改讀 NewsData(status='tokenized')
輸出:  data/processed/uma_news_preprocessed.csv（新增 sentiment + summary 欄位）
       Phase 2b 新增：同步 bulk_update NewsData sentiment + status='labeled'

P4 修復項目：
- 移除硬寫 CONFIG_PATH（/workspaces/…），改由 .env 讀取 GEMINI_API_KEY
- 改用 google-genai SDK（requests.post → client.models.generate_content）
- 支援多資料來源（--source 參數）
- 輸出路徑自動使用專案根目錄下的 data/processed/
"""

import os
import re
import json
import time
import argparse
import sys

import pandas as pd
from dotenv import load_dotenv

# ── 載入 .env ────────────────────────────────────────────────
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
load_dotenv(os.path.join(_PROJECT_DIR, ".env"), override=True)

# ── Django 環境（Phase 2b：雙輸出需要 ORM）─────────────────────
sys.path.insert(0, _PROJECT_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

# ── SDK 匯入（延後以確保 dotenv 已載入）────────────────────
from google import genai
from google.genai import types

# ── 路徑設定 ─────────────────────────────────────────────────
DATA_DIR  = os.path.join(_PROJECT_DIR, "data")
RAW_DIR   = os.path.join(DATA_DIR, "raw")
PROC_DIR  = os.path.join(DATA_DIR, "processed")
os.makedirs(PROC_DIR, exist_ok=True)

# ── 預設 I/O（可被 --source 覆蓋）───────────────────────────
# P4 修復：改讀 preprocess.py 的多來源合併輸出
DEFAULT_IN_CSV  = os.path.join(PROC_DIR, "uma_combined_tokenized.csv")
DEFAULT_OUT_CSV = os.path.join(PROC_DIR, "uma_news_preprocessed.csv")

# ── 重試模型列表（gemini-2.0-flash 已於 2026-06-01 停服；gemini-2.5-flash 已過時，統一使用 gemini-3.5-flash）──
MODELS = ["gemini-3.5-flash"]

# ── Source 對應輸入檔 ─────────────────────────────────────────
SOURCE_INPUT_MAP = {
    "bilibili": os.path.join(_SCRIPT_DIR, "bilibili_uma_tokenized.csv"),
    "bahamut":  os.path.join(RAW_DIR, "bahamut_uma_raw.csv"),
    "ettoday":  os.path.join(RAW_DIR, "ettoday_uma_raw.csv"),
    "udn":      os.path.join(RAW_DIR, "udn_uma_raw.csv"),
    "gamme":    os.path.join(RAW_DIR, "gamme_uma_raw.csv"),
}


# ═══════════════════════════════════════════════════════════════
# Gemini SDK 呼叫（使用 google-genai，非舊版 requests.post）
# ═══════════════════════════════════════════════════════════════

def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY 未設定，請在 .env 中加入：GEMINI_API_KEY=你的金鑰"
        )
    return genai.Client(api_key=api_key)


def call_gemini_sdk(client: genai.Client, model: str, prompt: str) -> str | None:
    """使用新版 google-genai SDK 呼叫模型，回傳文字或 None"""
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=500,
                temperature=0.1,
            ),
        )
        return response.text
    except Exception as e:
        print(f"    [{model}] SDK 呼叫失敗：{e}")
        return None


# ═══════════════════════════════════════════════════════════════
# JSON 解析
# ═══════════════════════════════════════════════════════════════

def extract_json(text: str) -> dict:
    """從 Gemini 回傳的文字中提取 JSON，容錯處理"""
    text = re.sub(r'```(?:json)?|```', '', text).strip()
    # 方法 1：直接解析
    try:
        return json.loads(text)
    except Exception:
        pass
    # 方法 2：regex 提取 JSON 物件
    m = re.search(r'\{.*?\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    # 方法 3：提取數值
    score_m = re.search(r'sentiment_score["\s:]+([0-9.]+)', text)
    summ_m  = re.search(r'summary["\s:]+["\u300c]([^""\u300d\n]{1,20})', text)
    if score_m:
        return {
            "sentiment_score": float(score_m.group(1)),
            "summary": summ_m.group(1) if summ_m else "",
        }
    return {"sentiment_score": 0.5, "summary": ""}


def make_prompt(title: str, content: str) -> str:
    snippet = str(content)[:150]
    return (
        "你是情緒分析師，只輸出一個JSON物件，無任何說明。\n"
        f"標題：{title}\n"
        f"內容：{snippet}\n\n"
        '輸出（只有這個JSON）：{"sentiment_score":0.0,"summary":""}\n'
        "規則：sentiment_score 範圍 0.0~1.0\n"
        "  活動/周年/費用折扣/登入獎勵 → 0.75~0.90\n"
        "  競賽/節日/一般活動 → 0.55~0.65\n"
        "  平衡調整/賽事通知/維護/停服 → 0.20~0.40\n"
        "summary：繁體中文 10 字以內\n"
    )


# ═══════════════════════════════════════════════════════════════
# 主邏輯
# ═══════════════════════════════════════════════════════════════

def label_one(row: pd.Series, client: genai.Client) -> tuple[float, str, bool]:
    """標記單筆，回傳 (score, summary, api_success)"""
    prompt        = make_prompt(str(row.get("title", "")), str(row.get("content", "")))
    response_text = None

    for model in MODELS:
        text = call_gemini_sdk(client, model, prompt)
        if text:
            response_text = text
            break

    if not response_text:
        print(f"    ⚠ API 全部失敗，使用預設值 0.5")
        return 0.5, "", False

    data    = extract_json(response_text)
    score   = max(0.0, min(1.0, float(data.get("sentiment_score", 0.5))))
    summary = str(data.get("summary", ""))
    return score, summary, True


CHECKPOINT_EVERY = 50  # 每處理 N 筆就寫一次 checkpoint


# ── Phase 2b：DB 讀取（--db 模式）────────────────────────────
def _load_df_from_db(source_tag: str) -> pd.DataFrame | None:
    """從 NewsData(status='tokenized') 讀取待標記資料。"""
    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(status='tokenized')
        if source_tag:
            qs = qs.filter(source=source_tag)
        df_db = pd.DataFrame.from_records(list(qs.values(
            'item_id', 'source', 'date', 'category', 'title', 'content',
            'tokens_filtered', 'top_key_freq', 'sentiment',
        )))
        if not df_db.empty:
            df_db['date'] = df_db['date'].astype(str)
            print(f"[label_sentiment] 從 DB 讀取 {len(df_db)} 筆（status=tokenized）")
            return df_db
        print("[label_sentiment] DB 無 status=tokenized 資料")
    except Exception as exc:
        print(f"[label_sentiment] DB 讀取失敗：{exc}")
    return None


# ── Phase 2b：DB 回寫 ─────────────────────────────────────────
def _sync_sentiment_to_db(df: pd.DataFrame) -> None:
    """將 sentiment 結果 bulk_update 至 NewsData，status 改為 'labeled'。"""
    try:
        from app_user_keyword_db.models import NewsData
        item_ids = df['item_id'].astype(str).tolist()
        existing = {
            obj.item_id: obj
            for obj in NewsData.objects.filter(item_id__in=item_ids)
        }
        to_update = []
        for _, row in df.iterrows():
            iid = str(row.get('item_id', ''))
            obj = existing.get(iid)
            if obj is None:
                continue
            s = row.get('sentiment')
            if s is None or str(s) in ('', 'nan', 'None'):
                continue
            obj.sentiment = float(s)
            obj.status    = 'labeled'
            to_update.append(obj)
        if to_update:
            NewsData.objects.bulk_update(
                to_update, ['sentiment', 'status'], batch_size=500,
            )
            print(f"[label_sentiment] DB bulk_update {len(to_update)} 筆 → status=labeled")
        else:
            print("[label_sentiment] 無符合條件的 DB 項目需更新")
    except Exception as exc:
        print(f"[label_sentiment] DB 回寫失敗（CSV 仍已正常寫出）：{exc}")


def run(in_csv: str | None, out_csv: str, source_tag: str = "", use_db: bool = False) -> None:
    # ── 讀取輸入資料 ─────────────────────────────────────────
    if use_db:
        df = _load_df_from_db(source_tag)
        if df is None or df.empty:
            print("[label_sentiment] DB 模式無可用資料，終止")
            return
    else:
        if not in_csv or not os.path.exists(in_csv):
            print(f"[label_sentiment] 輸入檔不存在：{in_csv}")
            sys.exit(1)
        df = pd.read_csv(in_csv, sep='|')
        print(f"[label_sentiment] 讀取：{in_csv}  筆數：{len(df)}")

    if "sentiment" not in df.columns:
        df["sentiment"] = None
    if "summary" not in df.columns:
        df["summary"]   = ""
    if source_tag and "source" not in df.columns:
        df["source"]    = source_tag

    # 斷點續跑：若 out_csv 已存在則合併既有 sentiment，跳過已標記列
    already_labeled: dict = {}
    if os.path.exists(out_csv):
        try:
            df_prev = pd.read_csv(out_csv, sep='|', usecols=["item_id", "sentiment", "summary"])
            for _, r in df_prev.iterrows():
                s = r.get("sentiment")
                if s is not None and str(s) not in ("", "nan", "None"):
                    already_labeled[str(r["item_id"])] = (float(s), str(r.get("summary", "")))
            print(f"[label_sentiment] 既有標記：{len(already_labeled)} 筆，將跳過")
        except Exception as e:
            print(f"[label_sentiment] 讀取舊輸出失敗，從頭標記：{e}")

    # 將已有標記回填至 df
    for i, row in df.iterrows():
        iid = str(row.get("item_id", ""))
        if iid in already_labeled:
            df.at[i, "sentiment"] = already_labeled[iid][0]
            df.at[i, "summary"]   = already_labeled[iid][1]

    client        = get_client()
    api_successes = 0
    processed     = 0

    for i, row in df.iterrows():
        iid = str(row.get("item_id", ""))
        existing = row.get("sentiment")
        # 跳過所有已有 sentiment 的列（包含 comment_ 和新聞列）
        if existing is not None and str(existing) not in ("", "nan", "None"):
            print(f"[{i+1:03d}/{len(df)}] [SKIP] {str(row.get('title',''))[:40]}")
            continue

        print(f"[{i+1:03d}/{len(df)}] [{row.get('category','?')}] {str(row.get('title',''))[:45]}")
        score, summary, ok = label_one(row, client)
        if ok:
            api_successes += 1
        df.at[i, "sentiment"] = score
        df.at[i, "summary"]   = summary
        processed += 1
        print(f"  → score={score:.2f}  ok={ok}  summary={summary[:25]}")
        time.sleep(0.8)

        # checkpoint 存檔
        if processed % CHECKPOINT_EVERY == 0:
            df.to_csv(out_csv, sep='|', index=False)
            print(f"  [checkpoint] 已存 {processed} 筆進度 → {out_csv}")

    df.to_csv(out_csv, sep='|', index=False)

    # ── Phase 2b：同步至 DB ───────────────────────────────────
    _sync_sentiment_to_db(df)

    # 驗收報告
    pos = (df["sentiment"] >= 0.6).sum()
    neu = ((df["sentiment"] > 0.4) & (df["sentiment"] < 0.6)).sum()
    neg = (df["sentiment"] <= 0.4).sum()
    print(f"\n=== 驗收報告 ===")
    print(f"API 成功呼叫：{api_successes} / {len(df)}")
    print(f"正面(≥.6)：{pos}  中性(0.4-.6)：{neu}  負面(≤.4)：{neg}")
    print(f"正負佔比：{(pos+neg)/max(len(df),1)*100:.0f}%")
    print(f"已儲存：{out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Gemini 情緒標記 Pipeline")
    parser.add_argument(
        "--source",
        choices=list(SOURCE_INPUT_MAP.keys()),
        default=None,
        help="指定資料來源（bilibili/bahamut/ettoday/udn/gamme）；省略則使用 bilibili tokenized CSV",
    )
    parser.add_argument("--in",  dest="in_csv",  default=None, help="覆蓋輸入 CSV 路徑")
    parser.add_argument("--out", dest="out_csv", default=None, help="覆蓋輸出 CSV 路徑")
    parser.add_argument(
        "--db", action="store_true",
        help="Phase 2b：改讀 NewsData(status='tokenized') 而非 CSV",
    )
    args = parser.parse_args()

    if args.db:
        in_csv = None
    elif args.in_csv:
        in_csv = args.in_csv
    elif args.source:
        in_csv = SOURCE_INPUT_MAP.get(args.source, DEFAULT_IN_CSV)
    else:
        in_csv = DEFAULT_IN_CSV

    out_csv = args.out_csv or DEFAULT_OUT_CSV
    run(in_csv, out_csv, source_tag=args.source or "", use_db=args.db)


if __name__ == "__main__":
    main()
