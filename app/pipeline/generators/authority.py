from typing import Optional
from app.core.llm_gateway import call_llm, LLMUsage


async def generate_authority(
        state: dict,
        hook: str,
        transition_question: str,
        problem: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.2,
        model="gpt-5.4-mini",
) -> tuple[str, LLMUsage]:

    # -------------------------
    # Feedback section
    # -------------------------
    feedback_section = ""

    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS AUTHORITY ATTEMPT (FAILED):
{previous_result}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS FOR THIS RETRY:
- Fix ONLY the semantic issue identified above
- Preserve all anchored meaning
- Do NOT rewrite correct sections
- Do NOT introduce new operational ideas
"""

    # -------------------------
    # Prompt
    # -------------------------
    prompt = f"""
You are:
{problem['solution_actor']}.

You are writing the AUTHORITY section of a high-level analytical email.

The reader has already seen:
- the operational tension
- the contradiction
- the consequence of instability

Your job now is to continue naturally into:
- how the instability gets structurally controlled
- how the tension becomes operationally manageable

You are given:

HOOK:
{hook}

TRANSITION QUESTION:
{transition_question}

UNDERLYING CONTRADICTION:
{state["contradiction"]}

DECISION CONSEQUENCE:
{state["decision_consequence"]}

CORE SOLUTION MECHANISM:
{state["solution_mechanism"]}

FEEDBACK:
{feedback_section}

IDENTITY:
{problem['solution_actor']}

OBJECTIVE:

Write a paragraph that:
- feels like a direct continuation of the hook and transition question
- introduces the operational mechanism naturally
- shows how the mechanism stabilizes the tension
- stays grounded in real system behavior
- reads like practical implementation reality, not marketing

RULE:
- MUST be anchored to CORE SOLUTION MECHANISM

AUTHORITY OPENING RULE:

he paragraph MUST begin with a first-person authority introduction.


The opening must establish:
1. who the speaker is
2. what they specialize in
3. why their expertise is directly relevant to the instability described earlier

The opening should sound like:
- a practitioner speaking from operational experience
- someone who has repeatedly handled this exact failure pattern in practice

GOOD EXAMPLES:

"I am an AI automation engineer specialised in stabilizing probabilistic outreach systems where personalization quality degrades under prompt iteration."

"I am a surgeon specialised in reconstructive procedures where small structural errors compound into long term instability."

"I am a plumber specialised in pressure balancing systems where uncontrolled flow variation creates recurring failures."

BAD EXAMPLES:

"AI Automation Engineer specialised in..."
(REJECT: title fragment, not a first-person authority introduction)

"There are several ways to solve this..."
(REJECT: no identity establishment)

"Most systems fail because..."
(REJECT: explanatory opening before authority establishment)

"I help companies scale..."
(REJECT: generic positioning instead of operational specialization)

SEMANTIC ANCHORING RULE:

Everything described in the authority section must be traceable back to the provided mechanism.

DO NOT:
- introduce unrelated solution ideas
- inject new business problems
- introduce external tooling concepts
- introduce scalability claims unless already implied
- introduce implementation details not present in the mechanism
- add abstractions outside the provided reasoning state

IMPORTANT:

Assume the contradiction is already understood.

Do NOT:
- restate the hook
- explain the contradiction again
- re-teach the problem
- summarize previous sections

Instead:
state who you are and continue directly into operational control and stabilization.

STYLE RULES:

- MUST start with who you are: {problem['solution_actor']}
- MUST sound operational and grounded
- MUST feel like practical system experience
- MUST avoid thought-leader style abstraction
- MUST avoid hype language
- MUST avoid educational framing
- MUST avoid philosophical commentary

LANGUAGE RULES:

- No em dashes
- No en dashes
- Use only commas and full stops
- Keep language compressed and controlled
- Prefer operational wording over conceptual wording

MECHANISM RULE:

Do NOT describe the mechanism as technical implementation details.

Instead:
express how the system behaves operationally once structure and control are introduced.

GOOD DIRECTION:
"I constrain generation inside predefined reasoning states so outputs are selected from bounded possibilities instead of drifting across probabilistic variations."

BAD DIRECTION:
"I use validators, retrieval systems, orchestration pipelines and multi-stage generation architectures."

ENDING RULE:

The paragraph should end with implied stability.
Do NOT explicitly declare:
- certainty
- guaranteed success
- perfect outputs

The stability should feel like the natural consequence of structural control.

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
  "authority_text": ""
}}
"""

    result, usage= await call_llm(
        prompt=prompt,
        temperature=temperature,
        max_tokens=1000,
        model=model
    )

    authority_text= result.get("authority_text",result.get("text", str(result)))
    return authority_text,usage