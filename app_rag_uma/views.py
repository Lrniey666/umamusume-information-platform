"""
app_rag_uma/views.py

H1/M3 修復：
- 啟動時嘗試從磁碟載入持久化 FAISS 索引（knowledge_base 預建索引）
- 支援使用者上傳 PDF 疊加到現有向量庫
- 修正 model 名稱：gemini-3.1-flash-lite → gemini-3.5-flash
"""

import os
import json
import pickle
import numpy as np
import faiss
from pypdf import PdfReader
from google import genai
from google.genai import types
from django.shortcuts import render
from django.conf import settings

# ──────────────────────────────────────────────────────────────
# 路徑常數
# ──────────────────────────────────────────────────────────────
APP_DIR    = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR   = os.path.join(APP_DIR, "temp_files")
INDEX_DIR  = os.path.join(APP_DIR, "index")
INDEX_FILE = os.path.join(INDEX_DIR, "uma_knowledge.faiss")
TEXTS_FILE = os.path.join(INDEX_DIR, "uma_knowledge_texts.pkl")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# Gemini Embedding-001 維度為 3072
EMBED_DIM = 3072

# ──────────────────────────────────────────────────────────────
# 全域向量庫（啟動時嘗試從磁碟載入）
# ──────────────────────────────────────────────────────────────
_vector_db_texts: list[str] = []
_faiss_index = faiss.IndexFlatL2(EMBED_DIM)


def _try_load_persistent_index():
    """嘗試從磁碟載入預建 FAISS 索引與文本（啟動一次）"""
    global _vector_db_texts, _faiss_index
    if os.path.exists(INDEX_FILE) and os.path.exists(TEXTS_FILE):
        try:
            _faiss_index = faiss.read_index(INDEX_FILE)
            with open(TEXTS_FILE, "rb") as f:
                _vector_db_texts = pickle.load(f)
            print(f"[RAG] 已從磁碟載入索引：{_faiss_index.ntotal} 筆向量")
        except Exception as e:
            print(f"[RAG] 載入持久化索引失敗，使用空索引：{e}")
            _faiss_index = faiss.IndexFlatL2(EMBED_DIM)
            _vector_db_texts = []


# 模組載入時執行一次
_try_load_persistent_index()


# ──────────────────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────────────────
def get_genai_client():
    api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("找不到 GEMINI_API_KEY，請確認 .env 設定。")
    return genai.Client(api_key=api_key)


def _save_persistent_index():
    """將當前索引寫回磁碟"""
    try:
        faiss.write_index(_faiss_index, INDEX_FILE)
        with open(TEXTS_FILE, "wb") as f:
            pickle.dump(_vector_db_texts, f)
    except Exception as e:
        print(f"[RAG] 持久化索引儲存失敗：{e}")


# ──────────────────────────────────────────────────────────────
# Django View
# ──────────────────────────────────────────────────────────────
def rag_demo_view(request):
    context = {
        "has_vectorstore":   _faiss_index.ntotal > 0,
        "vector_count":      _faiss_index.ntotal,
        "has_persistent_index": os.path.exists(INDEX_FILE),
    }

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upload":
            pdf_file = request.FILES.get("pdf_file")
            if pdf_file:
                message = process_uploaded_pdf(pdf_file)
                context["upload_message"] = message
            else:
                context["upload_message"] = "請選擇 PDF 檔案！"

        elif action == "query":
            query_text = request.POST.get("query", "").strip()
            if query_text:
                try:
                    context["answer"] = query_rag(query_text)
                except Exception as e:
                    context["answer"] = f"⚠️ 查詢發生錯誤：{e}"
                context["query"] = query_text

        elif action == "clear":
            _vector_db_texts.clear()
            _faiss_index.reset()
            context["upload_message"] = "已清空所有向量庫資料（不含磁碟持久化索引）。"

        elif action == "reload":
            _try_load_persistent_index()
            context["upload_message"] = f"已重新載入持久化索引：{_faiss_index.ntotal} 筆向量。"

        context["has_vectorstore"] = _faiss_index.ntotal > 0
        context["vector_count"]    = _faiss_index.ntotal

    return render(request, "app_rag_uma/rag_demo.html", context)


# ──────────────────────────────────────────────────────────────
# 核心 RAG 邏輯
# ──────────────────────────────────────────────────────────────
def process_uploaded_pdf(file_obj) -> str:
    """讀取 PDF、切塊並將向量疊加到 FAISS"""
    global _vector_db_texts, _faiss_index

    file_path = os.path.join(TEMP_DIR, file_obj.name)
    try:
        with open(file_path, "wb+") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        reader   = PdfReader(file_path)
        raw_text = "\n".join(
            page.extract_text() for page in reader.pages if page.extract_text()
        )

        if not raw_text.strip():
            return "檔案中找不到任何可讀取的文字。"

        # 切塊：800 字 / 重疊 150 字
        chunk_size, overlap = 800, 150
        chunks, start = [], 0
        while start < len(raw_text):
            chunks.append(f"[來源：{file_obj.name}]\n{raw_text[start:start + chunk_size]}")
            start += chunk_size - overlap

        client   = get_genai_client()
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunks,
        )
        vectors = np.array(
            [emb.values for emb in response.embeddings], dtype=np.float32
        )
        _faiss_index.add(vectors)
        _vector_db_texts.extend(chunks)
        _save_persistent_index()

        return f"成功處理「{file_obj.name}」，切分為 {len(chunks)} 個文本塊，向量庫共 {_faiss_index.ntotal} 筆。"

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def query_rag(query_text: str) -> str:
    """向量化查詢 → FAISS 搜尋 → Gemini 生成回覆"""
    global _vector_db_texts, _faiss_index

    if _faiss_index.ntotal == 0:
        return "請先上傳 PDF 檔案或載入持久化知識庫！"

    client = get_genai_client()

    # 查詢向量化（contents 傳 list，與批次嵌入行為一致）
    query_resp   = client.models.embed_content(
        model="gemini-embedding-001",
        contents=[query_text],
    )
    query_vector = np.array([query_resp.embeddings[0].values], dtype=np.float32)

    # FAISS 搜尋前 3 名
    k = min(3, _faiss_index.ntotal)
    _, indices = _faiss_index.search(query_vector, k)

    top_chunks = [
        _vector_db_texts[idx]
        for idx in indices[0]
        if 0 <= idx < len(_vector_db_texts)
    ]

    print("[RAG] Retrieved chunks:")
    for i, c in enumerate(top_chunks, 1):
        print(f"--- chunk {i} ---\n{c[:200]}\n")

    merged_context = "\n\n---\n\n".join(top_chunks)

    system_prompt = (
        "你是「賽馬娘資訊平台」的知識庫問答助手。\n"
        "請根據以下檢索到的上下文片段來回答問題，不要編造超出上下文範圍的資訊。\n"
        "若上下文無法回答問題，請說明無法從知識庫中找到相關資訊。\n"
        "回答請使用繁體中文，並以 Markdown 格式呈現。\n\n"
        f"上下文：\n{merged_context}"
    )

    # 使用正確的 Gemini 模型名稱（gemini-3.5-flash）
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=query_text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )
    return response.text
