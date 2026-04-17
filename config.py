import os

LLM_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_OPENROUTER_API_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = "anthropic/claude-sonnet-4.6"

MAX_SPC_ITER = 5
GRANULARITY = 40
MAX_WORKERS = 10
OPENCODE_MAX_RETRIES = 5
