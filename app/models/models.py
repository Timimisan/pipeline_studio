from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CreateProblemRequest(BaseModel):
    problem_name: str
    core_problem: str
    system: str
    causal_mechanism: str
    failure_mode_A: str
    failure_mode_B: str
    failure_mode_A_mechanism: str
    failure_mode_B_mechanism: str
    contradiction:str
    business_impact: str
    solution_mechanism: str
    solution_actor:str


class CreateContextRequest(BaseModel):
    problem_id: str
    industry: str
    company_size: str
    decision_actor: str
    extra: Optional[str] = ""
    constraints: List[str] = []



class UserRead(BaseModel):
    id: str
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    oauth_provider: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2: allows ORM model mapping


class RunPipelineRequest(BaseModel):
    problem_id: str
    context_id: str

class AllProblem(BaseModel):
    id: str
    problem_name: str
    core_problem: str
    system: str
    causal_mechanism: str
    failure_mode_A: str
    failure_mode_B: str
    failure_mode_A_mechanism: str
    failure_mode_B_mechanism: str
    contradiction:str
    business_impact: str
    solution_mechanism: str
    solution_actor:str
    created_at: Optional[datetime]


class AllContext(BaseModel):
    id: str
    problem_id: str
    industry: str
    company_size: str
    decision_actor: str
    extra: Optional[str] = ""
    constraints: List[str] = []
    created_at: Optional[datetime]

