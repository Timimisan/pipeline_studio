from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import AsyncSessionLocal, Context, FinalEmail
from app.repositories import get_problem_or_404, get_context_or_404
from app.schemas import RuntimeContext
from app.pipeline.orchestrator import run_pipeline

# ============================================================
# CONFIG
# ============================================================

MAX_CONCURRENT_PIPELINES = 5


# ============================================================
# PROBLEM SERIALIZER (same as your email_service.py)
# ============================================================

def serialize_problem(problem_obj) -> Dict[str, Any]:
    return {
        "id": str(problem_obj.id),
        "problem_name": problem_obj.problem_name,
        "core_problem": problem_obj.core_problem,
        "system": problem_obj.system,
        "causal_mechanism": problem_obj.causal_mechanism,
        "failure_mode_A": problem_obj.failure_mode_A,
        "failure_mode_B": problem_obj.failure_mode_B,
        "failure_mode_A_mechanism": problem_obj.failure_mode_A_mechanism,
        "failure_mode_B_mechanism": problem_obj.failure_mode_B_mechanism,
        "contradiction": problem_obj.contradiction,
        "business_impact": problem_obj.business_impact,
        "solution_mechanism": problem_obj.solution_mechanism,
        "solution_actor": problem_obj.solution_actor,
    }


# ============================================================
# SINGLE PIPELINE RUNNER (isolated session)
# ============================================================

async def run_one_pipeline(
    context_id: str,
    problem_dict: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """
    Runs ONE context through the full pipeline with its own DB session.
    Isolated: if this crashes, it does not affect other concurrent pipelines.

    Returns:
    {
        "context_id": "...",
        "status": "done" | "failed",
        "email_id": "..." | None,
        "subject_line": "..." | None,
        "final_email": "..." | None,
        "error": None | "...",
        "latency_ms": float,
    }
    """
    start = time.time()

    async with semaphore:
        # Every pipeline gets its own session = total isolation
        async with AsyncSessionLocal() as db:
            try:
                # 1. Load context in this session
                result = await db.execute(select(Context).where(Context.id == context_id))
                ctx = result.scalar_one_or_none()
                if not ctx:
                    raise ValueError(f"Context {context_id} not found")

                # 2. Build RuntimeContext (same as email_service.py)
                runtime = RuntimeContext(
                    id=str(ctx.id),
                    problem_id=problem_dict["id"],
                    industry=ctx.industry,
                    company_size=ctx.company_size,
                    decision_actor=ctx.decision_actor,
                    extra=ctx.extra or "",
                    constraints=ctx.constraints or [],
                )

                # 3. RUN THE EXISTING PIPELINE — zero changes inside
                pipeline_result = await run_pipeline(db, problem_dict, runtime)

                latency = (time.time() - start) * 1000

                return {
                    "context_id": context_id,
                    "status": "done",
                    "email_id": pipeline_result.get("final_email_id"),
                    "subject_line": pipeline_result.get("subject_line"),
                    "final_email": pipeline_result.get("final_email"),
                    "error": None,
                    "latency_ms": latency,
                }

            except Exception as e:
                await db.rollback()
                latency = (time.time() - start) * 1000

                return {
                    "context_id": context_id,
                    "status": "failed",
                    "email_id": None,
                    "subject_line": None,
                    "final_email": None,
                    "error": str(e),
                    "latency_ms": latency,
                }


# ============================================================
# BATCH DISPATCHER
# ============================================================

async def dispatch_batch(
    problem_id: str,
    context_ids: List[str],
    max_concurrent: int = MAX_CONCURRENT_PIPELINES,
) -> List[Dict[str, Any]]:
    """
    Runs the pipeline for multiple contexts with controlled concurrency.

    - Loads problem once (read-only, safe to share)
    - Creates a semaphore to limit concurrent LLM/DB calls
    - Runs all contexts through asyncio.gather
    - Each pipeline uses its own AsyncSessionLocal session

    YES: this runs 5 pipelines simultaneously. Each is fully isolated.
    """

    # 1. Load problem once (outside concurrent zone)
    async with AsyncSessionLocal() as db:
        problem_obj = await get_problem_or_404(db, problem_id)
        problem_dict = serialize_problem(problem_obj)

    if not context_ids:
        return []

    print(f"[Dispatcher] Running {len(context_ids)} pipelines (max {max_concurrent} concurrent)")

    # 2. Semaphore controls how many run at once
    semaphore = asyncio.Semaphore(max_concurrent)

    # 3. Fire all tasks — asyncio schedules them through the semaphore
    tasks = [
        asyncio.create_task(run_one_pipeline(cid, problem_dict, semaphore))
        for cid in context_ids
    ]

    # 4. Wait for all to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 5. Normalize any stray exceptions
    normalized = []
    for r in results:
        if isinstance(r, Exception):
            normalized.append({
                "context_id": "unknown",
                "status": "failed",
                "error": str(r),
                "latency_ms": 0,
            })
        else:
            normalized.append(r)

    done = sum(1 for r in normalized if r["status"] == "done")
    failed = sum(1 for r in normalized if r["status"] == "failed")
    print(f"[Dispatcher] Complete: {done} done, {failed} failed")

    return normalized


# ============================================================
# CRM WRITEBACK (after dispatch)
# ============================================================

async def writeback_results(
    results: List[Dict[str, Any]],
    db: AsyncSession,
) -> Dict[str, int]:
    """
    For contexts that came from a CRM, push the generated email + status back.
    Reads CRM metadata from Context.extra JSON.

    Returns counts: {"sheets": N, "airtable": M, "failed": K}
    """
    from app.services.crm_writeback import push_to_google_sheets, push_to_airtable

    counts = {"sheets": 0, "airtable": 0, "failed": 0}

    for r in results:
        if r["status"] != "done" or not r["email_id"]:
            continue

        # Load context to check CRM metadata
        ctx_result = await db.execute(select(Context).where(Context.id == r["context_id"]))
        ctx = ctx_result.scalar_one_or_none()
        if not ctx or not ctx.extra:
            continue

        try:
            extra = json.loads(ctx.extra)
        except json.JSONDecodeError:
            continue

        source = extra.get("source")
        crm_meta = extra.get("crm")
        if not source or not crm_meta:
            continue

        email_text = r["final_email"] or ""

        try:
            if source == "google_sheets":
                success = await push_to_google_sheets(crm_meta, email_text, "done")
                if success:
                    counts["sheets"] += 1
                else:
                    counts["failed"] += 1

            elif source == "airtable":
                success = await push_to_airtable(crm_meta, email_text, "done")
                if success:
                    counts["airtable"] += 1
                else:
                    counts["failed"] += 1
        except Exception as e:
            print(f"[Writeback] Failed for {r['context_id']}: {e}")
            counts["failed"] += 1

    return counts