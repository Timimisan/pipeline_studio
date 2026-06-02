from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    PARTIAL = "partial"

class RowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

class ColumnMapping(BaseModel):
    """Maps CSV column names to Context fields."""
    industry: str = "industry"
    company_size: str = "company_size"
    decision_actor: str = "decision_actor"
    extra: Optional[str] = None
    constraints: Optional[List[str]] = None

class CreateBatchRequest(BaseModel):
    problem_id: str
    column_mapping: ColumnMapping
    # constraints applied to ALL rows in the batch (optional)
    global_constraints: List[str] = []

class BatchResponse(BaseModel):
    batch_id: str
    problem_id: str
    status: BatchStatus
    total_rows: int
    completed_rows: int
    failed_rows: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class BatchRowResponse(BaseModel):
    row_id: str
    batch_id: str
    status: RowStatus
    raw_data: Dict[str, Any]
    context_id: Optional[str]
    email_id: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]

class BatchProgressResponse(BaseModel):
    batch_id: str
    status: BatchStatus
    total: int
    pending: int
    processing: int
    done: int
    failed: int
    percent_complete: int

class BatchResultItem(BaseModel):
    row_id: str
    raw_data: Dict[str, Any]
    context_id: str
    subject_line: Optional[str]
    final_email: Optional[str]
    overall_score: Optional[float]
    status: RowStatus
    error_message: Optional[str]