# core/llm_utils.py
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def llm_call(**kwargs):
    delays = [5, 15, 30, 60]
    for attempt, wait in enumerate(delays, 1):
        try:
            if "model" not in kwargs:
                kwargs["model"] = MODEL
            response = client.chat.completions.create(**kwargs)
            time.sleep(2.0) # Fast polling for paid APIs, change to 2.0 for free tiers
            return response
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"  ⏳ Rate limit hit — waiting {wait}s (attempt {attempt}/{len(delays)})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Rate limit retries exhausted")