from __future__ import annotations
from app.schemas import ValidationResult
from app.pipeline.validators.general_llm_validator import llm_validate_hook
from app.core.llm_gateway import embed, cosine_similarity



async def validate_hook(hook: str, state: dict) -> ValidationResult:
    if not isinstance(hook, str):
        return ValidationResult.invalid("Hook is not a string", hook)

    if "—" in hook:
        return ValidationResult.invalid("Contains em dash", hook)

    if len(hook) < 50:
        return ValidationResult.invalid("Hook is too short (< 50 chars)", hook)

    if len(hook) > 1500:
        return ValidationResult.invalid("Hook is too long (> 1500 chars), make it concise", hook)

    is_valid, reason, metric = await llm_validate_hook(hook, state)

    if not is_valid:
        return ValidationResult.invalid(f"Hook semantic failure: {reason}", hook, metrics=metric)

    # Success with score
    return ValidationResult(True, "", hook, metrics=metric)


