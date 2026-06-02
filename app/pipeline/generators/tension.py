from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_tension(
        hook: str,
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.3,
        model="gpt-5.4-mini"
) -> tuple[str, LLMUsage]:

    # -------------------------
    # 3. Feedback section
    # -------------------------
    feedback_section = ""

    if previous_result is not None and failure_reason:
        feedback_section = f"""
    PREVIOUS QUESTION ATTEMPT (FAILED):
    {previous_result}

    FAILURE REASON:
    {failure_reason}

    INSTRUCTIONS FOR THIS RETRY:
    - Fix ONLY the semantic issue identified above
    - Preserve all anchored meaning
    - Do NOT rewrite correct sections
    - Do NOT introduce new operational ideas
    """

    # -------------------------
    # 4. Prompt (slightly improved wording)
    # -------------------------
    prompt = f"""
You are writing the TENSION line of an email.

HOOK:
{hook}

CONTRADICTION:
{state["contradiction"]}

{feedback_section}

TASK:
Write ONE sentence that expresses what must logically follow from the hook given the contradiction.

RULES:
- Do NOT repeat or paraphrase the hook
- Do NOT describe the situation
- Do NOT explain
- Conclude something new that becomes unavoidable
- Compress the implication into a single insight
- Max 25 words
- Direct and precise
- No fluff, no storytelling
- MUST Feels inevitable once read
- MUST Introduces a sharper truth
- MUST NOT Sounds like explanation
- MUST NOT Sounds like summary
- MUST NOT Restates known information
- MUST ONLY USE CONTRADICTION
- MUST be anchored to contradiction 
- MUST NOT BE  inferrable directly from the hook alone
- Do NOT use em dashes (—)
- Do NOT use en dashes (–)
- Use only commas and full stops for separation

OUTPUT JSON:
{{
  "tension_text": ""
}}
"""

    result, usage = await call_llm(
        prompt=prompt,
        temperature=temperature,
        max_tokens=300,
        model=model,
    )

    tension_text = result.get("tension_text", result.get("text", str(result)))
    return tension_text, usage