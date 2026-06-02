from __future__ import annotations
import asyncio
import time
from typing import Callable, Any, Optional, Tuple, List, Awaitable, Union
from app.schemas import ValidationResult, StageTrace, StageStatus, FailureClass


# ============================================================
# FAILURE CLASSIFIER
# ============================================================

class FailureClassifier:
    @staticmethod
    def classify(reason: str) -> FailureClass:
        reason_lower = reason.lower()
        if "semantic drift" in reason_lower:
            return FailureClass.SEMANTIC_DRIFT
        elif "contradiction" in reason_lower and ("mismatch" in reason_lower or "alignment" in reason_lower):
            return FailureClass.CONTRADICTION_MISMATCH
        elif "hook" in reason_lower and "redundancy" in reason_lower:
            return FailureClass.HOOK_REDUNDANCY
        elif "explanatory" in reason_lower or "explanation" in reason_lower:
            return FailureClass.EXPLANATORY_DRIFT
        elif "mechanism" in reason_lower and ("alignment" in reason_lower or "mismatch" in reason_lower):
            return FailureClass.MECHANISM_MISMATCH
        elif "identity" in reason_lower:
            return FailureClass.IDENTITY_MISSING
        elif "sales" in reason_lower or ("cta" in reason_lower and "meeting" in reason_lower):
            return FailureClass.SALES_DRIFT
        elif "length" in reason_lower or "too long" in reason_lower or "too short" in reason_lower:
            return FailureClass.LENGTH_VIOLATION
        elif "format" in reason_lower or "json" in reason_lower:
            return FailureClass.FORMAT_ERROR
        return FailureClass.UNKNOWN


# ============================================================
# GENERATE WITH RETRY — VALIDATION-AWARE + FEEDBACK LOOP + STREAMING
# ============================================================

ValidatorFn = Callable[[Any], Union[ValidationResult, Awaitable[ValidationResult]]]
GeneratorFn = Callable[..., Union[Any, Awaitable[Any]]]
StreamCallback = Callable[[StageTrace], Union[None, Awaitable[None]]]


async def generate_with_retry(
        generator_fn: GeneratorFn,
        validator_fn: ValidatorFn,
        generator_args: Tuple = (),
        generator_kwargs: dict | None = None,
        max_retries: int = 3,
        temperature_increment: float = 0.1,
        context_id: Optional[str] = None,
        stage: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None,
) -> Tuple[Any, List[ValidationResult], StageTrace]:
    """
    Generates content with validation, retry logic, and real-time streaming.

    Returns:
        (result_data, validation_history, stage_trace)
    """

    trace = StageTrace(
        stage=stage or "unknown",
        status=StageStatus.STARTED,
    )

    if generator_kwargs is None:
        generator_kwargs = {}

    attempts = 0
    history: List[ValidationResult] = []

    previous_result: Any = None
    failure_reason: str = ""

    current_temperature = generator_kwargs.get("temperature", 0.3)

    # ========================================================
    # RETRY LOOP
    # ========================================================

    while attempts < max_retries:

        retry_kwargs = dict(generator_kwargs)
        retry_kwargs["temperature"] = current_temperature

        # feedback injection
        if previous_result is not None:
            retry_kwargs["previous_result"] = previous_result
            print(f"\n{retry_kwargs['previous_result']}\n")
            retry_kwargs["failure_reason"] = failure_reason
            print(f"\n{retry_kwargs['failure_reason']}\n")

        # ====================================================
        # GENERATION
        # ====================================================

        gen_start = time.time()

        try:
            result = generator_fn(*generator_args, **retry_kwargs)

            if asyncio.iscoroutine(result):
                result = await result

            # Extract LLM usage if returned as tuple (data, usage)
            usage = None
            if isinstance(result, tuple) and len(result) == 2:
                result_data, usage = result
            else:
                result_data = result

            gen_latency = (time.time() - gen_start) * 1000
            trace.latency_ms += gen_latency

            # Track tokens/cost from LLM usage
            if usage:
                trace.tokens_in += getattr(usage, 'tokens_in', 0)
                trace.tokens_out += getattr(usage, 'tokens_out', 0)
                trace.cost += getattr(usage, 'cost', 0.0)

            # Stream: generation attempt complete
            trace.retry_count = attempts
            if stream_callback:
                await _safe_callback(stream_callback, trace)

        except Exception as e:
            trace.status = StageStatus.FAILED
            trace.failure_reason = f"Generator crashed: {str(e)}"
            trace.failure_class = FailureClass.FORMAT_ERROR

            validation = ValidationResult.invalid(
                trace.failure_reason,
                previous_result,
                failure_class=FailureClass.FORMAT_ERROR
            )
            history.append(validation)

            if stream_callback:
                await _safe_callback(stream_callback, trace)

            attempts += 1

            if attempts < max_retries:
                trace.status = StageStatus.REPAIRING
                if stream_callback:
                    await _safe_callback(stream_callback, trace)
                await asyncio.sleep(2)

            continue

        # ====================================================
        # VALIDATION
        # ====================================================

        val_start = time.time()

        validation = validator_fn(result_data)

        if asyncio.iscoroutine(validation):
            validation = await validation

        # safety guard (in case someone returns bool)
        if isinstance(validation, bool):
            validation = (
                ValidationResult.valid()
                if validation
                else ValidationResult.invalid("Boolean validation failed", result_data)
            )

        val_latency = (time.time() - val_start) * 1000
        trace.latency_ms += val_latency

        history.append(validation)

        # Record attempt in history — failure_class is None when valid
        trace.attempts_history.append({
            "attempt": attempts + 1,
            "valid": validation.is_valid,
            "scores": validation.metrics if hasattr(validation, 'metrics') else None,
            "failure_class": validation.failure_class.value if (validation.failure_class and not validation.is_valid) else None,
            "reason": validation.reason if not validation.is_valid else None,
        })

        # Stream: validation complete
        if stream_callback:
            await _safe_callback(stream_callback, trace)

        # ====================================================
        # SUCCESS
        # ====================================================

        if validation.is_valid:
            trace.status = StageStatus.SUCCESS
            trace.output = result_data
            trace.validation_scores = validation.metrics if hasattr(validation, 'metrics') else {}
            trace.failure_reason = ""
            trace.failure_class = None

            if stream_callback:
                await _safe_callback(stream_callback, trace)

            return result_data, history, trace

        # ====================================================
        # FAILURE → PREPARE NEXT ATTEMPT
        # ====================================================

        previous_result = result_data
        failure_reason = validation.reason
        trace.failure_reason = failure_reason
        trace.failure_class = FailureClassifier.classify(failure_reason)
        trace.status = StageStatus.REPAIRING

        if stream_callback:
            await _safe_callback(stream_callback, trace)

        attempts += 1
        current_temperature = min(current_temperature + temperature_increment, 1.0)

        if attempts < max_retries:
            await asyncio.sleep(2)

    # ========================================================
    # FINAL FAILURE
    # ========================================================

    trace.status = StageStatus.FAILED
    trace.failure_reason = f"Failed after {max_retries} attempts. Last: {failure_reason}"

    if stream_callback:
        await _safe_callback(stream_callback, trace)

    raise RuntimeError(
        f"\nFailed after {max_retries} attempts.\n "
        f"\nresult: {previous_result}\n",
        f"\nLast failure: {failure_reason}.\n "
        f"\nHistory: {[v.reason for v in history]}\n"
    )


# ============================================================
# HELPER: Safe async callback execution
# ============================================================

async def _safe_callback(callback: StreamCallback, trace: StageTrace):
    """Execute callback safely, handling both sync and async callbacks."""
    try:
        result = callback(trace)
        if asyncio.iscoroutine(result):
            await result
    except Exception as e:
        print(f"[Stream callback error] {e}")