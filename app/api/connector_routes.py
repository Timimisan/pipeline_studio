from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
import json

from app.core.db import get_db, Context, FinalEmail
from app.repositories import get_problem_or_404
from app.services.connector_service import (
    parse_csv_bytes,
    create_contexts_from_csv,
    fetch_google_sheet_rows,
    fetch_airtable_rows,
    create_contexts_from_crm,
)
from app.services.dispatcher import dispatch_batch, writeback_results
from pydantic import BaseModel

router = APIRouter()


# ============================================================
# SCHEMAS
# ============================================================

class ImportResponse(BaseModel):
    problem_id: str
    source: str
    total_imported: int
    context_ids: List[str]
    message: str

class ProcessRequest(BaseModel):
    problem_id: str
    context_ids: List[str]
    max_concurrent: int = 5
    writeback: bool = True

class ProcessResponse(BaseModel):
    problem_id: str
    total: int
    done: int
    failed: int
    results: List[Dict[str, Any]]
    writeback_summary: Optional[Dict[str, int]] = None

class ResultItem(BaseModel):
    context_id: str
    status: str
    industry: str
    company_size: str
    decision_actor: str
    subject_line: Optional[str]
    final_email: Optional[str]
    error: Optional[str]
    created_at: Optional[str]


# ============================================================
# 1. CSV UPLOAD → CREATE CONTEXTS (per-row constraints)
# ============================================================

@router.post("/import/csv", response_model=ImportResponse)
async def import_csv(
    problem_id: str = Form(...),
    column_mapping: str = Form(..., description='{"industry":"Sector","company_size":"Size","decision_actor":"Role","constraints":"Tags"}'),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file. Each row becomes a normal Context record.
    Constraints are read per-row from the CSV column mapped by column_mapping["constraints"].

    Example column_mapping:
    {
        "industry": "Sector",
        "company_size": "Employees",
        "decision_actor": "Role",
        "extra": "Notes",
        "constraints": "Tags"
    }

    If constraints maps to a column with comma-separated values like "b2b,saas,enterprise",
    each row gets its own constraint list.
    """
    await get_problem_or_404(db, problem_id)

    try:
        mapping: Dict[str, str] = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(400, "column_mapping must be valid JSON")

    file_bytes = await file.read()
    rows = parse_csv_bytes(file_bytes)
    if not rows:
        raise HTTPException(400, "CSV is empty or has no data rows")

    # Validate headers
    headers = list(rows[0].keys())
    required = [mapping.get(k, k) for k in ["industry", "company_size", "decision_actor"]]
    missing = [c for c in required if c not in headers]
    if missing:
        raise HTTPException(400, f"CSV missing required columns: {missing}. Found: {headers}")

    # Create contexts using existing build_context — per-row constraints
    created = await create_contexts_from_csv(db, problem_id, rows, mapping)
    await db.commit()

    context_ids = [c["id"] for c in created]

    return ImportResponse(
        problem_id=problem_id,
        source="csv",
        total_imported=len(created),
        context_ids=context_ids,
        message=f"{len(created)} contexts created. POST /process to generate emails.",
    )


# ============================================================
# 2. CRM IMPORT → CREATE CONTEXTS (per-row constraints)
# ============================================================

@router.post("/import/crm", response_model=ImportResponse)
async def import_crm(
    problem_id: str = Form(...),
    source: str = Form(..., description="google_sheets or airtable"),
    crm_config: str = Form(..., description="JSON config for the CRM connection"),
    column_mapping: str = Form(..., description='{"industry":"Sector","company_size":"Size","decision_actor":"Role","constraints":"Tags"}'),
    db: AsyncSession = Depends(get_db),
):
    """
    Pull leads from Google Sheets or Airtable and create Context records.
    Each row has its own constraints from the mapped column.
    CRM metadata is stashed in Context.extra for writeback later.
    """
    await get_problem_or_404(db, problem_id)

    if source not in ("google_sheets", "airtable"):
        raise HTTPException(400, "source must be 'google_sheets' or 'airtable'")

    try:
        mapping = json.loads(column_mapping)
        config = json.loads(crm_config)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON in form fields")

    # Fetch rows from CRM
    if source == "google_sheets":
        rows = await fetch_google_sheet_rows(config)
    elif source == "airtable":
        rows = await fetch_airtable_rows(config)
    else:
        rows = []

    if not rows:
        raise HTTPException(400, "No rows found in CRM")

    # Create contexts with per-row constraints
    created = await create_contexts_from_crm(
        db=db,
        problem_id=problem_id,
        rows=rows,
        mapping=mapping,
        source=source,
        crm_config=config,
    )
    await db.commit()

    context_ids = [c["id"] for c in created]

    return ImportResponse(
        problem_id=problem_id,
        source=source,
        total_imported=len(created),
        context_ids=context_ids,
        message=f"{len(created)} contexts created from {source}. POST /process to generate emails.",
    )


# ============================================================
# 3. PROCESS BATCH (the dispatcher)
# ============================================================

@router.post("/process", response_model=ProcessResponse)
async def process_batch(
    req: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Fire the pipeline for the given context_ids with controlled concurrency.
    Runs up to 5 pipelines simultaneously. Each uses its own DB session.

    If writeback=True and contexts came from a CRM, pushes results back.
    """
    await get_problem_or_404(db, req.problem_id)

    if not req.context_ids:
        raise HTTPException(400, "No context_ids provided")

    # Verify all context_ids exist and belong to this problem
    result = await db.execute(
        select(Context).where(Context.id.in_(req.context_ids))
    )
    found = result.scalars().all()
    found_ids = {str(c.id) for c in found}

    invalid = set(req.context_ids) - found_ids
    if invalid:
        raise HTTPException(400, f"Invalid context_ids: {invalid}")

    # Run dispatch — waits for completion
    results = await dispatch_batch(
        problem_id=req.problem_id,
        context_ids=req.context_ids,
        max_concurrent=req.max_concurrent,
    )

    # CRM writeback if requested
    writeback_summary = None
    if req.writeback:
        writeback_summary = await writeback_results(results, db)

    done = sum(1 for r in results if r["status"] == "done")
    failed = sum(1 for r in results if r["status"] == "failed")

    return ProcessResponse(
        problem_id=req.problem_id,
        total=len(results),
        done=done,
        failed=failed,
        results=results,
        writeback_summary=writeback_summary,
    )


# ============================================================
# 4. GET RESULTS (query existing tables normally)
# ============================================================

@router.get("/results", response_model=List[ResultItem])
async def get_results(
    context_ids: Optional[str] = None,
    problem_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve generated emails for contexts. Uses existing tables only.
    """
    stmt = select(Context).order_by(Context.created_at.desc())

    if context_ids:
        ids = [i.strip() for i in context_ids.split(",") if i.strip()]
        stmt = stmt.where(Context.id.in_(ids))

    if problem_id:
        stmt = stmt.where(Context.problem_id == problem_id)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    contexts = result.scalars().all()

    if not contexts:
        return []

    # Pre-fetch FinalEmails
    cids = [c.id for c in contexts]
    email_result = await db.execute(
        select(FinalEmail).where(FinalEmail.context_id.in_(cids))
    )
    email_map = {str(e.context_id): e for e in email_result.scalars().all()}

    return [
        ResultItem(
            context_id=c.id,
            status="done" if c.id in email_map else "pending",
            industry=c.industry,
            company_size=c.company_size,
            decision_actor=c.decision_actor,
            subject_line=email_map[c.id].final_email.split("\n")[0][:120] if c.id in email_map else None,
            final_email=email_map[c.id].final_email if c.id in email_map else None,
            error=None,
            created_at=str(c.created_at) if c.created_at else None,
        )
        for c in contexts
    ]


# ============================================================
# 5. GET CONTEXTS WITHOUT EMAILS (failed or pending)
# ============================================================

@router.get("/pending")
async def get_pending_contexts(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns contexts that have no FinalEmail linked (failed or never processed).
    Useful for retry logic.
    """
    email_result = await db.execute(select(FinalEmail.context_id))
    has_email_ids = {str(r[0]) for r in email_result.all()}

    stmt = select(Context).where(Context.problem_id == problem_id)
    if has_email_ids:
        stmt = stmt.where(Context.id.notin_(has_email_ids))

    result = await db.execute(stmt.order_by(Context.created_at.desc()))
    contexts = result.scalars().all()

    return [
        {
            "context_id": c.id,
            "industry": c.industry,
            "company_size": c.company_size,
            "decision_actor": c.decision_actor,
            "constraints": c.constraints,
            "created_at": str(c.created_at),
        }
        for c in contexts
    ]