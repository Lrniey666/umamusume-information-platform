"""
app_rag_uma/build_index.py

H1 任務：預建 FAISS 向量索引
從 knowledge_base/ 目錄讀取所有 .md/.txt 文件，
向量化後存到 app_rag_uma/index/uma_knowledge.faiss

執行方式：
    python app_rag_uma/build_index.py
    （在 Docker entrypoint.sh 中自動呼叫）
"""

import os
import sys
import pickle
import numpy as np

# 確保在 Django 環境中執行時，可正確找到 google.genai
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, ".env"), override=True)

import faiss
from google import genai

# ──────────────────────────────────────────────────────────────
# 路徑設定
# ──────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_DIR, "knowledge_base")
INDEX_DIR   = os.path.join(CURRENT_DIR, "index")
INDEX_FILE  = os.path.join(INDEX_DIR, "uma_knowledge.faiss")
TEXTS_FILE  = os.path.join(INDEX_DIR, "uma_knowledge_texts.pkl")
EMBED_DIM   = 3072
CHUNK_SIZE  = 800
OVERLAP     = 150

os.makedirs(INDEX_DIR, exist_ok=True)


def read_knowledge_files() -> list[tuple[str, str]]:
    """讀取 knowledge_base/ 內所有 .md / .txt 文件，回傳 (filename, content) 列表"""
    results = []
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"[build_index] knowledge_base 目錄不存在：{KNOWLEDGE_BASE_DIR}")
        return results

    for fname in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
        if not fname.endswith((".md", ".txt")):
            continue
        fpath = os.path.join(KNOWLEDGE_BASE_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            results.append((fname, content))
            print(f"[build_index] 讀取：{fname}  ({len(content)} 字)")
        except Exception as e:
            print(f"[build_index] 讀取失敗：{fname}  {e}")
    return results


def chunk_text(filename: str, text: str) -> list[str]:
    """切塊，每塊附上來源標記"""
    chunks = []
    start  = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = f"[來源：{filename}]\n{text[start:end]}"
        chunks.append(chunk)
        start += CHUNK_SIZE - OVERLAP
    return chunks


def build_faiss_index(chunks: list[str]) -> tuple[faiss.IndexFlatL2, list[str]]:
    """呼叫 Gemini Embedding API 向量化，建立 FAISS 索引"""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未設定，無法建立 Embedding 向量。")

    client = genai.Client(api_key=api_key)

    # 分批送出（避免單次太多 chunks）
    batch_size = 20
    all_vectors = []

    for i in range(0, len(chunks), batch_size):
        batch  = chunks[i: i + batch_size]
        resp   = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
        )
        vectors = [emb.values for emb in resp.embeddings]
        all_vectors.extend(vectors)
        print(f"[build_index] Embedding {i + len(batch)}/{len(chunks)} 完成")

    vectors_np = np.array(all_vectors, dtype=np.float32)
    index      = faiss.IndexFlatL2(EMBED_DIM)
    index.add(vectors_np)
    return index, chunks


def main():
    print("=" * 50)
    print("[build_index] 開始建立 RAG 知識庫索引")
    print("=" * 50)

    files = read_knowledge_files()
    if not files:
        print("[build_index] 無任何文件，中止。")
        return

    all_chunks = []
    for fname, content in files:
        chunks = chunk_text(fname, content)
        all_chunks.extend(chunks)
        print(f"[build_index] {fname} 切分為 {len(chunks)} 個 chunk")

    print(f"\n[build_index] 共 {len(all_chunks)} 個 chunk，開始向量化…")
    index, texts = build_faiss_index(all_chunks)

    faiss.write_index(index, INDEX_FILE)
    with open(TEXTS_FILE, "wb") as f:
        pickle.dump(texts, f)

    print(f"\n[build_index] 索引已儲存：")
    print(f"  FAISS：{INDEX_FILE}  ({index.ntotal} 筆向量)")
    print(f"  Texts：{TEXTS_FILE}")
    print("[build_index] 完成！")


if __name__ == "__main__":
    main()
