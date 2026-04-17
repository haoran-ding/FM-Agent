import re
import time
import random
from config import *
from openai import OpenAI, RateLimitError, BadRequestError

_openrouter_client = OpenAI(api_key=LLM_OPENROUTER_API_KEY, base_url=LLM_OPENROUTER_API_BASE_URL)

_MAX_RATE_LIMIT_RETRIES = 20


def _retry_create(client, model, messages):
    for attempt in range(_MAX_RATE_LIMIT_RETRIES):
        try:
            response = client.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content
        except BadRequestError:
            raise
        except RateLimitError:
            wait = min(2 ** attempt * 5, 300) + random.uniform(1, 10)
            time.sleep(wait)
    raise RuntimeError(f"Rate limited after {_MAX_RATE_LIMIT_RETRIES} retries")


def _extract_tagged(text, start_tag, end_tag):
    pattern = rf"\[{re.escape(start_tag)}\](.*?)\[{re.escape(end_tag)}\]"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def _llm_call(client, model, messages, start_tag, end_tag, max_retries=MAX_SPC_ITER):
    for _ in range(max_retries):
        response = _retry_create(client, model, messages)
        result = _extract_tagged(response, start_tag, end_tag)
        if result is not None:
            return result
        messages = messages + [
            {"role": "assistant", "content": response},
            {"role": "user", "content": f"Your output format is wrong. Please wrap your answer within [{start_tag}] and [{end_tag}]."}
        ]
    return None
