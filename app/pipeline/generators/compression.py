from typing import List, Tuple, Dict
from app.core.llm_gateway import call_llm, LLMUsage


async def compress_retrieval_signals(
    snippets: List[str],
    problem: dict,
    context: dict,
    temperature: float = 0.2,
    model: str = "gpt-5.4-mini",
) -> Tuple[Dict, LLMUsage]:

    prompt = f"""
You are a retrieval compression engine.

Your job is NOT to reason.

Your job is ONLY to extract structured signals from retrieved text.

You are given:

PROBLEM (immutable truth):
{problem}

CONTEXT:
{context}

RETRIEVED SNIPPETS:
{snippets}

TASK:

Convert these snippets into structured signals.

RULES:

1. Do NOT modify the problem
2. Do NOT infer solutions
3. Do NOT add new ideas
4. Only extract observable signals from text

SIGNAL TYPES:

- pressure_signals:
  operational stress, scaling pressure, quality degradation pressure

- contradiction_signals:
  tension between intent vs outcome, automation vs quality, etc.

- market_signals:
  industry trends, adoption behavior, external shifts

- language_signals:
  how people describe the problem in real-world terms

OUTPUT FORMAT:

Return ONLY JSON:

{{
  "pressure_signals": [],
  "contradiction_signals": [],
  "market_signals": [],
  "language_signals": []
}}
"""

    result, usage = await call_llm(
        prompt=prompt,
        temperature=temperature,
        max_tokens=600,
        model=model
    )

    return result, usage