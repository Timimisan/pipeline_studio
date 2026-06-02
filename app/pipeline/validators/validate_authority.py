from __future__ import annotations
from app.schemas import ValidationResult
from app.pipeline.validators.general_llm_validator import llm_validate_authority


async def validate_authority(authority: str,
        state: dict,
        hook: str,
        transition_question: str,
        problem: dict) -> ValidationResult:
    if not isinstance(authority, str):
        return ValidationResult.invalid("Authority is not a string", authority)

    if "—" in authority:
        return ValidationResult.invalid("Contains em dash", authority)

    if len(authority) < 50:
        return ValidationResult.invalid("Authority is too short", authority)

    is_valid, reason, metric = await llm_validate_authority(authority, state, hook, transition_question, problem)

    if not is_valid:
        return ValidationResult.invalid(f"Authority semantic failure: {reason}", authority, metrics=metric)

    # Success with score
    return ValidationResult(True, "", authority, metrics=metric)