#!/bin/bash
# docker-files-poa/entrypoint.sh
# M2 修復：加入 RAG 索引建立步驟，使用 DB 筆數作為 idempotent 判斷
set -e

echo "=== 賽馬娘資訊平台 啟動中 ==="

# ─────────────────────────────────────────
# 若 compose 指定了啟動指令（如 Discord Bot），走精簡流程：
# 等 web-poa 完成資料庫遷移後直接執行該指令，
# 不重複 migrate / collectstatic / 匯入（避免兩容器同時寫 sqlite 打架）。
# ─────────────────────────────────────────
if [ "$#" -gt 0 ]; then
    echo "=== 啟動指定服務：$* ==="
    echo "[wait] 等待資料庫遷移就緒（由 web-poa 執行）..."
    for i in $(seq 1 30); do
        if python manage.py migrate --check >/dev/null 2>&1; then
            echo "[wait] 資料庫已就緒"
            break
        fi
        if [ "$i" = "30" ]; then echo "[wait] 等待逾時，仍嘗試啟動..."; fi
        sleep 2
    done
    exec "$@"
fi

# ─────────────────────────────────────────
# [1/6] 資料庫遷移
# ─────────────────────────────────────────
echo "[1/6] 執行資料庫遷移..."
python manage.py migrate --noinput

# ─────────────────────────────────────────
# [2/6] 靜態檔案
# ─────────────────────────────────────────
echo "[2/6] 收集靜態檔案..."
python manage.py collectstatic --noinput --clear 2>/dev/null || \
python manage.py collectstatic --noinput

# ─────────────────────────────────────────
# [3/6] 資料初始化（idempotent：DB 空才匯入）
# ─────────────────────────────────────────
echo "[3/6] 檢查資料庫狀態..."
COUNT=$(python manage.py shell -c \
  "from app_user_keyword_db.models import NewsData; print(NewsData.objects.count())" \
  2>/dev/null || echo "0")

if [ "$COUNT" = "0" ]; then
    echo "  資料庫為空，開始初始化..."
    python scripts/import_uma_data.py 2>/dev/null    || echo "  [skip] import_uma_data.py 無可用資料"
    python scripts/generate_topkey_csv.py 2>/dev/null || echo "  [skip] generate_topkey_csv.py"
    python scripts/generate_top_character_csv.py 2>/dev/null || echo "  [skip] generate_top_character_csv.py"
    echo "  資料初始化完成（或無資料可匯入）"
else
    echo "  資料庫已有 ${COUNT} 筆，跳過初始化"
fi

# ─────────────────────────────────────────
# [4/6] 建立 RAG 知識庫索引（H1/M2 新增）
# ─────────────────────────────────────────
echo "[4/6] 檢查 RAG 知識庫索引..."
if [ ! -f "app_rag_uma/index/uma_knowledge.faiss" ]; then
    echo "  索引不存在，開始建立..."
    python app_rag_uma/build_index.py || echo "  [warn] RAG 索引建立失敗（跳過，不影響啟動）"
else
    echo "  RAG 索引已存在，跳過"
fi

# ─────────────────────────────────────────
# [5/6] 系統健康檢查
# ─────────────────────────────────────────
echo "[5/6] Django 系統檢查..."
python manage.py check --deploy 2>/dev/null || python manage.py check

# ─────────────────────────────────────────
# [6/6] 啟動 Gunicorn
# ─────────────────────────────────────────
echo "[6/6] 啟動 Gunicorn (workers=3, timeout=120)..."
exec gunicorn website_configs.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
