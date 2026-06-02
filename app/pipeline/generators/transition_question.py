from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage
from app.schemas import ValidationResult


async def generate_transition_question(
        hook: str,
        tension: str,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.1,
        model: str = "gpt-5.4-mini",
) -> tuple[str, LLMUsage]:

    """
    Generates a transition question that bridges:
    hook -> authority section

    The question must remain semantically anchored
    to the provided tension without introducing new ideas.
    """

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
You are generating a transition question for a structured cold email system.

The purpose of this question is to bridge:
- the hook
- into the authority/problem-resolution phase

HOOK:
{hook}

CORE TENSION:
{tension}

FEEDBACK:
{feedback_section}

OBJECTIVE:

Generate a question that naturally emerges from the tension.

The question should implicitly ask:
- how the tension gets resolved
- how both conflicting realities can coexist
- how the operational contradiction can be stabilized

The question acts as the conceptual bridge into the authority section.

IMPORTANT:
The question is NOT allowed to:
- answer the problem
- suggest a solution
- introduce new mechanisms
- add external business ideas
- inject new causal explanations
- expand the scope of the tension
- shift the optimization pressure

The question IS allowed to:
- compress meaning
- paraphrase naturally
- humanize wording
- simplify technical phrasing
- make the tension conversational

SEMANTIC ANCHORING RULE:

The generated question must remain fully anchored to the provided tension.

Everything in the question must already exist implicitly inside the tension.

If a concept cannot be traced back to the tension:
DO NOT include it.

QUESTION STYLE RULES:

- concise
- sharp
- diagnostic
- naturally conversational
- no corporate filler
- no teaching tone
- no abstract framing
- no rhetorical monologues

GOOD EXAMPLES:

Tension:
"The harder teams push for personalization through prompt iteration, the less controllable the system becomes."

Good Question:
"So how do you improve personalization without making outputs less predictable?"

Bad Question:
"So how do modern AI systems scale personalized outreach efficiently?"
(REJECT: introduces scaling + modern AI systems)

Bad Question:
"Why do LLMs struggle with personalization?"
(REJECT: explanatory and shifts into causal analysis)

Bad Question:
"How do you solve this with retrieval and validators?"
(REJECT: injects solution mechanisms)

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
  "transition_question": ""
}}
"""

    result, usage = await call_llm(
        prompt,
        temperature=temperature,
        max_tokens=300,
        model=model,
    )

    tq = result.get("transition_question", result.get("text", str(result)))
    return tq, usage



async def llm_validate_transition_question(
        question: str,
        hook: str,
        tension: str,
) -> tuple[bool, str, dict]:

    """
    Validates whether the transition question remains
    semantically anchored to the provided tension and
    properly bridges into the authority phase without drift.
    """

    json_example = '''{
      "valid": true/false,
      "reason": "specific semantic correction guidance while preserving anchored parts",
      "scores": {
        "tension_alignment": 0.0,
        "bridge_strength": 0.0,
        "unresolved_pressure": 0.0,
        "semantic_drift": 0.0,
        "explanatory_drift": 0.0
    }
    }'''

    prompt = f"""
You are a strict semantic validation system for a structured cold email generation pipeline.

Your job is NOT to judge writing quality.

Your job is to verify whether the transition question:
- remains semantically anchored to the provided tension
- acts as a natural bridge into the authority phase
- avoids introducing semantic drift

HOOK:
{hook}

CORE TENSION:
{tension}

QUESTION:
{question}

VALIDATION OBJECTIVE:

The question must emerge naturally from the tension.

It should feel like:
- the unresolved consequence of the tension
- the next logical question raised by the hook
- the conceptual bridge into the authority section

The question is allowed to:
- paraphrase naturally
- compress meaning
- humanize wording
- simplify phrasing
- make the tension conversational

The question is NOT allowed to:
- introduce new mechanisms
- introduce unrelated business concerns
- add external operational ideas
- inject solutions
- explain causality
- teach
- expand the semantic scope
- change the optimization pressure
- shift the contradiction into a different problem

SEMANTIC ANCHORING RULE:

Every semantic idea inside the question must already exist implicitly inside the tension.

If a concept cannot be traced back to the tension:
REJECT.

CORE RULES:

1. The question must remain anchored to the SAME operational tension.

2. The question must NOT answer the problem.
   - It should open a resolution path
   - not resolve it

3. The question must function as a bridge into authority.
   - It should create curiosity around resolution
   - without injecting the resolution itself

4. The question must remain diagnostic and tension-focused.
   Reject:
   - educational questions
   - explanatory questions
   - broad strategic questions
   - abstract philosophical questions

5. The question must NOT introduce:
   - scaling concerns
   - ROI concerns
   - tooling discussions
   - retrieval systems
   - validators
   - automation architecture
   unless explicitly present in the tension itself

6. The question must remain semantically aligned with the hook.
   - It should feel like a continuation
   - not a topic change

SEMANTIC DRIFT RULES:

Semantic drift includes:
- changing the core contradiction
- shifting from instability to targeting
- shifting from personalization to scaling
- adding implementation details
- injecting implied solutions
- changing observable tension into causal explanation
- introducing strategic abstractions not present in the tension

IMPORTANT FAILURE HANDLING RULE:

Do NOT ask for full rewrites.

Your failure reason must behave like partial optimization:
- identify ONLY the semantic region that drifted
- explain WHY it drifted
- explain what specifically must change
- preserve every anchored part

GOOD FAILURE REASONS:

- "The question introduces scalability concerns that are not present in the original tension. Keep the focus on instability caused by attempts to improve personalization."

- "The question shifts into causal explanation by asking why the system behaves this way. Keep the question focused on resolving the operational tension instead."

- "The first half remains anchored, but the second half introduces retrieval architecture which does not exist in the provided tension."

- "The question partially answers the problem by implying validators as the solution. Preserve the unresolved tension."

SCORING RULES:

Score independently from 0.0-1.0:

- tension_alignment:
How well the question preserves the exact operational tension.

- bridge_strength:
How naturally the question transitions into the authority phase.

- unresolved_pressure:
How strongly the question preserves unresolved tension without answering it.

- semantic_drift:
How much unrelated meaning, mechanisms, or business pressure was introduced.
HIGH = BAD.

- explanatory_drift:
How much the question shifts into explanation, teaching, or causal analysis.
HIGH = BAD.

REJECT IF:
- tension_alignment < 0.70
- bridge_strength < 0.65
- unresolved_pressure < 0.65
- semantic_drift > 0.30
- explanatory_drift > 0.35


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
    return False, "invalid LLM response", {}


async def validate_transition_question(tq: str, hook: str, tension: str) -> ValidationResult:
    is_valid, reason, metric = await llm_validate_transition_question(tq, hook, tension)

    if not is_valid:
        return ValidationResult.invalid(f"tq semantic failure: {reason}", tq, metrics=metric)

    # Success with score
    return ValidationResult(True, "", tq, metrics=metric)