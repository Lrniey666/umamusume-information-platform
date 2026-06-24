# 蝚砌??挾嚗emini Function Calling嚗ative Agentic AI嚗?
## 璁膩

?砍?獢洵銝?挾雿輻 **Google GenAI SDK嚗google-genai 2.9.0`嚗?* ?剝? Gemini 2.5 Flash 璅∪?嚗誑?? Function Calling 撖衣 Agentic AI ?拍???
---

## ?銵瑽?
```
雿輻?撓????chat_view嚗jango View嚗?    ??run_agent_native_function_calling()
        ??Gemini 2.5 Flash嚗unction Calling 璅∪?嚗?            ??撌亙?澆嚗ool Use嚗?            ???蝯?閬?    ??Session ?脣?撠店甇瑕
    ???垢憿舐內嚗arkdown 皜脫?嚗?```

---

## ?詨??辣

### `agent_core/agent.py`

- 雿輻 `google.genai.Client` 撱箇????
- 撠極?瑕?蝢拙??`config=types.GenerateContentConfig(tools=[...])`
- 撖虫?憭憚撠店嚗? `chat_history` ?喲?甇瑕嚗?- ?芸??? Function Calling 餈游?嚗?  1. Gemini ? `function_call` ???瑁?撠? Python 撌亙
  2. 撠極?瑞?????`function_response` ??璅∪?
  3. ???游璅∪?頛詨?蝯?摮?閬?
### `agent_core/tools.py`

?桀?撖虫??極?瑕撘?

| 撌亙?迂 | 隤芣? |
|---|---|
| `search_uma_announcements` | ??鞈?摨思葉?魚擐砍??砍? |
| `get_top_keywords` | ???梢??閰?銵?|
| `get_character_ranking` | ??閫鈭箸除?? |
| `get_sentiment_summary` | ???????? |
| `get_data_source_stats` | ??????皞絞閮?|
| `read_local_document` | 霈??knowledge_base/ ?抒??砍?辣 |

---

## SDK ??隤芣?

### ?撠

| 憟辣 | ??嚗歇璉嚗?| ?啁?嚗蝙?其葉嚗?|
|---|---|---|
| SDK | `google-generativeai` | `google-genai 2.9.0` |
| 璅∪? | `gemini-2.0-flash` | `gemini-3.5-flash` |
| Client | `genai.configure(api_key=...)` | `genai.Client(api_key=...)` |
| ?? | `model.generate_content(...)` | `client.models.generate_content(...)` |

### 雿輻蝭?

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="鞈賡收憡??啣?隞暻潘?",
    config=types.GenerateContentConfig(
        tools=[tool_declarations],
        system_instruction="雿鞈賡收憡?閮??,
    )
)
```

---

## 撠店瘚?

1. 雿輻?蝬脤?頛詨??
2. Django view 敺?Session ??甇瑕撠店
3. ?澆 `run_agent_native_function_calling(message, history_dict=history)`
4. Agent 餈游?嚗?   - 璅∪??斗?臬?閬極?????瑁?撌亙 ???蝯?蝯行芋??   - ???游璅∪??Ｗ?蝯?閬?5. ???脣???Session嚗?蝡臭誑 Marked.js 皜脫? Markdown
