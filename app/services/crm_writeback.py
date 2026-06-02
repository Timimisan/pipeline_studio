from __future__ import annotations
from typing import Dict, Any

# ============================================================
# GOOGLE SHEETS
# ============================================================

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False


async def push_to_google_sheets(
    crm_meta: Dict[str, Any],
    email_text: str,
    status: str,
) -> bool:
    """
    Writes generated email + status back to a specific Google Sheet row.
    crm_meta comes from Context.extra["crm"].
    """
    if not GSHEETS_AVAILABLE:
        print("[CRM] gspread not installed, skipping Sheets writeback")
        return False

    sheet_id = crm_meta.get("sheet_id")
    worksheet_name = crm_meta.get("worksheet_name", "Sheet1")
    row_number = crm_meta.get("row_number")
    email_col = crm_meta.get("email_column", "Email")
    status_col = crm_meta.get("status_column", "Status")
    credentials_path = crm_meta.get("credentials_path", "gsheets-credentials.json")

    if not sheet_id or not row_number:
        print("[CRM] Missing sheet_id or row_number in CRM metadata")
        return False

    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)

        # Find column indices by header name
        headers = worksheet.row_values(1)

        def col_idx(name):
            try:
                return headers.index(name) + 1  # gspread is 1-based
            except ValueError:
                return None

        email_idx = col_idx(email_col)
        status_idx = col_idx(status_col)

        if email_idx:
            worksheet.update_cell(row_number, email_idx, email_text)
        if status_idx:
            worksheet.update_cell(row_number, status_idx, status)

        return True

    except Exception as e:
        print(f"[CRM] Google Sheets writeback failed: {e}")
        return False


# ============================================================
# AIRTABLE
# ============================================================

try:
    from pyairtable import Api
    AIRTABLE_AVAILABLE = True
except ImportError:
    AIRTABLE_AVAILABLE = False


async def push_to_airtable(
    crm_meta: Dict[str, Any],
    email_text: str,
    status: str,
) -> bool:
    """
    Updates an Airtable record with generated email + status.
    crm_meta comes from Context.extra["crm"].
    """
    if not AIRTABLE_AVAILABLE:
        print("[CRM] pyairtable not installed, skipping Airtable writeback")
        return False

    base_id = crm_meta.get("base_id")
    table_name = crm_meta.get("table_name")
    record_id = crm_meta.get("record_id")
    email_field = crm_meta.get("email_field", "Email")
    status_field = crm_meta.get("status_field", "Status")
    api_key = crm_meta.get("api_key")

    if not base_id or not table_name or not record_id:
        print("[CRM] Missing base_id, table_name, or record_id in CRM metadata")
        return False

    try:
        api = Api(api_key)
        table = api.table(base_id, table_name)

        table.update(record_id, {
            email_field: email_text,
            status_field: status,
        })

        return True

    except Exception as e:
        print(f"[CRM] Airtable writeback failed: {e}")
        return False