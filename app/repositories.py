from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Row, RowMapping
from typing import List, Optional, Any, Coroutine, Sequence
from fastapi import HTTPException

from app.core.db import (
    User,
    Problem,
    Context,
    ReasoningState,
    SubjectTrace,
    HookTrace,
    TensionTrace,
    AuthorityTrace,
    CtaTrace,
    TransitionQuestion,
    FinalEmail,
    StageAttempt,
)


# ============================================================
# USER HELPERS
# ============================================================

async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# ============================================================
# BUILD PROBLEM
# ============================================================

async def build_problem(
    db: AsyncSession,
    user_id: str,
    problem_name: str,
    core_problem: str,
    system: str,
    causal_mechanism: str,
    failure_mode_A: str,
    failure_mode_B: str,
    failure_mode_A_mechanism: str,
    failure_mode_B_mechanism: str,
    contradiction: str,
    business_impact: str,
    solution_mechanism: str,
    solution_actor: str,
) -> dict:

    problem = Problem(
        user_id=user_id,
        problem_name=problem_name,
        core_problem=core_problem,
        system=system,
        causal_mechanism=causal_mechanism,
        failure_mode_A=failure_mode_A,
        failure_mode_B=failure_mode_B,
        failure_mode_A_mechanism=failure_mode_A_mechanism,
        failure_mode_B_mechanism=failure_mode_B_mechanism,
        contradiction=contradiction,
        business_impact=business_impact,
        solution_mechanism=solution_mechanism,
        solution_actor=solution_actor,
    )

    db.add(problem)
    await db.commit()
    await db.refresh(problem)

    return {
        "id": problem.id,
        "user_id": problem.user_id,
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
# BUILD CONTEXT
# ============================================================

async def build_context(
    db: AsyncSession,
    user_id: str,
    problem_id: str,
    industry: str,
    company_size: str,
    decision_actor: str,
    extra: Optional[str],
    constraints: List[str],
) -> dict:

    context = Context(
        user_id=user_id,
        problem_id=problem_id,
        industry=industry,
        company_size=company_size,
        decision_actor=decision_actor,
        extra=extra,
        constraints=constraints,
    )

    db.add(context)
    await db.commit()
    await db.refresh(context)

    return {
        "id": context.id,
        "user_id": context.user_id,
        "problem_id": context.problem_id,
        "industry": context.industry,
        "company_size": context.company_size,
        "decision_actor": context.decision_actor,
        "extra": context.extra,
        "constraints": context.constraints,
        "created_at": context.created_at,
    }


# ============================================================
# BUILD REASONING STATE
# ============================================================

async def build_reasoning_state(
    db: AsyncSession,
    context_id: str,
    failure_mode_A: Optional[str] = None,
    failure_mode_B: Optional[str] = None,
    valid: bool = False,
    selected: bool = False,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
    confidence: Optional[float] = None,
    output_json: Optional[dict] = None,
) -> dict:

    state = ReasoningState(
        context_id=context_id,
        failure_mode_A=failure_mode_A,
        failure_mode_B=failure_mode_B,
        valid=valid,
        selected=selected,
        score=score,
        scores=scores,
        confidence=confidence,
        output_json=output_json,
    )

    db.add(state)
    await db.flush()
    await db.refresh(state)

    return {
        "id": state.id,
        "context_id": state.context_id,
        "failure_mode_A": state.failure_mode_A,
        "failure_mode_B": state.failure_mode_B,
        "valid": state.valid,
        "selected": state.selected,
        "score": state.score,
        "scores": state.scores,
        "confidence": state.confidence,
        "output_json": state.output_json,
        "created_at": state.created_at,
    }


# ============================================================
# UPSERT HELPERS
# ============================================================

async def _upsert_subject_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    subject_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> SubjectTrace:
    result = await db.execute(
        select(SubjectTrace).where(SubjectTrace.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.subject_text = subject_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    subject = SubjectTrace(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        subject_text=subject_text,
        score=score,
        scores=scores,
    )
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return subject


async def _upsert_hook_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    hook_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> HookTrace:
    result = await db.execute(
        select(HookTrace).where(HookTrace.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.hook_text = hook_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    hook = HookTrace(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        hook_text=hook_text,
        score=score,
        scores=scores,
    )
    db.add(hook)
    await db.flush()
    await db.refresh(hook)
    return hook


async def _upsert_tension_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    tension_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> TensionTrace:
    result = await db.execute(
        select(TensionTrace).where(TensionTrace.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.tension_text = tension_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    tension = TensionTrace(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        tension_text=tension_text,
        score=score,
        scores=scores,
    )
    db.add(tension)
    await db.flush()
    await db.refresh(tension)
    return tension


async def _upsert_transition_question(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    question_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> TransitionQuestion:
    result = await db.execute(
        select(TransitionQuestion).where(TransitionQuestion.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.question_text = question_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    tq = TransitionQuestion(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        question_text=question_text,
        score=score,
        scores=scores,
    )
    db.add(tq)
    await db.flush()
    await db.refresh(tq)
    return tq


async def _upsert_authority_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    authority_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> AuthorityTrace:
    result = await db.execute(
        select(AuthorityTrace).where(AuthorityTrace.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.authority_text = authority_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    authority = AuthorityTrace(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        authority_text=authority_text,
        score=score,
        scores=scores,
    )
    db.add(authority)
    await db.flush()
    await db.refresh(authority)
    return authority


async def _upsert_cta_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    cta_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> CtaTrace:
    result = await db.execute(
        select(CtaTrace).where(CtaTrace.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.cta_text = cta_text
        existing.score = score
        existing.scores = scores
        await db.flush()
        await db.refresh(existing)
        return existing

    cta = CtaTrace(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        cta_text=cta_text,
        score=score,
        scores=scores,
    )
    db.add(cta)
    await db.flush()
    await db.refresh(cta)
    return cta


async def _upsert_final_email(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    final_email: str,
    total_latency: Optional[float] = None,
    total_cost: Optional[float] = None,
    total_input_tokens: Optional[int] = None,
    total_output_tokens: Optional[int] = None,
    overall_score: Optional[float] = None,
    overall_scores: Optional[dict] = None,
) -> FinalEmail:
    result = await db.execute(
        select(FinalEmail).where(FinalEmail.reasoning_state_id == reasoning_state_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.context_id = context_id
        existing.final_email = final_email
        existing.total_latency = total_latency
        existing.total_cost = total_cost
        existing.total_input_tokens = total_input_tokens
        existing.total_output_tokens = total_output_tokens
        existing.overall_score = overall_score
        existing.overall_scores = overall_scores
        await db.flush()
        await db.refresh(existing)
        return existing

    email = FinalEmail(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        final_email=final_email,
        total_latency=total_latency,
        total_cost=total_cost,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        overall_score=overall_score,
        overall_scores=overall_scores,
    )
    db.add(email)
    await db.flush()
    await db.refresh(email)
    return email


# ============================================================
# BUILD TRACE FUNCTIONS
# ============================================================

async def build_subject_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    subject_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    subject = await _upsert_subject_trace(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        subject_text=subject_text,
        score=score,
        scores=scores,
    )
    return {
        "id": subject.id,
        "context_id": subject.context_id,
        "reasoning_state_id": subject.reasoning_state_id,
        "subject_text": subject.subject_text,
        "score": subject.score,
        "scores": subject.scores,
        "created_at": subject.created_at,
    }


async def build_hook_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    hook_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    hook = await _upsert_hook_trace(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        hook_text=hook_text,
        score=score,
        scores=scores,
    )
    return {
        "id": hook.id,
        "context_id": hook.context_id,
        "reasoning_state_id": hook.reasoning_state_id,
        "hook_text": hook.hook_text,
        "score": hook.score,
        "scores": hook.scores,
        "created_at": hook.created_at,
    }


async def build_tension_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    tension_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    tension = await _upsert_tension_trace(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        tension_text=tension_text,
        score=score,
        scores=scores,
    )
    return {
        "id": tension.id,
        "context_id": tension.context_id,
        "reasoning_state_id": tension.reasoning_state_id,
        "tension_text": tension.tension_text,
        "score": tension.score,
        "scores": tension.scores,
        "created_at": tension.created_at,
    }


async def build_transition_question(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    question_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    tq = await _upsert_transition_question(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        question_text=question_text,
        score=score,
        scores=scores,
    )
    return {
        "id": tq.id,
        "context_id": tq.context_id,
        "reasoning_state_id": tq.reasoning_state_id,
        "question_text": tq.question_text,
        "score": tq.score,
        "scores": tq.scores,
        "created_at": tq.created_at,
    }


async def build_authority_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    authority_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    authority = await _upsert_authority_trace(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        authority_text=authority_text,
        score=score,
        scores=scores,
    )
    return {
        "id": authority.id,
        "context_id": authority.context_id,
        "reasoning_state_id": authority.reasoning_state_id,
        "authority_text": authority.authority_text,
        "score": authority.score,
        "scores": authority.scores,
        "created_at": authority.created_at,
    }


async def build_cta_trace(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    cta_text: str,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
) -> dict:
    cta = await _upsert_cta_trace(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        cta_text=cta_text,
        score=score,
        scores=scores,
    )
    return {
        "id": cta.id,
        "context_id": cta.context_id,
        "reasoning_state_id": cta.reasoning_state_id,
        "cta_text": cta.cta_text,
        "score": cta.score,
        "scores": cta.scores,
        "created_at": cta.created_at,
    }


async def build_final_email(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    final_email: str,
    total_latency: Optional[float] = None,
    total_cost: Optional[float] = None,
    total_input_tokens: Optional[int] = None,
    total_output_tokens: Optional[int] = None,
    overall_score: Optional[float] = None,
    overall_scores: Optional[dict] = None,
) -> dict:
    email = await _upsert_final_email(
        db=db,
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        final_email=final_email,
        total_latency=total_latency,
        total_cost=total_cost,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        overall_score=overall_score,
        overall_scores=overall_scores,
    )
    return {
        "id": email.id,
        "context_id": email.context_id,
        "reasoning_state_id": email.reasoning_state_id,
        "final_email": email.final_email,
        "total_latency": email.total_latency,
        "total_cost": email.total_cost,
        "total_input_tokens": email.total_input_tokens,
        "total_output_tokens": email.total_output_tokens,
        "overall_score": email.overall_score,
        "overall_scores": email.overall_scores,
        "created_at": email.created_at,
    }


# ============================================================
# BUILD STAGE ATTEMPT
# ============================================================

async def build_stage_attempt(
    db: AsyncSession,
    context_id: str,
    reasoning_state_id: str,
    stage_name: str,
    attempt_number: int,
    status: str,
    failure_reason: Optional[str] = None,
    failure_mode: Optional[str] = None,
    valid: Optional[bool] = None,
    selected: Optional[bool] = None,
    score: Optional[float] = None,
    scores: Optional[dict] = None,
    confidence: Optional[float] = None,
    latency: Optional[float] = None,
    cost: Optional[float] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    model_name: Optional[str] = None,
    output_text: Optional[str] = None,
) -> dict:

    attempt = StageAttempt(
        context_id=context_id,
        reasoning_state_id=reasoning_state_id,
        stage_name=stage_name,
        attempt_number=attempt_number,
        status=status,
        failure_reason=failure_reason,
        failure_mode=failure_mode,
        valid=valid,
        selected=selected,
        score=score,
        scores=scores,
        confidence=confidence,
        latency=latency,
        cost=cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_name=model_name,
        output_text=output_text,
    )

    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)

    return {
        "attempt_id": attempt.attempt_id,
        "context_id": attempt.context_id,
        "reasoning_state_id": attempt.reasoning_state_id,
        "stage_name": attempt.stage_name,
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "failure_reason": attempt.failure_reason,
        "failure_mode": attempt.failure_mode,
        "valid": attempt.valid,
        "selected": attempt.selected,
        "score": attempt.score,
        "scores": attempt.scores,
        "confidence": attempt.confidence,
        "latency": attempt.latency,
        "cost": attempt.cost,
        "input_tokens": attempt.input_tokens,
        "output_tokens": attempt.output_tokens,
        "model_name": attempt.model_name,
        "output_text": attempt.output_text,
        "created_at": attempt.created_at,
    }


# ============================================================
# FETCH HELPERS (with user_id filtering)
# ============================================================

async def get_problem(db: AsyncSession, problem_id: str, user_id: str) -> Optional[Problem]:
    result = await db.execute(
        select(Problem).where(Problem.id == problem_id, Problem.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_context(db: AsyncSession, context_id: str, user_id: str) -> Optional[Context]:
    result = await db.execute(
        select(Context).where(Context.id == context_id, Context.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_problem_or_404(db: AsyncSession, problem_id: str, user_id: str) -> Problem:
    problem = await get_problem(db, problem_id, user_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    return problem


async def get_context_or_404(db: AsyncSession, context_id: str, user_id: str) -> Context:
    context = await get_context(db, context_id, user_id)
    if not context:
        raise HTTPException(404, "Context not found")
    return context


async def list_problems_by_user(db: AsyncSession, user_id: str) -> Sequence[Row[Any] | RowMapping | Any]:
    result = await db.execute(
        select(Problem).where(Problem.user_id == user_id).order_by(Problem.created_at.desc())
    )
    return result.scalars().all()


async def list_contexts_by_user(db: AsyncSession, user_id: str) -> Sequence[Row[Any] | RowMapping | Any]:
    result = await db.execute(
        select(Context).where(Context.user_id == user_id).order_by(Context.created_at.desc())
    )
    return result.scalars().all()