from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_hook(
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.1,
        model="gpt-4.1-mini",
) -> tuple[str, LLMUsage]:


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
    You are writing a HOOK for a high-level analytical email.

    You are given two underlying patterns:
    
    PATTERN A:
    {state["contextualized_A"]}
    
    PATTERN B:
    {state["contextualized_B"]}
    
    Contradiction:
    {state["contradiction"]}
    

    
    This leads to this consequence:
    {state["decision_consequence"]}
        
    feedback:
    {feedback_section}

    TASK:
    Write a hook that expresses this situation naturally.

    STRICT RULES:

    - DO NOT introduce any new ideas, scenarios, or interpretations
    - DO NOT explain anything
    - DO NOT reframe the situation
    - DO NOT use labels like "Pattern A", "Pattern B", or "failure mode"
    - DO NOT begin with generic setup phrases (e.g. "In today's world", "Many companies", "This happens when")
    - DO NOT mention structure or reasoning process
    - MUST NOT use explanatory beginnings like 'In this, it starts', the or start with reframing the context.
    - MUST NOT explain what has been previously explained or repeat yourself
    - MUST USE the more human equivalent of the subject
    - MUST USE contradiction
    - MUST NOT contain solution only state the problem
    - MUST preserve semantic meaning exactly.
        Rephrasing is allowed only if the underlying operational truth remains unchanged.
        Linguistic variation is permitted.
        Semantic drift is not.
    - opening must be plural and anchored to the system:{state['system']}
    - write the hook in details 
    
    TRANSFORMATION RULE:
    - You may only reuse meaning that already exists in the inputs.
    

    OUTPUT STYLE:
    - Direct diagnostic tone
    - No introductions
    - No framing

    OUTPUT FORMAT:
    Return ONLY valid JSON:

    {{
    "hook_text": ""
    }}
    """

    # -------------------------
    # 5. Call LLM WITH bias
    # -------------------------
    result, usage = await call_llm(
        prompt=prompt,
        temperature=temperature,
        #logit_bias=bias,
        max_tokens=1000,
        model=model,
    )

    hook_text = result.get("hook_text", result.get("text", str(result)))
    return hook_text, usage
