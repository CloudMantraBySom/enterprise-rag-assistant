import os
from src.config import settings


def init_tracing() -> None:
    """Enable LangSmith tracing for every LLM/graph call."""
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


class UsageTracker:
    """Per-request token & cost accounting (rough GPT-4o pricing)."""
    PRICE_IN  = 0.005 / 1000   # USD per input token
    PRICE_OUT = 0.015 / 1000   # USD per output token

    def __init__(self):
        self.total_tokens = 0
        self.total_cost   = 0.0

    def record(self, prompt_tokens: int, completion_tokens: int):
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_cost   += (
            prompt_tokens  * self.PRICE_IN +
            completion_tokens * self.PRICE_OUT
        )

    def summary(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost, 6),
        }
