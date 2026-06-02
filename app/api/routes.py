from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AllProblem, AllContext, RunPipelineRequest, CreateContextRequest, CreateProblemRequest
from app.services.create_tables import create_problem, create_context
from app.services.email_service import run_generation
from app.core.db import get_db, FinalEmail, ReasoningState, HookTrace, TensionTrace, TransitionQuestion, AuthorityTrace, CtaTrace, StageAttempt, Problem, Context, User
from app.pipeline.orchestrator import StreamingOrchestrator
from app.repositories import get_problem_or_404, get_context_or_404, list_problems_by_user, list_contexts_by_user
from app.schemas import RuntimeContext
from app.api.auth import current_active_user
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta, timezone
import json
import asyncio

router = APIRouter()


def _extract_result(raw):
    """
    Normalize orchestrator output to a dict.
    Some orchestrators return (result_dict, trace_object) tuples.
    """
    if isinstance(raw, tuple) and len(raw) >= 1:
        return raw[0]
    return raw


# ============================================================
# AUTH ROUTES (mounted by fastapi-users in main.py)
# ============================================================
# fastapi_users provides:
#   POST /auth/register
#   POST /auth/login
#   POST /auth/logout
#   POST /auth/forgot-password
#   POST /auth/reset-password
#   POST /auth/request-verify-token
#   POST /auth/verify


# ============================================================
# PROBLEMS (protected)
# ============================================================

@router.post("/problems")
async def create_problem_api(
        req: CreateProblemRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    result = await create_problem(db, req, str(user.id))
    return {
        "problem_id": result["id"],
        "snapshot": result["snapshot"]
    }


@router.get("/problems", response_model=List[AllProblem])
async def list_problems(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    problems = await list_problems_by_user(db, str(user.id))
    return [AllProblem(**{k: getattr(c, k) for k in AllProblem.model_fields}) for c in problems]


@router.get("/problems/{problem_id}")
async def get_problem_api(
        problem_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    problem = await get_problem_or_404(db, problem_id, str(user.id))
    return {
        "id": problem.id,
        "problem_name": problem.problem_name,
        "core_problem": problem.core_problem,
        "system": problem.system,
        "causal_mechanism": problem.causal_mechanism,
        "failure_mode_A": problem.failure_mode_A,
        "failure_mode_B": problem.failure_mode_B,
        "failure_mode_A_mechanism": problem.failure_mode_A_mechanism,
        "failure_mode_B_mechanism": problem.failure_mode_B_mechanism,
        "contradiction": problem.contradiction,
        "business_impact": problem.business_impact,
        "solution_mechanism": problem.solution_mechanism,
        "solution_actor": problem.solution_actor,
        "created_at": problem.created_at,
    }


# ============================================================
# CONTEXTS (protected)
# ============================================================

@router.post("/contexts")
async def create_context_api(
        req: CreateContextRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
) -> dict:
    # Verify the problem belongs to this user
    await get_problem_or_404(db, req.problem_id, str(user.id))
    result = await create_context(db, req, str(user.id))
    return {
        "context_id": result["id"],
        "snapshot": result["snapshot"]
    }


@router.get("/contexts", response_model=List[AllContext])
async def list_contexts(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    contexts = await list_contexts_by_user(db, str(user.id))
    return [AllContext(**{k: getattr(c, k) for k in AllContext.model_fields}) for c in contexts]


@router.get("/contexts/{context_id}")
async def get_context_api(
        context_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    context = await get_context_or_404(db, context_id, str(user.id))
    return {
        "id": context.id,
        "problem_id": context.problem_id,
        "industry": context.industry,
        "company_size": context.company_size,
        "decision_actor": context.decision_actor,
        "extra": context.extra,
        "constraints": context.constraints,
        "created_at": context.created_at,
    }


# ============================================================
# PIPELINE (protected)
# ============================================================

@router.post("/run")
async def run_pipeline_api(
        req: RunPipelineRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    # Verify ownership
    await get_problem_or_404(db, req.problem_id, str(user.id))
    await get_context_or_404(db, req.context_id, str(user.id))

    raw = await run_generation(req, db, str(user.id))
    result = _extract_result(raw)
    return {
        "final_email_id": result.get("final_email_id"),
        "context_id": result.get("context_id"),
        "subject_line": result.get("subject_line"),
        "email": result.get("final_email"),
        "validation_scores": result.get("validation_scores", {}),
        "attempts": result.get("attempts", {}),
        "trace": result.get("trace", {}),
    }


@router.post("/run-stream")
async def run_pipeline_stream(
        req: RunPipelineRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    # ============================================================
    # ALL DB LOOKUPS HAPPEN HERE — BEFORE THE STREAM STARTS
    # ============================================================
    problem = await get_problem_or_404(db, req.problem_id, str(user.id))
    context = await get_context_or_404(db, req.context_id, str(user.id))

    runtime_context = RuntimeContext(
        id=str(context.id),
        problem_id=str(problem.id),
        industry=context.industry,
        company_size=context.company_size,
        decision_actor=context.decision_actor,
        extra=context.extra or "",
        constraints=context.constraints or []
    )

    problem_dict = {
        "problem_name": problem.problem_name,
        "core_problem": problem.core_problem,
        "system": problem.system,
        "causal_mechanism": problem.causal_mechanism,
        "failure_mode_A": problem.failure_mode_A,
        "failure_mode_B": problem.failure_mode_B,
        "failure_mode_A_mechanism": problem.failure_mode_A_mechanism,
        "failure_mode_B_mechanism": problem.failure_mode_B_mechanism,
        "contradiction": problem.contradiction,
        "business_impact": problem.business_impact,
        "solution_mechanism": problem.solution_mechanism,
        "solution_actor": problem.solution_actor,
    }

    # ============================================================
    # GENERATOR — ONLY YIELDING, NO EXCEPTIONS THAT BECOME HTTP RESPONSES
    # ============================================================
    async def event_stream(problem_dict, runtime_context):
        queue = asyncio.Queue()
        pipeline_done = asyncio.Event()

        def on_trace_update(trace):
            asyncio.create_task(queue.put(json.dumps({
                "type": "trace_update",
                "data": {
                    "request_id": trace.request_id,
                    "stages": [
                        {
                            "stage": s.stage,
                            "status": s.status.value,
                            "latency_ms": s.latency_ms,
                            "tokens_in": s.tokens_in,
                            "tokens_out": s.tokens_out,
                            "cost": s.cost,
                            "retry_count": s.retry_count,
                            "failure_class": s.failure_class.value if s.failure_class else None,
                            "failure_reason": s.failure_reason,
                            "validation_scores": s.validation_scores,
                            "attempts_history": s.attempts_history,
                        }
                        for s in trace.stages
                    ],
                    "total_latency_ms": trace.total_latency_ms,
                    "total_cost": trace.total_cost,
                    "total_tokens_in": trace.total_tokens_in,
                    "total_tokens_out": trace.total_tokens_out,
                    "final_status": trace.final_status,
                }
            })))

        orchestrator = StreamingOrchestrator()
        orchestrator.add_stream_callback(on_trace_update)

        async def _run_pipeline():
            try:
                return await orchestrator.run_pipeline(db, problem_dict, runtime_context)
            finally:
                pipeline_done.set()

        pipeline_task = asyncio.create_task(_run_pipeline())

        yield f"data: {json.dumps({'type': 'started', 'message': 'Pipeline initialized'})}\n\n"

        while not pipeline_done.is_set() or not queue.empty():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield f"data: {item}\n\n"
            except asyncio.TimeoutError:
                if pipeline_task.done():
                    break
                continue

        try:
            raw = await pipeline_task
            result = _extract_result(raw)
            yield f"""data: {json.dumps({ 'type': 'complete','data': {
                    'final_email_id': result.get('final_email_id'),
                    'context_id': result.get('context_id'),
                    'subject_line': result.get('subject_line'),
                    'email': result.get('final_email'),
                    'validation_scores': result.get('validation_scores', {}),
                    'attempts': result.get('attempts', {}),
                }
            })}\n\n"""
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(problem_dict, runtime_context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================
# ANALYTICS (protected — user-scoped)
# ============================================================

@router.get("/analytics")
async def get_analytics(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    user_id_str = str(user.id)

    total_stmt = select(func.count()).select_from(FinalEmail).where(
        FinalEmail.context_id.in_(
            select(Context.id).where(Context.user_id == user_id_str)
        )
    )
    total_emails = (await db.execute(total_stmt)).scalar() or 0

    if total_emails == 0:
        return {
            "average_retries": 0.0,
            "top_failure_modes": [],
            "validator_disagreement_rate": 0.0,
            "repair_success_rate": 0.0,
            "average_latency_ms": 0.0,
            "average_cost": 0.0,
            "total_emails_generated": 0,
        }

    avg_stmt = select(
        func.avg(FinalEmail.total_latency),
        func.avg(FinalEmail.total_cost),
    ).select_from(FinalEmail).where(
        FinalEmail.context_id.in_(
            select(Context.id).where(Context.user_id == user_id_str)
        )
    )
    avg_latency, avg_cost = (await db.execute(avg_stmt)).first() or (0, 0)

    failure_rows = (
        await db.execute(
            select(StageAttempt.failure_mode, func.count())
            .where(
                StageAttempt.context_id.in_(
                    select(Context.id).where(Context.user_id == user_id_str)
                ),
                StageAttempt.failure_mode.isnot(None)
            )
            .group_by(StageAttempt.failure_mode)
            .order_by(func.count().desc())
        )
    ).all()

    total_failures = sum(c for _, c in failure_rows) or 1
    top_failure_modes = [
        {"class": fc, "count": c, "percentage": round((c / total_failures) * 100)}
        for fc, c in failure_rows[:5]
    ]

    total_retries = (
        await db.execute(
            select(func.coalesce(func.sum(StageAttempt.attempt_number - 1), 0))
            .select_from(StageAttempt)
            .where(
                StageAttempt.context_id.in_(
                    select(Context.id).where(Context.user_id == user_id_str)
                )
            )
        )
    ).scalar() or 0

    total_stages = (
        await db.execute(
            select(func.count(func.distinct(StageAttempt.context_id + '-' + StageAttempt.stage_name)))
            .select_from(StageAttempt)
            .where(
                StageAttempt.context_id.in_(
                    select(Context.id).where(Context.user_id == user_id_str)
                )
            )
        )
    ).scalar() or 1

    repair_success = (
        await db.execute(
            select(func.count())
            .select_from(StageAttempt)
            .where(
                StageAttempt.context_id.in_(
                    select(Context.id).where(Context.user_id == user_id_str)
                ),
                StageAttempt.attempt_number > 1,
                StageAttempt.status == "success"
            )
        )
    ).scalar() or 0

    repair_attempts = (
        await db.execute(
            select(func.count())
            .select_from(StageAttempt)
            .where(
                StageAttempt.context_id.in_(
                    select(Context.id).where(Context.user_id == user_id_str)
                ),
                StageAttempt.attempt_number > 1
            )
        )
    ).scalar() or 1

    avg_retries = total_retries / total_stages if total_stages else 0.0
    repair_rate = repair_success / repair_attempts if repair_attempts else 0.0

    return {
        "average_retries": round(avg_retries, 1),
        "top_failure_modes": top_failure_modes,
        "validator_disagreement_rate": 0.0,
        "repair_success_rate": round(repair_rate, 2),
        "average_latency_ms": round(float(avg_latency or 0), 0),
        "average_cost": round(float(avg_cost or 0), 3),
        "total_emails_generated": total_emails,
    }


@router.get("/analytics/email/{context_id}")
async def get_email_analytics(
        context_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    """
    Per-context stage inspection.
    Returns the *latest* pipeline run for this context (most recent reasoning state).
    """
    user_id_str = str(user.id)

    # Verify context ownership
    context = await get_context_or_404(db, context_id, user_id_str)

    email_result = await db.execute(
        select(FinalEmail)
        .where(FinalEmail.context_id == context_id)
        .order_by(FinalEmail.created_at.desc())
    )
    email = email_result.scalars().first()

    if not email:
        raise HTTPException(404, "Email not found for this context")

    reasoning_state_id = email.reasoning_state_id

    rs_result = await db.execute(
        select(ReasoningState).where(ReasoningState.id == reasoning_state_id)
    )
    reasoning_state = rs_result.scalar_one_or_none()

    async def get_stage(model):
        row = (
            await db.execute(
                select(model).where(model.reasoning_state_id == reasoning_state_id)
            )
        ).scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "score": row.score,
            "scores": row.scores,
        }

    stages = {
        "reasoning_state": {
            "id": reasoning_state.id,
            "score": reasoning_state.score,
            "scores": reasoning_state.scores,
        } if reasoning_state else None,
        "hook": await get_stage(HookTrace),
        "tension": await get_stage(TensionTrace),
        "transition_question": await get_stage(TransitionQuestion),
        "authority": await get_stage(AuthorityTrace),
        "cta": await get_stage(CtaTrace),
    }

    attempts_result = await db.execute(
        select(StageAttempt)
        .where(StageAttempt.reasoning_state_id == reasoning_state_id)
        .order_by(StageAttempt.stage_name, StageAttempt.attempt_number)
    )
    attempts = attempts_result.scalars().all()

    return {
        "context_id": context_id,
        "reasoning_state_id": reasoning_state_id,
        "email_id": email.id,
        "final_email": email.final_email,
        "totals": {
            "total_latency": email.total_latency,
            "total_cost": email.total_cost,
            "total_input_tokens": email.total_input_tokens,
            "total_output_tokens": email.total_output_tokens,
            "overall_score": email.overall_score,
            "overall_scores": email.overall_scores,
        },
        "stages": {k: v for k, v in stages.items() if v is not None},
        "attempt_history": [
            {
                "stage_name": a.stage_name,
                "attempt_number": a.attempt_number,
                "status": a.status,
                "failure_reason": a.failure_reason,
                "failure_mode": a.failure_mode,
                "score": a.score,
                "scores": a.scores,
                "latency": a.latency,
                "cost": a.cost,
                "input_tokens": a.input_tokens,
                "output_tokens": a.output_tokens,
                "model_name": a.model_name,
                "output_text": a.output_text,
            }
            for a in attempts
        ],
    }


@router.get("/analytics/daily")
async def get_daily_analytics(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    user_id_str = str(user.id)

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=6)

    daily_stmt = (
        select(
            func.date(FinalEmail.created_at).label("day"),
            func.avg(FinalEmail.total_latency).label("avg_latency"),
            func.avg(FinalEmail.total_cost).label("avg_cost"),
            func.count().label("email_count"),
        )
        .where(
            FinalEmail.created_at >= start_date,
            FinalEmail.context_id.in_(
                select(Context.id).where(Context.user_id == user_id_str)
            )
        )
        .group_by(func.date(FinalEmail.created_at))
        .order_by(func.date(FinalEmail.created_at))
    )
    daily_results = (await db.execute(daily_stmt)).all()

    retry_stmt = (
        select(
            func.date(StageAttempt.created_at).label("day"),
            func.avg(StageAttempt.attempt_number - 1).label("avg_retries"),
        )
        .where(
            StageAttempt.created_at >= start_date,
            StageAttempt.context_id.in_(
                select(Context.id).where(Context.user_id == user_id_str)
            )
        )
        .group_by(func.date(StageAttempt.created_at))
    )
    retry_results = (await db.execute(retry_stmt)).all()
    retry_map = {str(r.day): float(r.avg_retries or 0) for r in retry_results}

    days = []
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    for i in range(7):
        day_date = start_date + timedelta(days=i)
        day_str = day_date.strftime('%Y-%m-%d')
        day_name = day_names[day_date.weekday()]

        day_data = next((r for r in daily_results if str(r.day) == day_str), None)

        days.append({
            "day": day_name,
            "date": day_str,
            "latency": round(float(day_data.avg_latency or 0) / 1000, 1) if day_data else 0.0,
            "cost": round(float(day_data.avg_cost or 0), 3) if day_data else 0.0,
            "retries": round(retry_map.get(day_str, 0), 1),
            "emails": int(day_data.email_count or 0) if day_data else 0,
        })

    return days