from __future__ import annotations
from app.schemas import ValidationResult
from app.pipeline.validators.general_llm_validator import llm_validate_tension

async def validate_tension(tension: str, hook:str, state: dict) -> ValidationResult:
    if not isinstance(tension, str):
        return ValidationResult.invalid("Tension is not a string", tension)

    if len(tension.split()) > 25:
        return ValidationResult.invalid("Tension too long", tension)

    if "—" in tension:
        return ValidationResult.invalid("Tension contains em dash", tension)

    # LLM semantic validation
    is_valid, reason, metric = await llm_validate_tension( tension, hook, state)

    if not is_valid:
        return ValidationResult.invalid(f"Tension semantic failure: {reason}", tension, metrics=metric)


    # Success with score
    return ValidationResult(True, "", tension, metrics=metric)