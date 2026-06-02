from app.pipeline.generators.compression import compress_retrieval_signals
from app.pipeline.generators.search_query import generate_search_queries
from app.pipeline.retry import generate_with_retry, FailureClassifier
from app.pipeline.validators.validate_reasoning import validate_reasoning_state
from app.pipeline.validators.validate_subject import validate_subject_line
from app.pipeline.validators.validate_hook import validate_hook
from app.pipeline.validators.validate_tension import validate_tension
from app.pipeline.validators.validate_authority import validate_authority
from app.pipeline.validators.validate_cta import validate_cta
from app.schemas import RuntimeContext, ValidationResult, StageTrace, StageStatus, PipelineTrace

from app.pipeline.generators.reasoning import generate_reasoning_states
from app.pipeline.generators.subject import generate_subject_line
from app.pipeline.generators.hook import generate_hook
from app.pipeline.generators.tension import generate_tension
from app.pipeline.generators.transition_question import generate_transition_question, validate_transition_question
from app.pipeline.generators.authority import generate_authority
from app.pipeline.generators.cta import generate_cta
from app.pipeline.generators.final_assembly import final_assembly_stage
from typing import Dict, Any, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import (
    build_reasoning_state,
    build_subject_trace,
    build_hook_trace,
    build_tension_trace,
    build_transition_question,
    build_authority_trace,
    build_cta_trace,
    build_final_email,
    build_stage_attempt,
)
from functools import partial
import uuid
import time
import asyncio

from app.services.search import exa_search_snippets


async def _validate_subject(result: dict, state: dict) -> ValidationResult:
    return await validate_subject_line(result["subject_line"], state)


async def _validate_hook(result: str, state: dict) -> ValidationResult:
    return await validate_hook(result, state)


async def _validate_tension(result: str, hook: str, state: dict) -> ValidationResult:
    return await validate_tension(result, hook, state)


async def _validate_transition_question(result: str, hook: str, tension: str) -> ValidationResult:
    return await validate_transition_question(result, hook, tension)


async def _validate_authority(result: str, state: dict, hook, transition_question, problem) -> ValidationResult:
    return await validate_authority(result, state, hook, transition_question, problem)


async def _validate_cta(result: str, state: dict, hook: str, transition_question: str,
                        authority: str) -> ValidationResult:
    return await validate_cta(result, state, hook, transition_question, authority)


def _extract_scores(history: list) -> list[dict]:
    scores = []
    for h in history:
        if isinstance(h.metrics, dict) and h.metrics:
            scores.append(h.metrics)
    return scores


def _get_selected_attempt(attempts_history: list) -> Optional[dict]:
    """Return the first valid attempt, or the last attempt if none are valid."""
    for attempt in attempts_history:
        if attempt.get("valid"):
            return attempt
    return attempts_history[-1] if attempts_history else None


# ============================================================
# STREAMING LAYER (separated responsibility)
# ============================================================

class PipelineStreamer:
    def __init__(self):
        self._callbacks: list[Callable[[PipelineTrace], Any]] = []

    def subscribe(self, callback: Callable[[PipelineTrace], Any]):
        self._callbacks.append(callback)

    async def emit(self, trace: "PipelineTrace"):
        tasks = []

        for cb in self._callbacks:
            try:
                result = cb(trace)

                # support async callbacks
                if asyncio.iscoroutine(result):
                    tasks.append(asyncio.create_task(result))

            except Exception as e:
                print(f"Stream callback error: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# ============================================================
# ORCHESTRATOR
# ============================================================

class StreamingOrchestrator:
    def __init__(self):
        self.trace = PipelineTrace(
            request_id=str(uuid.uuid4()),
            problem_id="",
            context_id="",
        )

        self.streamer = PipelineStreamer()

    # ----------------------------
    # streaming subscription
    # ----------------------------
    def add_stream_callback(self, callback: Callable[[PipelineTrace], None]):
        self.streamer.subscribe(callback)

    # ----------------------------
    # stage update helper
    # ----------------------------
    async def _add_stage(self, stage_trace: StageTrace):
        # FIX: only append once per stage trace object; subsequent updates
        # mutate the same object in-place, so the list reference stays live.
        if stage_trace not in self.trace.stages:
            self.trace.stages.append(stage_trace)

        # FIX: recalculate totals from the actual stage list so retries
        # never double-count latency, tokens, or cost.
        self.trace.total_latency_ms = sum(s.latency_ms for s in self.trace.stages)
        self.trace.total_cost = sum(s.cost for s in self.trace.stages)
        self.trace.total_tokens_in = sum(s.tokens_in for s in self.trace.stages)
        self.trace.total_tokens_out = sum(s.tokens_out for s in self.trace.stages)

        await self.streamer.emit(self.trace)

    # ============================================================
    # MAIN PIPELINE
    # ============================================================

    async def run_pipeline(
        self,
        db: AsyncSession,
        problem: Dict[str, Any],
        context: RuntimeContext,
        stream_callback: Optional[Callable[[PipelineTrace], None]] = None,
    ):

        if stream_callback:
            self.add_stream_callback(stream_callback)

        self.trace.problem_id = str(problem.get("id", ""))
        self.trace.context_id = str(context.id)

        results = {}

        try:
            # ============================================================
            # STEP 1: REASONING STATE
            # ============================================================
            print("\n=== RETRIEVAL LAYER (EXA + COMPRESSION) ===")

            queries, query_usage = await generate_search_queries(
                problem=problem,
                context=context
            )

            print(f"Search queries: {queries}")

            snippets = await exa_search_snippets(
                queries=queries,
                max_results=3
            )

            print(f"Retrieved snippets: {len(snippets)}")

            compressed_signals, compression_usage = await compress_retrieval_signals(
                snippets=snippets,
                problem=problem,
                context=context
            )

            print("Compressed signals generated")
            # ============================================================
            # STEP 1: REASONING STATE
            # ============================================================

            async def _validate_reasoning_state(result: dict):
                return await validate_reasoning_state(state=result, problem=problem)

            print("\n=== GENERATING REASONING STATES ===")

            async def reasoning_stream(stage_trace: StageTrace):
                stage_trace.stage = "reasoning_state"
                await self._add_stage(stage_trace)

            reasoning_state, reasoning_history, reasoning_trace = await generate_with_retry(
                generator_fn=generate_reasoning_states,
                validator_fn=partial(_validate_reasoning_state),
                generator_args=(problem, context, compressed_signals),  # 👈 ONLY CHANGE
                generator_kwargs={"temperature": 0.2},
                context_id=str(context.id),
                stage="reasoning_state",
                stream_callback=reasoning_stream,
            )

            print(f'\n contextualized_A: {reasoning_state["contextualized_A"]}\n')
            print(f'\n contextualized_B:  {reasoning_state["contextualized_B"]}\n')
            print(f'\n contradiction: {reasoning_state["contradiction"]}\n')
            print(f'\n decision_consequences: {reasoning_state["decision_consequence"]}\n')
            print(f"\nReasoning state generated after {len(reasoning_history)} attempts\n")

            selected_reasoning = _get_selected_attempt(reasoning_trace.attempts_history)

            reasoning_record = await build_reasoning_state(
                db=db,
                context_id=str(context.id),
                failure_mode_A=problem["failure_mode_A"],
                failure_mode_B=problem["failure_mode_B"],
                valid=True,
                selected=True,
                score=selected_reasoning.get("score") if selected_reasoning else None,
                scores=selected_reasoning.get("metrics") if selected_reasoning else None,
                output_json=reasoning_state,
            )

            reasoning_state_id = reasoning_record["id"]

            for attempt in reasoning_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="reasoning_state",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["reasoning_state"] = reasoning_state

            state = {
                "system_context": context.industry,
                **reasoning_state,
                "failure_mode_A": problem["failure_mode_A"],
                "failure_mode_B": problem["failure_mode_B"],
                "solution_mechanism": problem["solution_mechanism"],
                "system": problem["system"]
            }

            # ============================================================
            # STEP 2: SUBJECT LINE
            # ============================================================

            print("\n=== GENERATING SUBJECT LINE ===")

            async def subject_stream(stage_trace: StageTrace):
                stage_trace.stage = "subject_line"
                await self._add_stage(stage_trace)

            subject_result, subject_history, subject_trace = await generate_with_retry(
                generator_fn=generate_subject_line,
                validator_fn=partial(_validate_subject, state=state),
                generator_args=(state,),
                generator_kwargs={"temperature": 0.5},
                context_id=str(context.id),
                stage="subject_line",
                stream_callback=subject_stream,
            )

            selected_subject = _get_selected_attempt(subject_trace.attempts_history)

            await build_subject_trace(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                subject_text=subject_result["subject_line"],
                score=selected_subject.get("score") if selected_subject else None,
                scores=selected_subject.get("metrics") if selected_subject else None,
            )

            for attempt in subject_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="subject_line",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["subject_line"] = subject_result["subject_line"]

            # ============================================================
            # STEP 3: HOOK
            # ============================================================

            print("\n=== GENERATING HOOK ===")

            async def hook_stream(stage_trace: StageTrace):
                stage_trace.stage = "hook"
                await self._add_stage(stage_trace)

            hook, hook_history, hook_trace = await generate_with_retry(
                generator_fn=generate_hook,
                validator_fn=partial(_validate_hook, state=state),
                generator_args=(state,),
                generator_kwargs={"temperature": 0.2},
                context_id=str(context.id),
                stage="hook",
                stream_callback=hook_stream,
            )

            print(f"\nhook: {hook}\n")
            print(f"\nscore:{_extract_scores(hook_history)}\n")
            print(f"Hook generated after {len(hook_history)} attempts\n")

            selected_hook = _get_selected_attempt(hook_trace.attempts_history)

            hook_record = await build_hook_trace(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                hook_text=hook,
                score=selected_hook.get("score") if selected_hook else None,
                scores=selected_hook.get("metrics") if selected_hook else None,
            )

            for attempt in hook_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="hook",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["hook"] = hook

            # ============================================================
            # STEP 4: TENSION
            # ============================================================

            print("\n=== GENERATING TENSION ===")

            async def tension_stream(stage_trace: StageTrace):
                stage_trace.stage = "tension"
                await self._add_stage(stage_trace)

            tension, tension_history, tension_trace = await generate_with_retry(
                generator_fn=generate_tension,
                validator_fn=partial(_validate_tension, hook=hook, state=state),
                generator_args=(hook, state),
                generator_kwargs={"temperature": 0.2},
                context_id=str(context.id),
                stage="tension",
                stream_callback=tension_stream,
            )

            selected_tension = _get_selected_attempt(tension_trace.attempts_history)

            tension_record = await build_tension_trace(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                tension_text=tension,
                score=selected_tension.get("score") if selected_tension else None,
                scores=selected_tension.get("metrics") if selected_tension else None,
            )

            for attempt in tension_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="tension",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["tension"] = tension

            # ============================================================
            # STEP 4b: TRANSITION QUESTION
            # ============================================================

            print("\n=== GENERATING TRANSITION QUESTION ===")

            async def tq_stream(stage_trace: StageTrace):
                stage_trace.stage = "transition_question"
                await self._add_stage(stage_trace)

            transition_question, tq_history, tq_trace = await generate_with_retry(
                generator_fn=generate_transition_question,
                validator_fn=partial(_validate_transition_question, hook=hook, tension=tension),
                generator_args=(hook, tension),
                generator_kwargs={"temperature": 0.1},
                context_id=str(context.id),
                stage="transition_question",
                stream_callback=tq_stream,
            )

            selected_tq = _get_selected_attempt(tq_trace.attempts_history)

            tq_record = await build_transition_question(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                question_text=transition_question,
                score=selected_tq.get("score") if selected_tq else None,
                scores=selected_tq.get("metrics") if selected_tq else None,
            )

            for attempt in tq_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="transition_question",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["transition_question"] = transition_question

            # ============================================================
            # STEP 5: AUTHORITY
            # ============================================================

            print("\n=== GENERATING AUTHORITY ===")

            async def authority_stream(stage_trace: StageTrace):
                stage_trace.stage = "authority"
                await self._add_stage(stage_trace)

            authority, authority_history, authority_trace = await generate_with_retry(
                generator_fn=generate_authority,
                validator_fn=partial(
                    _validate_authority,
                    state=state,
                    hook=hook,
                    transition_question=transition_question,
                    problem=problem
                ),
                generator_args=(state, hook, transition_question, problem),
                generator_kwargs={"temperature": 0.1},
                context_id=str(context.id),
                stage="authority",
                stream_callback=authority_stream,
            )

            selected_authority = _get_selected_attempt(authority_trace.attempts_history)

            authority_record = await build_authority_trace(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                authority_text=authority,
                score=selected_authority.get("score") if selected_authority else None,
                scores=selected_authority.get("metrics") if selected_authority else None,
            )

            for attempt in authority_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="authority",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["authority"] = authority

            # ============================================================
            # STEP 6: CTA
            # ============================================================

            print("\n=== GENERATING CTA ===")

            async def cta_stream(stage_trace: StageTrace):
                stage_trace.stage = "cta"
                await self._add_stage(stage_trace)

            cta, cta_history, cta_trace = await generate_with_retry(
                generator_fn=generate_cta,
                validator_fn=partial(
                    _validate_cta,
                    state=state,
                    hook=hook,
                    transition_question=transition_question,
                    authority=authority
                ),
                generator_args=(state, hook, transition_question, authority),
                generator_kwargs={"temperature": 0.2},
                context_id=str(context.id),
                stage="cta",
                stream_callback=cta_stream,
            )

            selected_cta = _get_selected_attempt(cta_trace.attempts_history)

            cta_record = await build_cta_trace(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                cta_text=cta,
                score=selected_cta.get("score") if selected_cta else None,
                scores=selected_cta.get("metrics") if selected_cta else None,
            )

            for attempt in cta_trace.attempts_history:
                await build_stage_attempt(
                    db=db,
                    context_id=str(context.id),
                    reasoning_state_id=reasoning_state_id,
                    stage_name="cta",
                    attempt_number=attempt["attempt"],
                    status="success" if attempt["valid"] else "failed",
                    failure_reason=attempt.get("reason"),
                    failure_mode=attempt.get("failure_class"),
                    valid=attempt["valid"],
                    selected=True if attempt["valid"] else False,
                    score=attempt.get("score"),
                    scores=attempt.get("metrics"),
                    latency=attempt.get("latency_ms"),
                    cost=attempt.get("cost"),
                    input_tokens=attempt.get("tokens_in"),
                    output_tokens=attempt.get("tokens_out"),
                    model_name=attempt.get("model_name"),
                    output_text=attempt.get("output_text"),
                )

            results["cta"] = cta

            # ============================================================
            # FINAL ASSEMBLY
            # ============================================================

            print("\n=== FINAL ASSEMBLY ===")

            start = time.time()

            raw_final = await final_assembly_stage(
                hook, tension, transition_question, authority, cta
            )

            # Handle (body_string, usage) tuple return
            if isinstance(raw_final, tuple) and len(raw_final) == 2:
                final_email, _ = raw_final
            else:
                final_email = raw_final

            latency = (time.time() - start) * 1000

            assembly_trace = StageTrace(
                stage="final_assembly",
                status=StageStatus.SUCCESS,
                latency_ms=latency,
                output=final_email,
            )

            await self._add_stage(assembly_trace)

            final_email_record = await build_final_email(
                db=db,
                context_id=str(context.id),
                reasoning_state_id=reasoning_state_id,
                final_email=final_email,
                total_latency=self.trace.total_latency_ms,
                total_cost=self.trace.total_cost,
                total_input_tokens=self.trace.total_tokens_in,
                total_output_tokens=self.trace.total_tokens_out,
                overall_score=None,
                overall_scores={
                    "reasoning_state": reasoning_record.get("scores"),
                    "hook": hook_record.get("scores"),
                    "tension": tension_record.get("scores"),
                    "transition_question": tq_record.get("scores"),
                    "authority": authority_record.get("scores"),
                    "cta": cta_record.get("scores"),
                },
            )

            self.trace.final_status = "complete"
            await self.streamer.emit(self.trace)

            await db.commit()

            return {
                "final_email_id": final_email_record["id"],
                "context_id": str(context.id),
                "subject_line": results["subject_line"],
                "final_email": final_email,
                "validation_scores": {
                    "reasoning_state": _extract_scores(reasoning_history),
                    "subject_line": _extract_scores(subject_history),
                    "hook": _extract_scores(hook_history),
                    "tension": _extract_scores(tension_history),
                    "transition_question": _extract_scores(tq_history),
                    "authority": _extract_scores(authority_history),
                    "cta": _extract_scores(cta_history),
                },
                "attempts": {
                    "reasoning_state": len(reasoning_history),
                    "subject_line": len(subject_history),
                    "hook": len(hook_history),
                    "tension": len(tension_history),
                    "transition_question": len(tq_history),
                    "authority": len(authority_history),
                    "cta": len(cta_history),
                },
                "trace": self.trace,
            }

        except asyncio.CancelledError:
            self.trace.final_status = "cancelled"
            await self.streamer.emit(self.trace)
            await db.rollback()
            raise

        except Exception:
            self.trace.final_status = "failed"
            await self.streamer.emit(self.trace)
            await db.rollback()
            raise


# ============================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================

async def run_pipeline(db: AsyncSession, problem: Dict[str, Any], context: RuntimeContext):
    orchestrator = StreamingOrchestrator()
    return await orchestrator.run_pipeline(db, problem, context)