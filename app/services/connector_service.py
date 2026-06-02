from __future__ import annotations
import csv
import io
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import build_context

# ============================================================
# CSV PARSING
# ============================================================

def parse_csv_bytes(file_bytes: bytes) -> List[Dict[str, str]]:
    """Parse uploaded CSV into clean row dicts."""
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = [
        {k: (v or "").strip() for k, v in row.items()}
        for row in reader
        if any(v.strip() for v in row.values())
    ]
    return rows


# ============================================================
# COLUMN MAPPER — per-row constraints from CSV columns
# ============================================================

def map_row_to_context_fields(
    row: Dict[str, str],
    mapping: Dict[str, str],
) -> Dict[str, Any]:
    """
    Maps a single CSV/CRM row to Context constructor kwargs.

    mapping defines which CSV columns map to which Context fields:
    {
        "industry": "Sector",
        "company_size": "Size",
        "decision_actor": "Role",
        "extra": "Notes",
        "constraints": "Tags"     # ← comma-separated in this CSV column
    }

    Every row has its own constraints. No global constraints exist.
    """
    industry = row.get(mapping.get("industry", "industry"), "unknown")
    company_size = row.get(mapping.get("company_size", "company_size"), "unknown")
    decision_actor = row.get(mapping.get("decision_actor", "decision_actor"), "unknown")

    extra = None
    if mapping.get("extra"):
        extra = row.get(mapping["extra"], "")

    # Per-row constraints — parsed from the CSV cell designated by mapping
    constraints = []
    if mapping.get("constraints"):
        raw = row.get(mapping["constraints"], "")
        if raw:
            constraints = [c.strip() for c in raw.split(",") if c.strip()]

    return {
        "industry": industry,
        "company_size": company_size,
        "decision_actor": decision_actor,
        "extra": extra,
        "constraints": constraints,
    }


# ============================================================
# CONTEXT CREATOR — CSV import, per-row constraints
# ============================================================

async def create_contexts_from_csv(
    db: AsyncSession,
    problem_id: str,
    rows: List[Dict[str, str]],
    mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Creates one Context per CSV row using your existing build_context().
    Each row has its own constraints from the CSV. No global constraints.

    Returns a list of created context dicts with their IDs.
    """
    created = []

    for row in rows:
        fields = map_row_to_context_fields(row, mapping)

        # Stash raw row data in extra as JSON for traceability
        extra_payload = {}
        if fields.get("extra"):
            extra_payload["note"] = fields["extra"]
        extra_payload["raw"] = row
        extra_json = json.dumps(extra_payload) if extra_payload else None

        ctx = await build_context(
            db=db,
            problem_id=problem_id,
            industry=fields["industry"],
            company_size=fields["company_size"],
            decision_actor=fields["decision_actor"],
            extra=extra_json,
            constraints=fields["constraints"],
        )

        created.append(ctx)

    return created


# ============================================================
# CRM FETCHERS
# ============================================================

async def fetch_google_sheet_rows(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Pull rows from a Google Sheet. Returns list of field dicts."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise RuntimeError("gspread not installed. Run: pip install gspread google-auth")

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(
        config.get("credentials_path", "gsheets-credentials.json"),
        scopes=scopes
    )
    client = gspread.authorize(creds)

    sheet = client.open_by_key(config["sheet_id"])
    worksheet = sheet.worksheet(config.get("worksheet_name", "Sheet1"))
    records = worksheet.get_all_records()

    return [{k: str(v) for k, v in rec.items()} for rec in records]


async def fetch_airtable_rows(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Pull rows from an Airtable base. Returns list of field dicts."""
    try:
        from pyairtable import Api
    except ImportError:
        raise RuntimeError("pyairtable not installed. Run: pip install pyairtable")

    import os
    api_key = config.get("api_key") or os.getenv("AIRTABLE_API_KEY")
    if not api_key:
        raise RuntimeError("Airtable API key missing")

    api = Api(api_key)
    table = api.table(config["base_id"], config["table_name"])
    records = table.all()

    return [{k: str(v) for k, v in rec.get("fields", {}).items()} for rec in records]


# ============================================================
# CONTEXT CREATOR — CRM import, per-row constraints
# ============================================================

async def create_contexts_from_crm(
    db: AsyncSession,
    problem_id: str,
    rows: List[Dict[str, str]],
    mapping: Dict[str, str],
    source: str,
    crm_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Creates contexts from CRM rows. Each row has its own constraints.
    CRM metadata is stashed in Context.extra for writeback later.
    """
    created = []

    for i, row in enumerate(rows):
        fields = map_row_to_context_fields(row, mapping)

        extra_payload = {}
        if fields.get("extra"):
            extra_payload["note"] = fields["extra"]
        extra_payload["raw"] = row

        # Stash CRM metadata for writeback later
        crm_meta = dict(crm_config)
        if source == "google_sheets":
            crm_meta["row_number"] = i + 2  # +2 because row 1 is headers
        elif source == "airtable":
            # record_id would need to come from fetch; we handle that in routes
            pass

        extra_payload["crm"] = crm_meta
        extra_payload["source"] = source

        extra_json = json.dumps(extra_payload)

        ctx = await build_context(
            db=db,
            problem_id=problem_id,
            industry=fields["industry"],
            company_size=fields["company_size"],
            decision_actor=fields["decision_actor"],
            extra=extra_json,
            constraints=fields["constraints"],
        )

        created.append(ctx)

    return created