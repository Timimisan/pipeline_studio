from __future__ import annotations
from app.core.llm_gateway import call_llm
from app.schemas import ValidationResult


async def llm_validate_subject(subject: str, state: dict) -> tuple[bool, str, dict]:
    json_example = '''{
      "valid": true/false,
      "reason": "",
      "scores": {
        "contradiction_hinting": 0.0,
        "concreteness": 0.0,
        "pain_realism": 0.0,
        "curiosity_pressure": 0.0,
        "semantic_drift": 0.0
      }
    }'''
    prompt = f"""
You are validating a cold email SUBJECT LINE.

STATE:
- Failure Mode A: {state["failure_mode_A"]}
- Failure Mode B: {state["failure_mode_B"]}
- Contradiction: {state["contradiction"]}
- Decision Consequence: {state["decision_consequence"]}

SUBJECT:
{subject}

VALIDATION RULES:

1. CONTRADICTION HINTING
- Does it express ONE failure mode as a real-world pain?
- Does it implicitly suggest the other failure mode exists?

2. SPECIFICITY
- Is it concrete and observable?
- Or is it generic business language?

3. PAIN QUALITY
- Does it feel like a real operational symptom?
- Or marketing abstraction?

4. DRIFT CHECK
- Reject if it fully explains the system
- Reject if it becomes generic SaaS messaging

5. OPENABILITY TEST
- Would a reader think: "this might be happening in my system"?


SCORING RULES:

Score independently from 0.0-1.0:

- contradiction_hinting:
How well the subject line implicitly reflects one side of the contradiction while hinting at the other.

- concreteness:
How observable and specific the subject line is (non-generic, non-abstraction).

- pain_realism:
How strongly it reflects a real operational symptom rather than marketing language.

- curiosity_pressure:
How likely it creates unresolved tension that encourages opening (without being clickbait).

- semantic_drift:
How much unrelated meaning or framing was introduced.
HIGH = BAD.

REJECT IF:
- contradiction_hinting < 0.65
- concreteness < 0.70
- pain_realism < 0.65
- curiosity_pressure < 0.60
- semantic_drift > 0.30

OUTPUT JSON:
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
        False,
        "invalid LLM response",
        {}
    )




async def validate_subject_line(subject: str, state: dict) -> ValidationResult:
    if not isinstance(subject, str):
        return ValidationResult.invalid("Subject is not a string", subject, metrics=0.0)

    words = subject.split()

    if len(words) > 12:
        return ValidationResult.invalid("Too long (>12 words)", subject, metrics=0.0)
    if len(words) < 3:
        return ValidationResult.invalid("Too short", subject, metrics=0.0)

    banned = ["improve", "optimize", "boost", "solution", "increase", "scale", "growth", "fix", "issue", "problem"]
    lowered = subject.lower()
    for b in banned:
        if b in lowered:
            return ValidationResult.invalid(f"Contains banned word: {b}", subject, metrics=0.0)

    if "?" in subject:
        return ValidationResult.invalid("Contains question", subject, metrics=0.0)
    if "—" in subject:
        return ValidationResult.invalid("Contains em dash", subject, metrics=0.0)

    # LLM semantic validation
    is_valid, reason, score = await llm_validate_subject(subject, state)

    if not is_valid:
        return ValidationResult.invalid(f"Semantic failure: {reason}", subject, metrics=score)

    # Success with score
    return ValidationResult(True, "", subject, metrics=score)

