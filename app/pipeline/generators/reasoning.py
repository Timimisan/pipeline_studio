from app.schemas import RuntimeContext
from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_reasoning_states(
        problem: dict,
        context: RuntimeContext,
        compressed_signals: dict,   # 👈 NEW INPUT
        previous_result: Optional[dict] = None,
        failure_reason: str = "",
        temperature: float = 0.1,
        model="gpt_4.5_mini"
) -> tuple[dict, LLMUsage]:
    feedback_section = ""

    if previous_result is not None and failure_reason:
        feedback_section = f"""
    PREVIOUS QUESTION ATTEMPT (FAILED):
    {previous_result}

    FAILURE REASON:
    {failure_reason}

    INSTRUCTIONS FOR THIS RETRY:
    - Fix ONLY the semantic issue identified above
    - Preserve all anchored meaning
    - Do NOT rewrite correct sections
    - Do NOT introduce new operational ideas
    """


    prompt = f"""
    You are generating structured reasoning states.
    
    YOU MUST FOLLOW STRICT RULES:
    
    You are given:
    - Failure Mode A: {problem['failure_mode_A']}
    - Failure Mode B: {problem['failure_mode_B']}
    - contradiction = {problem['contradiction']}
    and the mechanisms:
    - Failure Mode A mechanism: {problem['failure_mode_A_mechanism']}
    - Failure Mode B mechanism: {problem['failure_mode_B_mechanism']}
    
    You are also given context:
    - Industry: {context.industry}
    - Company Size: {context.company_size}
    - Constraints: {', '.join(context.constraints)}
    - Extra context: {context.extra}
    
    You are also given retrieval enrichment signals:
    - Retrieved Pressure Signals: {compressed_signals.get("pressure_signals", [])}
    - Retrieved Contradiction Signals: {compressed_signals.get("contradiction_signals", [])}
    - Retrieved Market Signals: {compressed_signals.get("market_signals", [])}
    - Retrieved Language Signals: {compressed_signals.get("language_signals", [])}
    
    {feedback_section}
    
    TASK:
    1. deduct how Failure Mode A appears in THIS context
    2. deduct how Failure Mode B appears in THIS context
    3. Construct a contradiction between them
    4. Define decision consequence 
    
    OUTPUT FORMAT (JSON ONLY):
    
    {{
      "contextualized_A": "",
      "contextualized_B": "",
      "contradiction": "",
      "decision_consequence": "",
    }}
    
    RULES:
    - DO NOT invent new failure modes
    - DO NOT introduce new problems
    - MUST use only Failure Mode A and B
    - MUST tie everything to provided context
    - contextualized_A MUST explicitly deduct how "{problem['failure_mode_A']}" manifests in this context and must be anchored on {problem['system']}
    - contextualized_B MUST explicitly deduct how "{problem['failure_mode_B']}" manifests in this context as a result of Failure Mode A
    - must USE the more human equivalent of the subject
    - deduct how contradiction shows up in this context
    - contradiction MUST be anchored on the provided contradiction
    - decision_consequence MUST describe a decision-level failure anchored to {context.decision_actor} without mentioning {context.decision_actor}.
    - MUST reference business decisions (evaluation, purchasing, allocation)
    - MUST NOT use explanatory beginnings like 'In this,' or start with reframing the context.
    - MUST NOT simulate perception. you must state structural behavior directly.
    - MUST USE the more human equivalent of the subject
    - MUST NOT revert to referent inertia equivalent as the subject
    
    
    """

    result, usage = await call_llm(prompt, temperature=temperature)
    return result, usage

