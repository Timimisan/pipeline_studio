from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import build_problem, build_context
from app.models.models import CreateProblemRequest, CreateContextRequest


async def create_problem(db: AsyncSession, request: CreateProblemRequest, user_id: str) -> dict:
    problem = await build_problem(
        db=db,
        user_id=user_id,
        problem_name=request.problem_name,
        core_problem=request.core_problem,
        system=request.system,
        causal_mechanism=request.causal_mechanism,
        failure_mode_A=request.failure_mode_A,
        failure_mode_B=request.failure_mode_B,
        failure_mode_A_mechanism=request.failure_mode_A_mechanism,
        failure_mode_B_mechanism=request.failure_mode_B_mechanism,
        contradiction=request.contradiction,
        business_impact=request.business_impact,
        solution_mechanism=request.solution_mechanism,
        solution_actor=request.solution_actor
    )

    return {
        "id": problem['id'],
        "snapshot": {
            "problem_name": problem['problem_name'],
            "core_problem": problem['core_problem'],
            "system": problem['system']
        }
    }


async def create_context(db: AsyncSession, request: CreateContextRequest, user_id: str) -> dict:
    context = await build_context(
        db=db,
        user_id=user_id,
        problem_id=request.problem_id,
        industry=request.industry,
        company_size=request.company_size,
        decision_actor=request.decision_actor,
        extra=request.extra,
        constraints=request.constraints
    )

    return {
        "id": context["id"],
        "snapshot": {
            "industry": context["industry"],
            "company_size": context["company_size"],
            "decision_actor": context["decision_actor"],
            "extra": context["extra"],
            "constraints": context["constraints"]
        }
    }