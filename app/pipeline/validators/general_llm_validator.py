from __future__ import annotations
from app.core.llm_gateway import call_llm


# ============================================================
# TENSION VALIDATOR
# ============================================================

async def llm_validate_tension(
        tension: str,
        hook: str,
        state: dict
) -> tuple[bool, str, dict]:


    json_example = """{
  "valid": true/false,
  "reason": "specific semantic correction guidance while preserving anchored parts",
  "scores": {
      "contradiction_alignment": 0.0,
      "inevitability": 0.0,
      "compression_integrity": 0.0,
      "hook_redundancy": 0.0,
      "semantic_drift": 0.0
  }
}"""

    prompt = f"""
    You are a strict validation system for the tension segment of a structured cold email generation pipeline.

    You are given:

    STATE:
    - Failure Mode A: {state["failure_mode_A"]}
    - Failure Mode B: {state["failure_mode_B"]}
    - Contradiction: {state["contradiction"]}

    Tension:
    {tension}

    TASK:
    Check if the Tension correctly preserves meaning and logical constraints.

    VALIDATION CRITERIA:

    1. Semantic Preservation
    - Does it preserve BOTH Failure Mode A and B accurately?
    - Does it preserve contradiction meaning?

    2. Logical Alignment
    - Does it express the correct relationship (A vs B conflict)?

    3. RULES
    must compress contradiction only


    4. No Drift Rule
    - Reject if it introduces new ideas not grounded in state
    - Reject if tension introduces solution
    
    SCORING:
    
    Score the following independently from 0.0 to 1.0:
    
    - contradiction_alignment
    - inevitability
    - compression_integrity
    - hook_redundancy
    - semantic_drift
    
    SCORING INTERPRETATION:
    
    - contradiction_alignment:
    How well the tension preserves the contradiction invariant.
    
    - inevitability:
    How strongly the tension feels like an unavoidable consequence.
    
    - compression_integrity:
    How effectively the tension compresses meaning without explanation.
    
    - hook_redundancy:
    How much the tension merely repeats the hook.
    HIGH = BAD.
    
    - semantic_drift:
    How much unrelated meaning was introduced.
    HIGH = BAD.
    
    FINAL VALIDITY RULE:
    
    Reject if:
    - contradiction_alignment < 0.70
    - inevitability < 0.65
    - compression_integrity < 0.60
    - hook_redundancy > 0.45
    - semantic_drift > 0.30
    
    OUTPUT FORMAT (STRICT JSON):
    {json_example}
"""

    result, usage = await call_llm(prompt, temperature=0.1)

    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", "no reason"),
            result.get("scores", {})
        )

    return (
        False,
        "invalid LLM response",
        {}
    )


# ============================================================
# HOOK VALIDATOR
# ============================================================

async def llm_validate_hook(hook: str, state: dict) -> tuple[bool, str, dict]:
    """
    LLM-based semantic validator.
    Returns (is_valid, reason, scores)
    """

    json_example = """{
  "valid": true/false,
  "reason": "specific semantic correction guidance while preserving anchored parts",
  "scores": {
    "contradiction_alignment": 0.0,
    "operational_tension": 0.0,
    "consequence_alignment": 0.0,
    "semantic_drift": 0.0,
    "explanatory_drift": 0.0
  }
}"""

    prompt = f"""
You are a strict semantic validation system for a structured cold email generation pipeline.

Your job is NOT to judge writing quality.
Your job is to verify whether the hook preserves the semantic truth of the provided reasoning state without drift.

REASONING STATE:

Failure Mode A:
{state.get("failure_mode_A", "")}

Failure Mode B:
{state.get("failure_mode_B", "")}

Contradiction:
{state.get("contradiction", "")}

Decision Consequence:
{state.get("decision_consequence", "")}

HOOK:
{hook}

VALIDATION OBJECTIVE:

The hook must remain semantically anchored to the provided reasoning state.

The hook is allowed to:
- compress ideas
- rephrase naturally
- convert technical language into human language
- make the contradiction more conversational

The hook is NOT allowed to:
- introduce new mechanisms
- introduce unrelated business problems
- shift the optimization pressure
- change the contradiction itself
- invent external consequences
- abstract away the core operational tension

CORE RULES:

1. The hook must express:
   - the contradiction
   - the consequence of the contradiction

2. The hook must preserve the SAME semantic tension defined in the state.

3. Both sides of the hook must describe observable outcomes or operational realities.
   - Do NOT explain WHY they happen
   - Do NOT introduce causal analysis
   - Do NOT teach

4. The hook must contain two opposing outcomes that create tension.

5. The hook opening must NOT be explanatory.
   Reject:
   - educational openings
   - framing statements
   - abstract setup language
   - generalized commentary

6. The hook must use a natural human equivalent of the subject instead of repeating technical state language mechanically.

7. Reject if the hook contains:
   decision_actor: {state.get("decision_actor")}
   or close semantic synonyms.

SEMANTIC DRIFT RULES:

Semantic drift includes:
- changing the original contradiction
- introducing new business pressures
- replacing personalization problems with scaling problems
- replacing instability with poor targeting
- changing operational outcomes
- adding unrelated abstractions
- turning outcomes into explanations

IMPORTANT FAILURE HANDLING RULE:

Do NOT ask for full rewrites.

Your failure reason must behave like partial optimization:
- identify ONLY the exact semantic region that drifted
- explain WHY it drifted
- explain what specifically must change
- preserve every anchored part of the hook

GOOD FAILURE REASONS:

- "The second outcome drifted into lead quality issues which are not present in the reasoning state. Keep the tension focused on instability caused by attempts to improve personalization."

- "The opening becomes explanatory by describing why the system behaves this way. Start directly from the operational tension instead."

- "The contradiction is preserved, but the consequence introduces scaling concerns not present in the provided state. Keep the consequence tied to unpredictable personalization quality."

- "The hook preserves the contradiction but converts observable outcomes into causal explanations. Keep both sides grounded in what operationally happens."

SCORING RULES:

Score independently from 0.0-1.0:

- contradiction_alignment:
How well the hook preserves the original contradiction.

- operational_tension:
How strongly the hook expresses opposing operational outcomes.

- consequence_alignment:
How well the hook preserves the decision consequence.

- semantic_drift:
How much unrelated meaning or optimization pressure was introduced.
HIGH = BAD.

- explanatory_drift:
How much the hook shifts from observable outcomes into explanation or teaching.
HIGH = BAD.

REJECT IF:
- contradiction_alignment < 0.70
- operational_tension < 0.65
- consequence_alignment < 0.60
- semantic_drift > 0.30
- explanatory_drift > 0.35

OUTPUT FORMAT (STRICT JSON):
{json_example}
"""

    result, usage = await call_llm(prompt, temperature=0.1)
    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", "no reason"),
            result.get("scores", {})
        )
    return (
        False,
        "invalid LLM response",
        {}
    )


# ============================================================
# AUTHORITY VALIDATOR
# ============================================================

async def llm_validate_authority(
        authority_text: str,
        state: dict,
        hook: str,
        transition_question: str,
        problem: dict,
) -> tuple[bool, str, dict]:

    """
    Validates whether the authority section:
    - remains semantically anchored to the solution mechanism
    - structurally resolves the established tension
    - flows naturally from the hook and transition question
    - properly introduces the authority identity
    """

    json_example = """{
  "valid": true/false,
  "reason": "specific semantic correction guidance while preserving anchored parts",
  "scores": {
    "mechanism_alignment": 0.0,
    "tension_resolution": 0.0,
    "authority_identity": 0.0,
    "semantic_drift": 0.0
  }
}"""

    prompt = f"""
You are a strict semantic validation system for a structured cold email generation pipeline.

Your job is NOT to judge writing quality.

Your job is to verify whether the authority section:
- remains semantically anchored to the provided mechanism
- resolves the established operational tension correctly
- continues naturally from the hook and transition question
- introduces authority identity correctly
- avoids semantic drift

CONTEXT:

HOOK:
{hook}

TRANSITION QUESTION:
{transition_question}

CONTRADICTION:
{state.get("contradiction", "")}

DECISION CONSEQUENCE:
{state.get("decision_consequence", "")}

SOLUTION MECHANISM:
{state.get("solution_mechanism", "")}

EXPECTED AUTHORITY IDENTITY:
"{problem.get('solution_actor', '')}"

AUTHORITY TEXT:
{authority_text}

VALIDATION OBJECTIVE:

The authority section must feel like:
- the natural continuation of the unresolved tension
- the beginning of structural stabilization
- a grounded explanation from someone who understands the system operationally


AUTHORITY OPENING RULE:

The paragraph MUST begin with a first-person authority introduction.

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

The authority section must remain fully anchored to:
solution_mechanism:
{state.get("solution_mechanism", "")}

Everything described in the authority section must already exist implicitly inside the provided mechanism.

If a concept cannot be traced back to the mechanism:
REJECT.

IDENTITY RULE:

The authority section MUST begin by introducing who is speaking.

It must start with:
"I am {problem.get('solution_actor', '')}" or its synonyms

Reject if:
- the identity introduction is missing
- the opening becomes explanatory before identity is established
- the authority voice feels detached from the mechanism

GOOD:
"I build constrained generation systems that keep outputs inside validated reasoning boundaries..."

BAD:
"Most systems fail because..."
(REJECT: explanatory opening before authority identity)

BAD:
"There are several ways to solve this..."
(REJECT: detached and generic opening)

CORE RULES:

1. The authority section must continue naturally from:
   - the hook
   - the transition question

It should feel like:
- the next logical operational explanation
not:
- a topic reset
- a new essay
- a disconnected sales pitch

2. The authority section must structurally stabilize the tension.

It must show:
- how instability becomes controlled
- how probabilistic drift becomes bounded
- how operational behavior becomes more predictable

3. The authority section must remain operational.

Reject:
- marketing language
- visionary abstraction
- philosophical commentary
- generic AI claims
- thought-leader style writing

4. The authority section must NOT:
- restate the contradiction
- explain the problem again
- summarize earlier sections
- introduce unrelated solution categories
- inject tooling discussions not implied by the mechanism
- introduce scalability claims unless already implied

5. The authority section must express mechanism behavior, not implementation dumping.

GOOD:
"I constrain generation before outputs are selected so the system stays behaviorally consistent."

BAD:
"I use validators, embeddings, orchestration layers and retrieval pipelines."
(REJECT: implementation dumping)

SEMANTIC DRIFT RULES:

Semantic drift includes:
- changing the original contradiction
- changing the optimization pressure
- introducing unrelated operational concerns
- replacing instability with different problems
- adding external architecture not present in the mechanism
- introducing solution claims outside the provided reasoning state
- drifting from operational stabilization into general AI commentary

IMPORTANT FAILURE HANDLING RULE:

Do NOT ask for full rewrites.

Your failure reason must behave like partial optimization:
- identify ONLY the exact semantic region that drifted
- explain WHY it drifted
- explain what specifically must change
- preserve every anchored part

GOOD FAILURE REASONS:

- "The opening starts with generalized commentary before establishing authority identity. Begin directly with 'I {problem.get('solution_actor', '')}' before introducing operational behavior."

- "The authority remains anchored initially, but later introduces retrieval architecture that does not exist in the provided mechanism. Keep the explanation constrained to structural control and validation behavior."

- "The section partially restates the contradiction instead of transitioning into stabilization behavior. Assume the tension is already understood and continue directly into control logic."

- "The authority introduces scaling guarantees that are not implied by the mechanism. Keep the focus on stabilizing probabilistic behavior."


SCORING RULES:

Score independently from 0.0-1.0:

- mechanism_alignment:
How well the authority stays anchored to the solution mechanism.

- tension_resolution:
How effectively the authority stabilizes the contradiction introduced earlier.

- authority_identity:
How clearly the opening establishes relevant first-person operational expertise.

- semantic_drift:
How much unrelated meaning or architecture was introduced.
HIGH = BAD.

REJECT IF:
- mechanism_alignment < 0.70
- tension_resolution < 0.65
- authority_identity < 0.70
- semantic_drift > 0.30

OUTPUT FORMAT (STRICT JSON):
{json_example}
"""

    result, usage = await call_llm(prompt, temperature=0.1)
    if isinstance(result, dict):
        return (
            result.get("valid", False),
            result.get("reason", "no reason"),
            result.get("scores", {})
        )
    return (
        False,
        "invalid LLM response",
        {}
    )