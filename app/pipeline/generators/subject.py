from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage

async def generate_subject_line(
        state: dict,
        previous_result: Optional[dict] = None,
        failure_reason: str = "",
        temperature: float = 0.6,
        model = "gpt_4.5_mini"
) -> tuple[dict, LLMUsage]:
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

    prompt = f"""
You are generating a SUBJECT LINE for a cold email system.

You are given:

Failure Mode A:
{state["failure_mode_A"]}

Failure Mode B:
{state["failure_mode_B"]}

Contradiction:
{state["contradiction"]}

Decision Consequence:
{state["decision_consequence"]}

{feedback_section}

TASK:
Write a subject line that HINTS at the contradiction by expressing ONE side of the failure as a visible pain.

RULES:

1. CORE LOGIC
- Must express a real negative outcome from either Failure Mode A OR B
- Must imply the existence of the opposite failure mode (without stating it)
- Must NOT explain both sides
- Must NOT resolve the contradiction

2. PAIN STYLE
- Must be concrete and observable (not abstract)
- Must feel like something happening in reality
- Must create “this might be true for us” recognition

3. CONTRADICTION HINTING
- Only show ONE side
- The missing side should be implied, not stated

4. STYLE RULES
- Max 10–12 words
- No marketing language
- No vague words: "issue", "problem", "solution", "optimize", "improve"
- No questions
- No em dashes

OUTPUT FORMAT (JSON ONLY):
{{
  "subject_line": ""
}}
"""

    result, usage = await call_llm(prompt, temperature=temperature)
    return result, usage