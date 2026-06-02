from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_cta(
        state: dict,
        hook: str,
        transition_question: str,
        authority_text: str,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.2,
        model="gpt-5.4-mini"
) -> tuple[str, LLMUsage]:

    # -------------------------
    # Feedback section
    # -------------------------
    feedback_section = ""

    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS CTA ATTEMPT (FAILED):
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
    # Prompt
    # -------------------------
    prompt = f"""
You are writing the CTA for a structured analytical cold email.

The email progression already established:
- a real operational tension
- the consequence of instability
- a structural way to stabilize the system

The CTA must now act as:
- a soft diagnostic check
- a low-friction confirmation question
- a natural continuation of the hook -> tension -> authority flow

CONTEXT:

SYSTEM CONTEXT:
{state["system_context"]}

CONTEXTUALIZED FAILURE MODE A:
{state["contextualized_A"]}

CONTEXTUALIZED FAILURE MODE B:
{state["contextualized_B"]}

DECISION CONSEQUENCE:
{state["decision_consequence"]}

HOOK:
{hook}

TRANSITION QUESTION:
{transition_question}

AUTHORITY:
{authority_text}

FEEDBACK:
{feedback_section}

OBJECTIVE:

Write a CTA that checks whether the reader is experiencing the same operational behavior.

The CTA should feel like:
- a practitioner validating a recognizable system pattern
not:
- a salesperson pushing for a meeting

SEMANTIC ANCHORING RULE:

The CTA must remain primarily anchored to:
- contextualized_A
- contextualized_B

These are the semantic source of:
- the hook
- the tension
- the authority

The CTA may compress or paraphrase these states naturally,
but MUST preserve the same operational reality.

DO NOT:
- introduce new business problems
- introduce new mechanisms
- introduce new outcomes
- inject tooling concepts
- introduce unrelated operational pressures
- add explanatory analysis

If a concept cannot be traced back to contextualized_A or contextualized_B:
DO NOT include it.

CTA FUNCTION RULE:

The CTA is NOT:
- a meeting request
- a pitch
- a conversion ask
- a demo request

The CTA IS:
- a diagnostic recognition check
- a peer-level observation
- a soft confirmation question

STRUCTURE RULE:

The CTA should naturally contain:

1. recognizable system behavior
2. operational contrast or instability
3. conditional recognition
4. low-pressure invitation to respond

STYLE RULES:

- calm
- compressed
- observational
- peer-level
- operational
- non-salesy

LANGUAGE RULES:

- MUST reference the reader's system behavior directly
- MUST preserve operational wording from earlier sections
- MUST remain grounded in instability/tension language
- MUST be phrased as a question or conditional recognition check
- MUST avoid corporate CTA language
- MUST avoid persuasion framing
- MUST avoid scheduling language
- MUST avoid hype language

FORBIDDEN:
- "book a call"
- "happy to chat"
- "open to a demo"
- "worth discussing"
- "can help"
- "reach out"
- "scale faster"
- "improve ROI"

GOOD DIRECTION:

"Are you seeing the same pattern where adding more personalization control makes output quality less predictable over time?"

"If the system keeps getting harder to stabilize every time prompts become more specific, is that happening on your side too?"

BAD DIRECTION:

"Would you be open to a quick call to discuss this?"
(REJECT: sales CTA)

"Are you looking to scale outbound performance?"
(REJECT: introduces scaling)

"Would retrieval augmentation help solve this?"
(REJECT: injects mechanism)

MAX LENGTH:
25 words

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
  "cta_text": ""
}}
"""

    result, usage = await call_llm(
        prompt=prompt,
        temperature=temperature,
        max_tokens=80,
        model=model,
    )

    cta_text = result.get("cta_text", result.get("text", str(result)))
    return cta_text, usage