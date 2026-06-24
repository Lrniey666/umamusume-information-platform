import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
MODEL_NAME = 'gemini-3.5-flash'

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('API_KEY')
if not api_key:
    raise ValueError('找不到 GEMINI_API_KEY，請在 .env 檔案中設定。')

client = OpenAI(
    base_url=GEMINI_BASE_URL,
    api_key=api_key,
)
