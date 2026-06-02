from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional, Dict, Any, Tuple
import tiktoken
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
import os
import json
import math
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pricing per 1M tokens (update as needed)
PRICING = {
    "gpt-5.4-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

class LLMUsage:
    def __init__(self):
        self.tokens_in = 0
        self.tokens_out = 0
        self.latency_ms = 0.0
        self.cost = 0.0

def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = PRICING.get(model, {"input": 0.15, "output": 0.60})
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000




async def call_llm(
    prompt: str,
    temperature: float = 0.3,
    max_retries: int = 3,
    logit_bias: Optional[Dict[int, float]] = None,
    max_tokens: int = 3000,
    model: str = "gpt-5.4-mini",
    track_usage: bool = True,
) -> Tuple[dict, Optional[LLMUsage]]:

    print("calling API")

    usage = LLMUsage() if track_usage else None
    start_time = time.time()

    system_message = ChatCompletionSystemMessageParam(
        role="system",
        content=(
            "You must return ONLY valid JSON. "
            "No markdown. No explanations. "
            "All output must be valid JSON parsable by json.loads. "
            "No trailing commas. No unescaped quotes."
        ),
    )

    user_message = ChatCompletionUserMessageParam(
        role="user",
        content=prompt,
    )

    messages = [system_message, user_message]

    for attempt in range(max_retries):
        try:
            request: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            }

            if logit_bias is not None:
                request["logit_bias"] = logit_bias

            response = client.chat.completions.create(**request)
            content = response.choices[0].message.content

            if content:
                content = content.strip()

            # Track usage
            if usage and response.usage:
                usage.tokens_in = response.usage.prompt_tokens
                usage.tokens_out = response.usage.completion_tokens
                usage.latency_ms = (time.time() - start_time) * 1000
                usage.cost = calculate_cost(model, usage.tokens_in, usage.tokens_out)

            return json.loads(content), usage

        except json.JSONDecodeError as je:
            print(f"[Retry {attempt + 1}] JSON decode failed:", je)

        except Exception as e:
            print(f"[Retry {attempt + 1}] failed:", e)

    raise ValueError("LLM failed to return valid JSON after retries.")


# ============================================================
# EMBEDDING HELPERS
# ============================================================

embedding_cache = {}

async def embed(text: str):
    if text in embedding_cache:
        return embedding_cache[text]
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    vector = response.data[0].embedding
    embedding_cache[text] = vector
    return vector

async def cosine_similarity(vec_a, vec_b):
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

async def semantic_similarity(text_a: str, text_b: str) -> float:
    emb_a = await embed(text_a)
    emb_b = await embed(text_b)
    return await cosine_similarity(emb_a, emb_b)

async def overlaps(text_a, text_b, threshold=0.6):
    emb_a = await embed(text_a)
    emb_b = await embed(text_b)
    return await cosine_similarity(emb_a, emb_b) >= threshold

