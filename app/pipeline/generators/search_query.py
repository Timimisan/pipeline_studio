from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_search_queries(
    problem: dict,
    context: dict,
    temperature: float = 0.2,
    model: str = "gpt-5.4-mini",
) -> tuple[list[str], LLMUsage]:

    prompt = f"""
You generate retrieval search queries.

IMPORTANT:

The PROBLEM OBJECT is immutable truth.

Your job is NOT to:
- redefine the problem
- search for unrelated ideas
- search for solutions
- search for tooling
- search for implementation patterns

Your job is ONLY to retrieve:
- current operational manifestations
- contextual pressure
- industry-specific tension
- recent language patterns
- modern contradiction signals

The retrieval must remain semantically anchored to the problem.

PROBLEM OBJECT:
{problem}

RUNTIME CONTEXT:
{context}

QUERY RULES:

Queries must:
- stay tightly anchored to the core problem
- reflect the runtime context
- focus on operational reality
- sound like realistic search queries
- prioritize manifestation over abstraction

DO NOT:
- generate generic business searches
- generate broad AI searches
- generate implementation searches
- generate educational searches

GOOD QUERY EXAMPLES:

"AI outbound personalization fatigue in B2B SaaS"

"venture backed SaaS outbound scaling pressure"

"high volume AI outreach causing generic messaging"

"buyer skepticism toward automated outbound"

BAD QUERY EXAMPLES:

"what is AI outreach"

"how do LLMs work"

"best outreach tools"

"prompt engineering techniques"

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
  "queries": [
    "...",
    "...",
    "..."
  ]
}}
"""

    result, usage = await call_llm(
        prompt=prompt,
        temperature=temperature,
        max_tokens=300,
        model=model
    )

    queries = result.get("queries", [])

    return queries, usage