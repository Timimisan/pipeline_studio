from app.schemas import RuntimeContext
from app.models.models import RunPipelineRequest
from app.repositories import get_problem_or_404, get_context_or_404
from app.pipeline.orchestrator import run_pipeline
from sqlalchemy.ext.asyncio import AsyncSession


async def run_generation(request: RunPipelineRequest, db: AsyncSession, user_id: str):
    # 1. Fetch problem (scoped to user)
    problem = await get_problem_or_404(db, request.problem_id, user_id)

    # 2. Fetch context (scoped to user)
    context = await get_context_or_404(db, request.context_id, user_id)

    # 3. Convert context → RuntimeContext
    runtime_context = RuntimeContext(
        id=str(context.id),
        problem_id=str(problem.id),
        industry=context.industry,
        company_size=context.company_size,
        decision_actor=context.decision_actor,
        extra=context.extra or "",
        constraints=context.constraints or []
    )

    # 4. Serialize problem
    problem_dict = {
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
    }

    # 5. Run pipeline
    result = await run_pipeline(db, problem_dict, runtime_context)

    return result