"""The one model every agent uses (gpt-6-luna through Portkey) and token-to-cost math."""

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

import config


def make_model() -> OpenAIResponsesModel:
    """gpt-6-luna routed through Portkey, using PORTKEY_API_KEY from .env. No fallbacks."""
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY not found. Put it in a .env file in the repo folder or the folder one level above."
        )
    client = AsyncOpenAI(
        api_key=key,
        base_url=config.PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
        timeout=60,      # seconds per model request
        max_retries=0,   # retries are done (once) by the broker, so every attempt is logged in the audit trail
    )
    return OpenAIResponsesModel(config.MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def usage_breakdown(usage: RunUsage) -> dict:
    """Input (uncached), cached input, cache-write and output tokens, plus cost in USD.

    input_tokens from the model includes the cached and cache-write tokens, so they are
    subtracted out and each slice is priced at its own rate.
    """
    cached = usage.cache_read_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    uncached = max((usage.input_tokens or 0) - cached - cache_write, 0)
    output = usage.output_tokens or 0
    cost = (uncached * config.PRICE_INPUT_PER_M
            + cached * config.PRICE_CACHED_INPUT_PER_M
            + cache_write * config.PRICE_CACHE_WRITE_PER_M
            + output * config.PRICE_OUTPUT_PER_M) / 1_000_000
    return {
        "requests": usage.requests,
        "input_tokens": uncached,
        "cached_tokens": cached,
        "cache_write_tokens": cache_write,
        "output_tokens": output,
        "total_tokens": uncached + cached + cache_write + output,
        "cost_usd": round(cost, 8),
    }
