from __future__ import annotations
from app.core.llm_gateway import call_llm
from app.schemas import ValidationResult


# ============================================================
# REASONING VALIDATION HELPERS
# ============================================================


async def llm_check_anchor(
        A: str,
        B: str,
        contradiction: str,
        problem: dict
) -> tuple[bool, str, dict]:

    json_example = """{
  "valid": true/false,
  "reason": "If invalid, explain exactly which component drifted, why it drifted semantically, and what specifically must be corrected while preserving all anchored parts.",
  "score": {
      "A_anchor_alignment": 0.0-1.0,
      "B_anchor_alignment": 0.0-1.0,
      "contradiction_alignment": 0.0-1.0,
      "contextual_grounding": 0.0-1.0,
      "semantic_drift": 0.0-1.0,
      "operational_realism": 0.0-1.0
  }
}"""

    prompt = f"""
You are validating semantic anchoring and contradiction integrity.

Your task is to determine whether each reasoning component remains faithfully grounded in the original semantic truth defined in the problem object.

ORIGINAL SEMANTIC TRUTH:

Failure Mode A:
{problem['failure_mode_A']}

Failure Mode B:
{problem['failure_mode_B']}

Core Contradiction:
{problem['contradiction']}

CANDIDATE REASONING:

Contextualized_A:
{A}

Contextualized_B:
{B}

Contradiction:
{contradiction}

VALIDATION RULES:

1. A must remain semantically anchored to the original Failure Mode A.
   - It may rephrase or compress the idea
   - It may add clarification
   - But it must NOT drift into a different failure pattern
   - It must preserve the same causal meaning

2. B must remain semantically anchored to the original Failure Mode B.
   - It may rephrase or compress the idea
   - It must preserve the original operational failure mechanism
   - It must NOT introduce unrelated optimization goals or new system behaviors

3. The contradiction must remain semantically anchored to the original contradiction.
   - It must express the same underlying tension
   - It must NOT introduce external ideas or extra causal claims

4. Semantic drift is defined as:
   - introducing new causal mechanisms
   - changing the optimization pressure
   - changing the operational failure
   - replacing the original tension with a different one
   - adding abstractions not implied by the original truth

IMPORTANT:
- Do NOT reject correct sections because another section failed
- Evaluate Contextualized_A, Contextualized_B, and contradiction independently
- The reason field must identify ONLY the component that drifted
- Preserve all correct components conceptually
- Your correction guidance must behave like partial optimization:
  fix only the drifting semantic dimension without rewriting stable parts

SCORING RULES:

0.90-1.00
- fully semantically preserved
- no meaningful drift
- operationally precise

0.75-0.89
- mostly preserved
- minor abstraction or compression loss

0.50-0.74
- partially preserved
- noticeable semantic weakening
- some operational drift

0.25-0.49
- major semantic drift
- contradiction weakened
- optimization pressure changed

0.00-0.24
- semantically invalid
- different problem entirely

RETURN FORMAT:
{json_example}


EXAMPLES OF GOOD FAILURE REASONS:

- "Contextualized_A drifted from the original failure mode by introducing lead qualification issues instead of output degradation. Keep the focus on personalization decay caused by unstable generation behavior."

- "The contradiction introduces scalability concerns that are not present in the original semantic tension. Preserve the existing relationship between personalization recovery attempts and increased variance."

- "Contextualized_B changed the mechanism from prompt iteration instability to data quality problems. Keep the instability tied to repeated prompt modifications."

Be strict about semantic equivalence, not wording similarity.
"""

    result, usage = await call_llm(prompt, temperature=0.1)

    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", ""),
            result.get("score", {})
        )

    return False, "invalid LLM response", {}




async def llm_check_consequence(
        contradiction: str,
        consequence: str
) -> tuple[bool, str, dict]:

    json_example= """
    {
      "valid": true/false,
      "reason": "",
      "score": {
          "causal_integrity": 0.0-1.0,
          "decision_consequence_alignment": 0.0-1.0
      }
    }"""

    prompt = f"""
You are validating causal reasoning in a business decision context.

Contradiction:
{contradiction}

Consequence:
{consequence}

Rules:
- The consequence must occur because the contradiction is unresolved
- It must describe a decision-level failure (evaluation, choice, prioritization, trust)
- Reject vague outcomes (e.g., confusion, inefficiency)
- Reject indirect or weak links

SCORING RULES:

0.90-1.00
- consequence is causally inevitable
- strongly decision-relevant
- operationally precise

0.75-0.89
- strong causal relationship
- slight abstraction or compression loss

0.50-0.74
- partially connected
- causality weakened
- consequence somewhat indirect

0.25-0.49
- weak or inconsistent causal relationship
- consequence feels detached

0.00-0.24
- contradiction and consequence are semantically disconnected

Output JSON:
{json_example}
"""

    result, usage = await call_llm(prompt, temperature=0.1)

    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", ""),
            result.get("score", {})
        )

    return False, "invalid LLM response", {}


# ============================================================
# REASONING VALIDATOR
# ============================================================

async def validate_reasoning_state(
        state: dict,
        problem: dict
) -> ValidationResult:

    if not isinstance(state, dict):
        return ValidationResult.invalid("State must be a dictionary", state)

    required = [
        "contextualized_A",
        "contextualized_B",
        "contradiction",
        "decision_consequence"
    ]

    missing = [k for k in required if not state.get(k)]

    if missing:
        return ValidationResult.invalid(
            f"Missing fields: {missing}",
            state
        )

    # leakage check
    for key, value in state.items():
        if isinstance(value, str):
            lower = value.lower()

            if (
                "failure mode a" in lower or
                "failure mode b" in lower
            ):
                return ValidationResult.invalid(
                    f"contains system instruction leakage in {key}",
                    state
                )

    A = state["contextualized_A"]
    B = state["contextualized_B"]
    contradiction = state["contradiction"]
    consequence = state["decision_consequence"]

    # ==========================================
    # 1. Semantic anchoring validation
    # ==========================================

    (
        anchor_ok,
        anchor_reason,
        anchor_scores
    ) = await llm_check_anchor(
        A,
        B,
        contradiction,
        problem
    )

    if not anchor_ok:
        return ValidationResult.invalid(
            f"not anchored: {anchor_reason}",
            state,
            metrics=anchor_scores
        )

    # ==========================================
    # 2. Consequence validation
    # ==========================================

    (
        cons_ok,
        cons_reason,
        consequence_scores
    ) = await llm_check_consequence(
        contradiction,
        consequence
    )

    if not cons_ok:
        return ValidationResult.invalid(
            f"Consequence invalid: {cons_reason}",
            state,
            metrics=consequence_scores
        )

    # ==========================================
    # 3. Merge orthogonal telemetry
    # ==========================================

    combined_scores = {
        **anchor_scores,
        **consequence_scores
    }

    return ValidationResult(
        is_valid=True,
        reason="",
        previous_result=None,
        metrics=combined_scores
    )