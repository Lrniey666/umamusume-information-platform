import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

try:
    from app_uma_top_keyword.views import get_category_topword
except ImportError:
    from app_top_keyword.views import get_category_topword

try:
    from app_uma_top_character.views import get_category_topPerson
except ImportError:
    from app_top_person.views import get_category_topPerson

try:
    from app_correlation_analysis.views import get_correlation_data
except (ImportError, Exception):
    get_correlation_data = None

from app_user_keyword_association.views import filter_dataFrame_fullText, get_same_para
from app_user_keyword_db.models import NewsData

from dotenv import load_dotenv
import requests


load_dotenv()


def search_and_read_web(query: str) -> str:
    """
    使用關鍵字搜尋網路資訊，並讀取最相關網頁的內容摘要。
    適合用來查詢最新的網路資訊或外部即時新聞（例如：今日新聞、最新政治動態）。
    """
    print(f"\n[Agent Tool] 執行 Tavily 安全搜尋: '{query}'")
    
    # 1. 嘗試呼叫 Tavily API
    try:
        from tavily import TavilyClient
        
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("找不到 TAVILY_API_KEY 環境變數")
            
        client = TavilyClient(api_key=api_key)
        # get_search_context 會直接回傳最適合給 LLM 閱讀的文字串
        response = client.get_search_context(query=query, max_results=3)
        
        if response:
            return response
            
    except Exception as e:
        # 當 401 錯誤或任何網路異常發生時，記錄 Log，但不中斷 Django，啟動 Fallback
        print(f"Tavily 搜尋失敗 ({str(e)})，啟動在地知識庫備援計畫。")

    # 2. 【通用防禦機制】不硬寫特定事件，而是告訴 AI 當前系統連線的真實狀況
    return (
        f"【系統通知：當前外部搜尋引擎 API 驗證受限（401 Unauthorized 或 額度用盡）。】\n"
        f"無法即時連網抓取關於「{query}」的最新網頁內容。\n"
        f"請助理（LLM）委婉向使用者說明目前無法即時連網更新資訊，"
        f"並嘗試根據你現有的知識庫提供協助，或者請使用者換個方式提問。"
    )



def read_local_document(filepath: str) -> str:
    """Read the content of a local file (e.g., .txt, .md, .csv).
    Use this tool when you need to read local document files to answer user questions.

    Args:
        filepath: 本地檔案的路徑。系統會優先從 'knowledge_base/' 目錄尋找 (例如: '公司規範.md')。
    """
    # 清理檔名：移除可能由 LLM 誤加的引號、空白或重複的目錄前綴
    clean_name = filepath.strip().strip('"').strip("'").strip("「").strip("」")
    clean_name = clean_name.replace('knowledge_base/', '').replace('knowledge_base\\', '')
    
    print(f"\n[Agent Tool] 執行 read_local_document(清理後檔名='{clean_name}')")

    # 取得專案根目錄下的 knowledge_base 資料夾
    base_dir = Path(__file__).resolve().parent.parent.parent / 'knowledge_base'
    
    # 優先從知識庫目錄尋找
    target_path = base_dir / clean_name

    if not target_path.exists():
        # 備援：嘗試從專案根目錄尋找
        root_path = Path(__file__).resolve().parent.parent.parent / clean_name
        if root_path.exists():
            target_path = root_path
        else:
            return f"錯誤：在 knowledge_base/ 找不到檔案 '{clean_name}'。目前目錄內有的檔案為: {[f.name for f in base_dir.glob('*')]}"

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 為了避免檔案過長超過 Token 限制，擷取前 4000 個字元
        if len(content) > 4000:
            return f"【檔案內容過長，僅顯示前4000字】\n{content[:4000]}..."
        return content
    except Exception as e:
        return f"讀取檔案時發生錯誤: {str(e)}"


def save_report_to_file(report_text: str, filename: Optional[str] = None) -> dict:
    """Save generated report text into a local text file.

    Args:
        report_text: The report content that should be written to disk.
        filename: Optional file name without extension. If omitted, a timestamped name is generated.
    """
    # 取得專案根目錄下的 knowledge_base 資料夾
    reports_dir = Path(__file__).resolve().parent.parent.parent / 'knowledge_base'
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 清理 report_text：如果模型在內容前後包了 markdown code block，將其去除
    if report_text.startswith("```"):
        report_text = re.sub(r'^```[\w]*\n|```$', '', report_text, flags=re.MULTILINE)

    if filename:
        safe_name = Path(filename).stem
    else:
        safe_name = datetime.now().strftime('report_%Y%m%d_%H%M%S')

    file_path = reports_dir / f"{safe_name}.txt"
    with file_path.open('w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"[Agent Tool Execution] save_report_to_file 執行完畢，已儲存至 {file_path}\n")
    return {
        "saved_path": str(file_path),
        "message": "Report saved successfully.",
    }


def get_latest_article_by_keyword(keyword: str, category: Optional[str] = None, max_chars: int = 1500) -> dict:
    """Get the latest article containing a keyword, optionally filtered by category.

    Args:
        keyword: The keyword to search in article content.
        category: Optional news category filter.
        max_chars: Max characters of content to return to the model.
    """
    print(
        "\n[Agent Tool Execution] 正在執行 get_latest_article_by_keyword(" 
        f"keyword='{keyword}', category='{category}', max_chars={max_chars})..."
    )

    queryset = NewsData.objects.filter(content__contains=keyword)
    if category:
        queryset = queryset.filter(category=category)

    article = queryset.order_by("-date").first()
    if not article:
        print("[Agent Tool Execution] get_latest_article_by_keyword 執行完畢，未找到文章。\n")
        return {"error": "No article found for the given keyword."}

    content = article.content or ""
    if max_chars and len(content) > int(max_chars):
        content = content[: int(max_chars)] + "..."

    print("[Agent Tool Execution] get_latest_article_by_keyword 執行完畢，取得 1 筆資料。\n")
    return {
        "date": article.date.isoformat(),
        "category": article.category,
        "title": article.title,
        "content": content,
        "link": article.link,
    }


def get_top_keywords(category: str, topk: int = 5) -> list:
    """Get the top keywords and their frequencies for a specific news category.

    Args:
        category: The news category (e.g., '政治', '科技', '運動').
        topk: The number of top keywords to return. Default is 5.
    """
    print(f"\n[Agent Tool Execution] 正在執行 get_top_keywords(category='{category}', topk={topk})...")
    topk = int(topk)
    _, wf_pairs = get_category_topword(category, topk)
    print(f"[Agent Tool Execution] get_top_keywords 執行完畢，取得 {len(wf_pairs)} 筆資料。\n")
    return [{'keyword': w, 'frequency': f} for w, f in wf_pairs]

def get_top_persons(category: str, topk: int = 3) -> list:
    """Get the most frequently mentioned people in a specific news category.

    Args:
        category: The news category (e.g., '政治', '科技', '運動').
        topk: The number of top people to return. Default is 3.
    """
    print(f"\n[Agent Tool Execution] 正在執行 get_top_persons(category='{category}', topk={topk})...")
    topk = int(topk)
    _, wf_pairs = get_category_topPerson(category, topk)

    print(f"[Agent Tool Execution] get_top_persons 執行完畢，取得 {len(wf_pairs)} 筆資料。\n")
    return [{'person': w, 'frequency': f} for w, f in wf_pairs]


def get_keyword_correlation(query_a: str, query_b: str, weeks: int = 12) -> dict:
    """Get the pearson correlation coefficient between two keywords over a specific number of weeks.
    This helps to understand if two keywords are trending together or opposite to each other.

    Args:
        query_a: The first keyword (e.g., '台積電').
        query_b: The second keyword (e.g., '輝達').
        weeks: The number of recent weeks to analyze. Default is 12 weeks.
    """
    print(f"\n[Agent Tool Execution] 正在執行 get_keyword_correlation(query_a='{query_a}', query_b='{query_b}', weeks={weeks})...")
    weeks = int(weeks)
    if get_correlation_data is None:
        return {"error": "相關性分析模組暫不可用（scipy 版本不相容）。"}
    res = get_correlation_data(query_a, query_b, weeks)
    if res is None:
        print("[Agent Tool Execution] get_keyword_correlation 執行完畢，資料不足無法計算。\n")
        return {"error": "No sufficient data found to calculate correlation."}
    
    pearson_coef, p_value, _, _ = res
    print(f"[Agent Tool Execution] get_keyword_correlation 執行完畢，相關係數: {pearson_coef}。\n")
    return {
        "keyword_a": query_a,
        "keyword_b": query_b,
        "pearson_correlation": pearson_coef,
        "p_value": p_value,
        "weeks_analyzed": weeks
    }

"""
Gemini (genai SDK) 會閱讀工具函數的說明（Docstring），並且這非常重要！

當你在 tools 列表中傳入 Python 函數時，SDK 會在背後使用 Python 的內建機制（反射/Introspection）來解析這個函數。它會提取以下資訊並轉換成 JSON Schema 格式發送給 Gemini：

函數名稱 (get_keyword_correlation)
函數的主說明 (例如：Get the pearson correlation coefficient between two keywords...)：這告訴 Gemini 這個工具做什麼用，以及什麼時候該呼叫它。
參數型別與預設值 (query_a: str, weeks: int = 12)。
Args 區塊的參數說明 (例如：The first keyword (e.g., '台積電'))：這指導 Gemini 在呼叫時，應該如何正確填寫這些參數。
為什麼這很重要？
Gemini 模型看不到工具內部的實作程式碼（也就是說，它看不到你的 print、get_correlation_data 這些邏輯），它完全依賴你的 Docstring 和 Type Hints 來理解這個工具。
"""