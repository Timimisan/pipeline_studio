from dataclasses import dataclass
from typing import Any
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


@dataclass
class RuntimeContext:
    id: str
    problem_id: str
    industry: str
    company_size: str
    decision_actor: str
    extra: str
    constraints: list[str]

    def __str__(self) -> str:
        return f"ID: {self.id}, Industry: {self.industry}, Size: {self.company_size}, Constraints: {', '.join(self.constraints)}"


class StageStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    REPAIRING = "repairing"
    COMPLETE = "complete"


class FailureClass(str, Enum):
    SEMANTIC_DRIFT = "semantic_drift"
    CONTRADICTION_MISMATCH = "contradiction_mismatch"
    HOOK_REDUNDANCY = "hook_redundancy"
    EXPLANATORY_DRIFT = "explanatory_drift"
    MECHANISM_MISMATCH = "mechanism_mismatch"
    IDENTITY_MISSING = "identity_missing"
    SALES_DRIFT = "sales_drift"
    LENGTH_VIOLATION = "length_violation"
    FORMAT_ERROR = "format_error"
    UNKNOWN = "unknown"


@dataclass
class StageTrace:
    stage: str
    status: StageStatus
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    output: Any = None
    failure_class: Optional[FailureClass] = None
    failure_reason: str = ""
    retry_count: int = 0
    validation_scores: dict = field(default_factory=dict)
    attempts_history: list = field(default_factory=list)


@dataclass
class PipelineTrace:
    request_id: str
    problem_id: str
    context_id: str
    stages: list[StageTrace] = field(default_factory=list)
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    final_status: str = "incomplete"


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str
    previous_result: Any = None
    metrics: Any = None
    failure_class: Optional[FailureClass] = None

    @classmethod
    def valid(cls, metrics: Any = None) -> "ValidationResult":
        return cls(True, "", None, metrics, None)

    @classmethod
    def invalid(cls, reason: str, previous_result: Any = None, metrics=None, failure_class: FailureClass = FailureClass.UNKNOWN) -> "ValidationResult":
        return cls(False, reason, previous_result, metrics, failure_class)


