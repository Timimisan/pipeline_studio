from __future__ import annotations
from app.schemas import ValidationResult
from app.core.llm_gateway import call_llm



async def llm_validate_cta(
        content: str,
        state: dict,
        hook: str,
        transition_question: str,
        authority_text: str,
) -> tuple[bool, str, dict]:

    """
    Validates whether the CTA:
    - remains semantically anchored to contextualized_A/B
    - naturally continues the email flow
    - preserves diagnostic tone
    - avoids sales drift
    """

    json_example = """{
  "valid": true/false,
  "reason": "specific semantic correction guidance while preserving anchored parts",
  "scores": {
    "diagnostic_alignment": 0.0,
    "tension_continuity": 0.0,
    "contextual_anchor_strength": 0.0,
    "conversational_naturalness": 0.0,
    "sales_drift": 0.0
  }
}
"""

    prompt = f"""
You are a strict semantic validation system for a structured cold email generation pipeline.

Your job is NOT to judge writing quality.

Your job is to verify whether the CTA:
- remains semantically anchored to the operational tension
- continues naturally from the previous sections
- preserves diagnostic tone
- avoids sales or persuasion drift

EMAIL FLOW CONTEXT:

HOOK:
{hook}

TRANSITION QUESTION:
{transition_question}

AUTHORITY:
{authority_text}

SEMANTIC SOURCE STATES:

CONTEXTUALIZED FAILURE MODE A:
{state["contextualized_A"]}

CONTEXTUALIZED FAILURE MODE B:
{state["contextualized_B"]}

CONTRADICTION:
{state["contradiction"]}

DECISION CONSEQUENCE:
{state["decision_consequence"]}

CTA:
{content}

VALIDATION OBJECTIVE:

The CTA must feel like:
- a natural continuation of the operational discussion
- a diagnostic recognition check
- a peer-level observation
- a low-pressure confirmation question

The CTA must NOT feel like:
- a pitch
- a meeting request
- a conversion attempt
- a generic outreach close

SEMANTIC ANCHORING RULE:

The CTA must remain primarily anchored to:
- contextualized_A
- contextualized_B

These states are the semantic source of:
- the hook
- the tension
- the authority

Every operational idea in the CTA must already exist implicitly inside those states.

If a concept cannot be traced back to contextualized_A or contextualized_B:
REJECT.

The CTA may:
- compress meaning
- paraphrase naturally
- humanize wording
- simplify language

The CTA may NOT:
- introduce new mechanisms
- introduce new business problems
- introduce implementation details
- inject external operational concerns
- change the optimization pressure
- expand the semantic scope

CORE RULES:

1. The CTA must reference the operational tension.
   - It must point toward recognizable system behavior
   - not generic outreach language

2. The CTA must contain:
   - a recognition check
   - a conditional observation
   - or a diagnostic question

3. The CTA must preserve diagnostic tone.
   Reject:
   - persuasive framing
   - sales framing
   - urgency framing
   - conversion language

4. The CTA must continue naturally from:
   - hook
   - transition question
   - authority

It should feel like:
- the final operational observation
not:
- a disconnected ask

5. The CTA must NOT contain:
   - meeting requests
   - demo language
   - scheduling language
   - "happy to chat"
   - "worth discussing"
   - "book a call"
   - "let me know"
   - "reach out"

6. The CTA must preserve tension consistency.
   Reject if:
   - the CTA shifts into different business problems
   - the CTA introduces scaling concerns
   - the CTA changes instability into targeting problems
   - the CTA introduces ROI or growth framing

SEMANTIC DRIFT RULES:

Semantic drift includes:
- changing the contradiction
- introducing unrelated optimization goals
- replacing instability with another problem
- introducing new operational mechanisms
- adding implementation concepts
- shifting from diagnostic tone into persuasion
- introducing business abstractions not present earlier

IMPORTANT FAILURE HANDLING RULE:

Do NOT ask for full rewrites.

Your failure reason must behave like partial optimization:
- identify ONLY the semantic region that drifted
- explain WHY it drifted
- explain what specifically must change
- preserve every anchored part

GOOD FAILURE REASONS:

- "The CTA introduces scaling concerns that do not exist in the contextualized states. Keep the focus on instability caused by increasing personalization pressure."

- "The first half remains anchored, but the ending shifts into sales language with an implied meeting request. Preserve the diagnostic tone."

- "The CTA becomes generic by removing the operational contrast established earlier. Re-anchor the question to the instability between specificity and predictability."

- "The CTA introduces implementation language around validators which does not exist in the contextualized states. Keep the wording operational rather than architectural."



SCORING RULES:

Score independently from 0.0-1.0:

- diagnostic_alignment:
How well the CTA preserves a system-check / diagnostic framing instead of persuasion.

- tension_continuity:
How strongly it continues the same operational instability from earlier sections.

- contextual_anchor_strength:
How tightly it stays grounded in contextualized_A/B without introducing new scope.

- conversational_naturalness:
How human and readable the CTA feels while still staying structurally constrained.

- sales_drift:
How much it shifts into persuasion, outreach, or conversion intent.
HIGH = BAD.

REJECT IF:
- diagnostic_alignment < 0.70
- tension_continuity < 0.65
- contextual_anchor_strength < 0.70
- conversational_naturalness < 0.55
- sales_drift > 0.25

OUTPUT FORMAT (STRICT JSON):
{json_example}
"""

    result, usage = await call_llm(prompt, temperature=0.1)
    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", "no reason"),
            result.get("scores", {})
        )
    return (
        False, "invalid LLM response", {}
    )



async def validate_cta(cta: str, state: dict, hook:str, transition_question:str, authority:str) -> ValidationResult:
    if not isinstance(cta, str):
        return ValidationResult.invalid("CTA is not a string", cta)

    if len(cta.split()) > 40:
        return ValidationResult.invalid("CTA too long", cta)

    is_valid, reason, metric = await llm_validate_cta(cta, state, hook, transition_question, authority)

    if not is_valid:
        return ValidationResult.invalid(f"CTA semantic failure: {reason}", cta, metrics=metric)

    # Success with score
    return ValidationResult(True, "", cta, metrics=metric)