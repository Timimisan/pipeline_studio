from app.core.llm_gateway import call_llm,LLMUsage


async def final_assembly_stage(
        hook: str,
        tension: str,
        transition_question:str,
        authority: str,
        cta: str) -> tuple[str, LLMUsage]:

    prompt = f"""
You are the final assembly stage of a constrained persuasion system.

You are NOT allowed to introduce new meaning.

You are ONLY allowed to improve flow.

INPUT COMPONENTS:

HOOK:
{hook}

TENSION:
{tension}

TRANSITION_QUESTION:
{transition_question}

INTRO:
That's where i come in

AUTHORITY:
{authority}

CTA:
{cta}

HIDDEN CONSTRAINTS (DO NOT EXPOSE OR REPEAT):
- There exists an underlying contradiction between two realities in the system
- That contradiction must remain intact throughout the email
- A decision consequence must remain implicit throughout
- No meta-language about reasoning, structure, or generation is allowed

RULES:
- Do NOT mention “failure mode”, “contextualized”, or “reasoning”
- Do NOT describe structure of the system
- Do NOT restate constraints
- Preserve meaning only
- Improve flow only
- Maintain Hook → Tension → Transition_question → Intro → Authority → CTA order

STRICT:
If meaning changes → invalid output

Output JSON:
{{
  "email": ""
}}
"""
    result, usage = await call_llm(prompt)

    email = result.get("email", result.get("text", str(result)))
    return email, usage