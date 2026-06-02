from __future__ import annotations
import sqlite3
import math
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
from typing import Callable, Any, Optional, Tuple, List
from dataclasses import dataclass

load_dotenv()
client = OpenAI()
print("✓ API key loaded successfully")

# ============================================================
# VALIDATED RESULT CACHE (context_id + stage keyed)
# ============================================================

_validated_cache: dict[str, Any] = {}


def clear_validated_cache() -> None:
    """Clear all validated pipeline results."""
    _validated_cache.clear()
    print("✓ Validated cache cleared")


def _cache_key(context_id: str, stage: str) -> str:
    return f"{context_id}:{stage}"


def get_cached(context_id: str, stage: str) -> Any | None:
    """Retrieve a previously validated result for this context + stage."""
    return _validated_cache.get(_cache_key(context_id, stage))


def set_cached(context_id: str, stage: str, result: Any) -> None:
    """Store a validated result."""
    _validated_cache[_cache_key(context_id, stage)] = result


# ============================================================
# SINGLE LLM GATEWAY — NO INTERNAL CACHING
# ============================================================

def call_llm(prompt: str, temperature: float = 0.3, max_retries: int = 3) -> dict:
    """Single LLM gateway. ALWAYS returns a parsed dict. No caching."""
    print('calling Api')
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You must ALWAYS return valid JSON. "
                            "No markdown fences. No explanations outside the JSON. "
                            "Use the exact field keys requested in the prompt."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```", 2)[-1].removeprefix("json").strip()
            return json.loads(content)
        except Exception as e:
            print(f"[Retry {attempt + 1}] JSON parse failed:", e)
            time.sleep(1)
    raise ValueError("LLM failed to return valid JSON after retries.")


# ============================================================
# EMBEDDING HELPERS
# ============================================================

embedding_cache = {}


def embed(text: str):
    if text in embedding_cache:
        return embedding_cache[text]
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    vector = response.data[0].embedding
    embedding_cache[text] = vector
    return vector


def cosine_similarity(vec_a, vec_b):
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def semantic_similarity(text_a: str, text_b: str) -> float:
    emb_a = embed(text_a)
    emb_b = embed(text_b)
    return cosine_similarity(emb_a, emb_b)


def overlaps(text_a, text_b, threshold=0.6):
    emb_a = embed(text_a)
    emb_b = embed(text_b)
    return cosine_similarity(emb_a, emb_b) >= threshold


# ============================================================
# DROP TABLES
# ============================================================

def drop_all_tables():
    conn = sqlite3.connect('layer1_core.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DROP TABLE IF EXISTS tension_traces")
    cursor.execute("DROP TABLE IF EXISTS hook_traces")
    cursor.execute("DROP TABLE IF EXISTS reasoning_states")
    cursor.execute("DROP TABLE IF EXISTS problems")
    conn.commit()
    conn.close()
    print("✓ All tables dropped")


# ============================================================
# VALIDATION RESULT TYPES
# ============================================================

@dataclass
class ValidationResult:
    is_valid: bool
    reason: str
    previous_result: Any = None

    @classmethod
    def valid(cls) -> "ValidationResult":
        return cls(is_valid=True, reason="")

    @classmethod
    def invalid(cls, reason: str, previous_result: Any = None) -> "ValidationResult":
        return cls(is_valid=False, reason=reason, previous_result=previous_result)


class TensionResult:
    def __init__(self, valid: bool, score: float, reason: str):
        self.valid = valid
        self.score = score
        self.reason = reason

    @staticmethod
    def invalid(reason, score=0.0):
        return TensionResult(False, score, reason)

    @staticmethod
    def valid(score, reason="OK"):
        return TensionResult(True, score, reason)


# ============================================================
# GENERATE WITH RETRY — VALIDATION-AWARE CACHING
# ============================================================


def generate_with_retry(
        generator_fn: Callable[..., Any],
        validator_fn: Callable[[Any], ValidationResult],
        generator_args: Tuple = (),
        generator_kwargs: dict = None,
        max_retries: int = 5,
        temperature_increment: float = 0.1,
        context_id: Optional[str] = None,
        stage: Optional[str] = None
) -> Tuple[Any, List[ValidationResult]]:
    """
    Generate with retry. If context_id + stage provided and result validates,
    cache it for future retrieval.
    """

    if context_id and stage:
        cached = get_cached(context_id, stage)
        if cached is not None:
            print(f"[Cache hit] {context_id}:{stage} — returning validated result")
            return cached, [ValidationResult.valid()]

    if generator_kwargs is None:
        generator_kwargs = {}

    attempts = 0
    history: List[ValidationResult] = []
    previous_result: Any = None
    failure_reason: str = ""
    current_temperature = generator_kwargs.get("temperature", 0.3)

    while attempts < max_retries:
        retry_kwargs = dict(generator_kwargs)
        retry_kwargs["temperature"] = current_temperature

        if previous_result is not None:
            retry_kwargs["previous_result"] = previous_result
            retry_kwargs["failure_reason"] = failure_reason

        try:
            result = generator_fn(*generator_args, **retry_kwargs)
        except Exception as e:
            history.append(ValidationResult.invalid(f"Generator crashed: {str(e)}", previous_result))
            attempts += 1

            if attempts < max_retries:
                time.sleep(3)

            continue

        validation = validator_fn(result)
        history.append(validation)

        if validation.is_valid:
            if context_id and stage:
                set_cached(context_id, stage, result)
                print(f"[Cache store] {context_id}:{stage}")
            return result, history

        previous_result = result
        failure_reason = validation.reason
        attempts += 1
        current_temperature = min(current_temperature + temperature_increment, 1.0)

        print(f"[Attempt {attempts}/{max_retries}] Temp={current_temperature:.2f} Failed: {failure_reason}")

        if attempts < max_retries:
            time.sleep(3)

    raise RuntimeError(
        f"Failed after {max_retries} attempts. "
        f"Last failure: {failure_reason}. "
        f"History: {[v.reason for v in history]}"
    )


# ============================================================
# TABLE CREATION
# ============================================================

conn = sqlite3.connect('layer1_core.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

cursor.execute("""
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_name TEXT NOT NULL,
    core_problem TEXT NOT NULL,
    system TEXT NOT NULL,
    causal_mechanism TEXT NOT NULL,
    failure_mode_A TEXT NOT NULL,
    failure_mode_B TEXT NOT NULL,
    failure_mode_A_mechanism TEXT NOT NULL,
    failure_mode_B_mechanism TEXT NOT NULL,
    business_impact TEXT NOT NULL,
    solution_mechanism TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reasoning_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    system_context TEXT NOT NULL,
    failure_mode_A TEXT NOT NULL,
    failure_mode_B TEXT NOT NULL,
    contextualized_A TEXT NOT NULL,
    contextualized_B TEXT NOT NULL,
    contradiction TEXT NOT NULL,
    decision_consequence TEXT NOT NULL,
    evidence TEXT NOT NULL,
    valid INTEGER DEFAULT 0 CHECK (valid IN (0, 1)),
    selected INTEGER DEFAULT 0 CHECK (selected IN (0, 1)),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hook_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reasoning_state_id INTEGER NOT NULL,
    system_context TEXT NOT NULL,
    used_A TEXT NOT NULL,
    used_B TEXT NOT NULL,
    contextualized_A TEXT NOT NULL,
    contextualized_B TEXT NOT NULL,
    explicit_contradiction TEXT NOT NULL,
    decision_consequence TEXT NOT NULL,
    hook_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reasoning_state_id) REFERENCES reasoning_states(id) ON DELETE CASCADE
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tension_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hook_trace_id INTEGER NOT NULL,
    input_contradiction TEXT NOT NULL,
    tension_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hook_trace_id) REFERENCES hook_traces(id) ON DELETE CASCADE
)""")

conn.commit()


# ============================================================
# BUILD FUNCTIONS
# ============================================================

def build_problem(
        problem_name: str,
        core_problem: str,
        system: str,
        causal_mechanism: str,
        failure_mode_A: str,
        failure_mode_B: str,
        failure_mode_A_mechanism: str,
        failure_mode_B_mechanism: str,
        business_impact: str,
        solution_mechanism: str
) -> int:
    cursor.execute("""
        INSERT INTO problems (
            problem_name, core_problem, system, causal_mechanism,
            failure_mode_A, failure_mode_B,
            failure_mode_A_mechanism, failure_mode_B_mechanism,
            business_impact, solution_mechanism
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        problem_name, core_problem, system, causal_mechanism,
        failure_mode_A, failure_mode_B,
        failure_mode_A_mechanism, failure_mode_B_mechanism,
        business_impact, solution_mechanism
    ))
    conn.commit()
    return cursor.lastrowid


def build_reasoning_state(
        problem_id: int,
        system_context: str,
        failure_mode_A: str,
        failure_mode_B: str,
        contextualized_A: str,
        contextualized_B: str,
        contradiction: str,
        decision_consequence: str,
        evidence: list | str,
        valid: bool = False,
        selected: bool = False
) -> int:
    if isinstance(evidence, list):
        evidence_json = json.dumps(evidence)
    else:
        evidence_json = str(evidence)

    cursor.execute("""
        INSERT INTO reasoning_states (
            problem_id, system_context,
            failure_mode_A, failure_mode_B,
            contextualized_A, contextualized_B,
            contradiction, decision_consequence,
            evidence, valid, selected
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        problem_id, system_context,
        failure_mode_A, failure_mode_B,
        contextualized_A, contextualized_B,
        contradiction, decision_consequence,
        evidence_json, int(valid), int(selected)
    ))
    conn.commit()
    return cursor.lastrowid


def build_hook_trace(
        reasoning_state_id: int,
        system_context: str,
        used_A: str,
        used_B: str,
        contextualized_A: str,
        contextualized_B: str,
        explicit_contradiction: str,
        decision_consequence: str,
        hook_text: str
) -> int:
    cursor.execute("""
        INSERT INTO hook_traces (
            reasoning_state_id, system_context,
            used_A, used_B,
            contextualized_A, contextualized_B,
            explicit_contradiction, decision_consequence,
            hook_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        reasoning_state_id, system_context,
        used_A, used_B,
        contextualized_A, contextualized_B,
        explicit_contradiction, decision_consequence,
        hook_text
    ))
    conn.commit()
    return cursor.lastrowid


def build_tension_trace(
        hook_trace_id: int,
        input_contradiction: str,
        compressed_contradiction: str,
        tension_text: str
) -> int:
    cursor.execute("""
        INSERT INTO tension_traces (
            hook_trace_id, input_contradiction,
            compressed_contradiction, tension_text
        ) VALUES (?, ?, ?, ?)
    """, (
        hook_trace_id, input_contradiction,
        compressed_contradiction, tension_text
    ))
    conn.commit()
    return cursor.lastrowid


# ============================================================
# CONTEXT (now requires id)
# ============================================================

@dataclass
class RuntimeContext:
    id: str  # REQUIRED: unique identifier for caching
    industry: str
    company_size: str
    extra: str
    constraints: List[str]

    def __str__(self) -> str:
        return f"ID: {self.id}, Industry: {self.industry}, Size: {self.company_size}, Constraints: {', '.join(self.constraints)}"


# ============================================================
# GENERATORS
# ============================================================

def generate_reasoning_states(
        problem: dict,
        context: RuntimeContext,
        previous_result: Optional[dict] = None,
        failure_reason: str = "",
        temperature: float = 0.3
) -> dict:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS ATTEMPT (FAILED):
{json.dumps(previous_result, indent=2)}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS FOR THIS RETRY:
- Fix the specific issue identified above
- Do NOT repeat the same mistake
- Ensure the output addresses the failure reason directly
"""

    prompt = f"""
You are generating structured reasoning states.

YOU MUST FOLLOW STRICT RULES:

You are given:
- Failure Mode A: {problem['failure_mode_A']}
- Failure Mode B: {problem['failure_mode_B']}

You are also given context:
- Industry: {context.industry}
- Company Size: {context.company_size}
- Constraints: {', '.join(context.constraints)}
- Extra context: {context.extra}

{feedback_section}

TASK:
1. Explain how Failure Mode A appears in THIS context
2. Explain how Failure Mode B appears in THIS context
3. Construct a contradiction between them
4. Define decision consequence (business impact if unresolved)

OUTPUT FORMAT (JSON ONLY):

{{
  "contextualized_A": "",
  "contextualized_B": "",
  "contradiction": "",
  "decision_consequence": "",
  "system": {problem['system']}
}}

RULES:
- DO NOT invent new failure modes
- DO NOT introduce new problems
- MUST use only Failure Mode A and B
- MUST tie everything to provided context
- contextualized_A MUST explicitly describe how "{problem['failure_mode_A']}" manifests in this context
- contextualized_B MUST explicitly describe how "{problem['failure_mode_B']}" manifests in this context
- contextualized_A and contextualized_B must represent conflicting realities
- contradiction MUST directly emerge from A and B (not be independent)
- contradiction MUST clearly express tension (use "while", "but", or equivalent structure)
- decision_consequence MUST describe a decision-level failure
- MUST reference business decisions (evaluation, purchasing, allocation)
- MUST NOT use vague terms like "confusion", "issues", "problems"
"""
    return call_llm(prompt, temperature=temperature)


def generate_subject_line(
        state: dict,
        previous_result: Optional[dict] = None,
        failure_reason: str = "",
        temperature: float = 0.6
) -> dict:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS FAILED ATTEMPT:
{json.dumps(previous_result, indent=2)}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS:
- Fix the issue explicitly
- Do NOT repeat same phrasing structure
"""

    prompt = f"""
You are generating a SUBJECT LINE for a cold email system.

You are given:

Failure Mode A:
{state["failure_mode_A"]}

Failure Mode B:
{state["failure_mode_B"]}

Contradiction:
{state["contradiction"]}

Decision Consequence:
{state["decision_consequence"]}

{feedback_section}

TASK:
Write a subject line that HINTS at the contradiction by expressing ONE side of the failure as a visible pain.

RULES:

1. CORE LOGIC
- Must express a real negative outcome from either Failure Mode A OR B
- Must imply the existence of the opposite failure mode (without stating it)
- Must NOT explain both sides
- Must NOT resolve the contradiction

2. PAIN STYLE
- Must be concrete and observable (not abstract)
- Must feel like something happening in reality
- Must create “this might be true for us” recognition

3. CONTRADICTION HINTING
- Only show ONE side
- The missing side should be implied, not stated

4. STYLE RULES
- Max 10–12 words
- No marketing language
- No vague words: "issue", "problem", "solution", "optimize", "improve"
- No questions
- No em dashes

OUTPUT FORMAT (JSON ONLY):
{{
  "subject_line": ""
}}
"""

    return call_llm(prompt, temperature=temperature)


def generate_hook(
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.3
) -> str:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS HOOK ATTEMPT (FAILED):
{previous_result}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS FOR THIS RETRY:
- Fix the specific issue identified above
- Do NOT repeat the same mistake
"""

    prompt = f"""
You are writing a HOOK for a high-level analytical email.

You are given two underlying patterns:

PATTERN A:
{state["contextualized_A"]}

PATTERN B:
{state["contextualized_B"]}

They create this contradiction:
{state["contradiction"]}

This leads to this consequence:
{state["decision_consequence"]}

{feedback_section}

TASK:
Write a hook that expresses this situation naturally.

CRITICAL RULES:

MEANING:
- You MUST preserve the meaning of Pattern A and Pattern B
- You MUST preserve the contradiction between them
- You MUST preserve the decision consequence

LANGUAGE:
- DO NOT use labels like "Failure Mode A", "Failure Mode B"
- DO NOT repeat input phrasing verbatim unless necessary
- DO NOT expose internal structure or reasoning terms

STYLE:
- Write like an industry observation, not a framework explanation
- Sound like you are describing a real pattern, not a model
- Use natural, fluid language

STRUCTURE:
- Ground in context
- Describe Pattern A naturally
- Describe Pattern B naturally
- Show the conflict
- End with consequence


ANTI-LEAK RULE:
If your output contains phrases like "Failure Mode", "Pattern A", "Pattern B", or references to structured reasoning → INVALID

RULES:
- MUST clearly express the system in context:
  "{state["system"]}"
- The reader should be able to recognize their own system behavior from the description
- DO NOT describe a general industry pattern without tying it back to the core problem
- The hook must make it clear this is about a system that produces outputs (not just “outreach” in general)
- Must not be longer than 1450 characters

Output JSON:
{{
  "hook_text": ""
}}
"""

    result = call_llm(prompt, temperature=temperature)
    return result.get("hook_text", result.get("text", str(result)))


def generate_tension(
        hook: str,
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.3
) -> str:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS TENSION ATTEMPT (FAILED):
{previous_result}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS:
- Fix the issue
- Do NOT repeat the hook
"""

    prompt = f"""
You are writing the TENSION line of a high-level analytical email.

HOOK (already written):
{hook}

UNDERLYING CONTRADICTION:
{state["contradiction"]}

{feedback_section}

TASK:
Write ONE sharp sentence that captures what the situation actually means.

CRITICAL RULES:

- DO NOT repeat the hook
- DO NOT summarize the hook
- DO NOT restate details
- DO NOT explain

INSTEAD:
- Collapse the situation into a single unavoidable insight
- Make the reader see the problem more clearly
- Increase pressure

STYLE:
- Short (1 sentence, max 25 words)
- Precise
- No fluff
- No em dashes
- No storytelling
- No examples

GOOD TENSION DOES:
- Reframe
- Sharpen
- Conclude

BAD TENSION DOES:
- Repeat
- Explain
- Paraphrase

ANTI-PATTERN:
If it sounds like a shorter version of the hook → INVALID

Output JSON:
{{
  "tension_text": ""
}}
"""

    result = call_llm(prompt, temperature=temperature)
    return result.get("tension_text", result.get("text", str(result)))


def generate_authority(
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.3
) -> str:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS AUTHORITY ATTEMPT (FAILED):
{previous_result}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS FOR THIS RETRY:
- Fix the issue identified above
- Do NOT repeat the same mistake
"""

    prompt = f"""
You are writing the AUTHORITY section of a high-level analytical email.

CONTEXT:
The reader has just been shown a real, unresolved tension in their system.

Your role is NOT to explain the problem again.
Your role is NOT to describe a contradiction.

Your role is to introduce a way of thinking that naturally removes the instability described earlier.

You are given:

Underlying situation:
{state["contradiction"]}

Decision pressure:
{state["decision_consequence"]}

Mechanism (internal, do not expose mechanically):
{state["solution_mechanism"]}

{feedback_section}

TASK:
Write a paragraph that:

- Feels like a continuation of the hook, not a new section
- Introduces a structured way of making the system stable
- Shows how consistency replaces instability
- Implies resolution without explicitly naming the contradiction

CRITICAL RULES:

LANGUAGE:
- DO NOT say "contradiction"
- DO NOT say "this resolves"
- DO NOT explain like a system
- DO NOT sound like documentation

STYLE:
- Should feel like insight, not explanation
- Should sound like someone who understands how systems behave in practice
- Should read like “this is how it actually works” not “this is how we solve it”

STRUCTURE:
- Start from instability described earlier
- Introduce control / structure / mechanism naturally
- Show how it creates repeatability
- End in stability (implied, not declared)

ANTI-PATTERN:
If it sounds like:
- a framework explanation
- a product pitch
- or uses meta-language

→ INVALID

Output JSON:
{{
  "authority_text": ""
}}
"""

    result = call_llm(prompt, temperature=temperature)
    return result.get("authority_text", result.get("text", str(result)))


def generate_cta(
        state: dict,
        previous_result: Optional[str] = None,
        failure_reason: str = "",
        temperature: float = 0.3
) -> str:
    feedback_section = ""
    if previous_result is not None and failure_reason:
        feedback_section = f"""
PREVIOUS CTA ATTEMPT (FAILED):
{previous_result}

FAILURE REASON:
{failure_reason}

INSTRUCTIONS:
- Fix the issue
- Do NOT repeat the same mistake
"""

    prompt = f"""
You are writing a CTA for a structured cold email.

Context:
{state["system_context"]}

Decision Consequence:
{state["decision_consequence"]}

{feedback_section}

TASK:
Write a CTA that feels like a natural continuation of the diagnosis, not a sales ask.

The CTA must:
1. Check if the reader is experiencing the problem (binary contrast)
2. Use the SAME language/mechanism described earlier (e.g., drift, fade, break, blur)
3. Lightly ask (as a question that's easy to answer) a discussion ONLY if the problem exists

CRITICAL RULES:
- MUST refer to the reader’s system (e.g., "your system", "your setup")
- MUST include a contrast (X vs Y)
- MUST reuse concrete mechanism words from the problem (e.g., "drift", "fade", "blur", "break")
- MUST include a conditional invite ("if it does", "if it fades", "if that's happening")
- MUST use soft, peer-level language ("worth comparing notes", "open to a quick chat")
- MUST NOT sound like a pitch or meeting request
- MUST NOT use generic phrases like "schedule a call", "book time", "let's connect"
- MUST NOT exceed 25 words


STYLE:
- Calm, observational, diagnostic tone
- Feels like a peer noticing a pattern, not selling a solution
- The invite should feel secondary to the observation

GOOD OUTPUT SHAPES:
- "Is your system holding steady, or does it fade after the first batch? If it fades, worth comparing notes?"
- "Does your system stay differentiated, or drift into the same SaaS language? If it drifts, open to a quick chat?"
- "Is your setup consistent, or does it blur as you scale? If it blurs, happy to compare notes."

BAD:
- "Can we schedule a call?"
- "Book a meeting"
- "Let me know if you're interested"
- Any CTA that does not reference the problem mechanism

Output JSON with key "cta_text".
"""

    result = call_llm(prompt, temperature=temperature)
    return result.get("cta_text", result.get("text", str(result)))


# ============================================================
# LLM BASED VALIDATION HELPERS
# ============================================================

def llm_check_opposition(A: str, B: str) -> tuple[bool, str]:
    prompt = f"""
You are validating whether two statements are in real opposition.

A:
{A}

B:
{B}

Rules:
- They must describe conditions that cannot both work together cleanly
- One must undermine, distort, or invalidate the other
- Reject if they are just different or unrelated
- Reject if they can coexist without tension

Output JSON:
{{"valid": true/false, "reason": ""}}
"""
    result = call_llm(prompt, temperature=0.1)
    return result.get("valid", False), result.get("reason", "")


def llm_check_derivation(A: str, B: str, contradiction: str) -> tuple[bool, str]:
    prompt = f"""
You are validating reasoning construction.

A:
{A}

B:
{B}

Contradiction:
{contradiction}

Rules:
- The contradiction must be the unavoidable result of A and B both being true
- It must NOT introduce new ideas outside A or B
- It must explicitly capture the tension between A and B
- If A and B can exist without leading to this contradiction → reject

Output JSON:
{{"valid": true/false, "reason": ""}}
"""
    result = call_llm(prompt, temperature=0.1)
    return result.get("valid", False), result.get("reason", "")


def llm_check_consequence(contradiction: str, consequence: str) -> tuple[bool, str]:
    prompt = f"""
You are validating causal reasoning in a business decision context.

Contradiction:
{contradiction}

Consequence:
{consequence}

Rules:
- The consequence must occur because the contradiction is unresolved
- It must describe a decision-level failure (evaluation, choice, prioritization, trust)
- Reject vague outcomes (e.g., confusion, inefficiency)
- Reject indirect or weak links

Output JSON:
{{"valid": true/false, "reason": ""}}
"""
    result = call_llm(prompt, temperature=0.1)
    return result.get("valid", False), result.get("reason", "")


# ============================================================
# VALIDATORS
# ============================================================

def validate_reasoning_state(state: dict) -> ValidationResult:
    if not isinstance(state, dict):
        return ValidationResult.invalid("State must be a dictionary", state)

    required = ["contextualized_A", "contextualized_B", "contradiction", "decision_consequence"]
    missing = [k for k in required if not state.get(k)]
    if missing:
        return ValidationResult.invalid(f"Missing fields: {missing}", state)

    A = state["contextualized_A"]
    B = state["contextualized_B"]
    contradiction = state["contradiction"]
    consequence = state["decision_consequence"]

    # === 1. A vs B must be in real opposition ===
    opp_ok, opp_reason = llm_check_opposition(A, B)
    if not opp_ok:
        return ValidationResult.invalid(f"A/B not in opposition: {opp_reason}", state)

    # === 2. Contradiction must be derived from A + B ===
    derive_ok, derive_reason = llm_check_derivation(A, B, contradiction)
    if not derive_ok:
        return ValidationResult.invalid(f"Contradiction invalid: {derive_reason}", state)

    # === 3. Consequence must follow from contradiction (decision-level) ===
    cons_ok, cons_reason = llm_check_consequence(contradiction, consequence)
    if not cons_ok:
        return ValidationResult.invalid(f"Consequence invalid: {cons_reason}", state)

    return ValidationResult.valid()


def validate_subject_line(subject: str, state: dict) -> ValidationResult:
    if not isinstance(subject, str):
        return ValidationResult.invalid("Subject is not a string", subject)

    words = subject.split()

    # --- STRUCTURE RULES ---
    if len(words) > 12:
        return ValidationResult.invalid("Too long (>12 words)", subject)

    if len(words) < 3:
        return ValidationResult.invalid("Too short", subject)

    banned = [
        "improve", "optimize", "boost", "solution",
        "increase", "scale", "growth", "fix", "issue", "problem"
    ]

    lowered = subject.lower()

    for b in banned:
        if b in lowered:
            return ValidationResult.invalid(f"Contains banned word: {b}", subject)

    if "?" in subject:
        return ValidationResult.invalid("Contains question", subject)

    if "—" in subject:
        return ValidationResult.invalid("Contains em dash", subject)

    # --- SEMANTIC VALIDATION (LLM) ---
    is_valid, reason = llm_validate_subject(subject, state)

    if not is_valid:
        return ValidationResult.invalid(f"Semantic failure: {reason}", subject)

    return ValidationResult.valid()


def validate_hook(hook: str, state: dict) -> ValidationResult:
    if not isinstance(hook, str):
        return ValidationResult.invalid("Hook is not a string", hook)

    if "—" in hook:
        return ValidationResult.invalid("Contains em dash", hook)

    if len(hook) < 50:
        return ValidationResult.invalid("Hook is too short (< 50 chars)", hook)

    if len(hook) > 1500:
        return ValidationResult.invalid("Hook is too long (> 1500 chars), make it concise", hook)

    is_valid, reason = llm_validate("hook", hook, state)

    if not is_valid:
        return ValidationResult.invalid(f"Hook semantic failure: {reason}", hook)

    return ValidationResult.valid()


def validate_tension(tension: str, state: dict) -> ValidationResult:
    if not isinstance(tension, str):
        return ValidationResult.invalid("Tension is not a string", tension)

    if len(tension.split()) > 25:
        return ValidationResult.invalid("Tension too long", tension)

    if "—" in tension:
        return ValidationResult.invalid("Tension contains em dash", tension)

    # LLM semantic validation
    is_valid, reason = llm_validate("tension", tension, state)

    if not is_valid:
        return ValidationResult.invalid(f"Tension semantic failure: {reason}", tension)

    return ValidationResult.valid()


def validate_authority(authority: str, state: dict) -> ValidationResult:
    if not isinstance(authority, str):
        return ValidationResult.invalid("Authority is not a string", authority)

    if "—" in authority:
        return ValidationResult.invalid("Contains em dash", authority)

    if len(authority) < 50:
        return ValidationResult.invalid("Authority is too short", authority)

    is_valid, reason = llm_validate("authority", authority, state)

    if not is_valid:
        return ValidationResult.invalid(f"Authority semantic failure: {reason}", authority)

    return ValidationResult.valid()


def validate_cta(cta: str, state: dict) -> ValidationResult:
    if not isinstance(cta, str):
        return ValidationResult.invalid("CTA is not a string", cta)

    if len(cta.split()) > 40:
        return ValidationResult.invalid("CTA too long", cta)

    is_valid, reason = llm_validate_cta(cta, state)

    if not is_valid:
        return ValidationResult.invalid(f"CTA semantic failure: {reason}", cta)

    return ValidationResult.valid()


# ================================
# LLM VALIDATORS
# ================================
def llm_validate_subject(subject: str, state: dict) -> tuple[bool, str]:
    prompt = f"""
You are validating a cold email SUBJECT LINE.

STATE:
- Failure Mode A: {state["failure_mode_A"]}
- Failure Mode B: {state["failure_mode_B"]}
- Contradiction: {state["contradiction"]}
- Decision Consequence: {state["decision_consequence"]}

SUBJECT:
{subject}

VALIDATION RULES:

1. CONTRADICTION HINTING
- Does it express ONE failure mode as a real-world pain?
- Does it implicitly suggest the other failure mode exists?

2. SPECIFICITY
- Is it concrete and observable?
- Or is it generic business language?

3. PAIN QUALITY
- Does it feel like a real operational symptom?
- Or marketing abstraction?

4. DRIFT CHECK
- Reject if it fully explains the system
- Reject if it becomes generic SaaS messaging

5. OPENABILITY TEST
- Would a reader think: "this might be happening in my system"?

OUTPUT JSON:
{{
  "valid": true/false,
  "reason": ""
}}
"""

    result = call_llm(prompt, temperature=0.1)
    return result.get("valid", False), result.get("reason", "")


def llm_validate_cta(content: str, state: dict) -> tuple[bool, str]:
    prompt = f"""
You are validating a cold email CTA.

STATE CONTEXT:
- Failure Mode A: {state["failure_mode_A"]}
- Failure Mode B: {state["failure_mode_B"]}
- Contradiction: {state["contradiction"]}

CONTENT:
{content}

VALID CTA MUST:
1. Refer to the problem situation (A vs B or equivalent tension)
2. Include a conditional invitation ("if", "if so", "if it does")
3. Match the tone of diagnosis, not sales outreach

INVALID IF:
- It sounds like a sales request (call, demo, meeting)
- It is generic and not tied to the problem situation
- It breaks tone consistency with the email body

Return JSON:
{{
  "valid": true/false,
  "reason": "brief"
}}
"""

    result = call_llm(prompt, temperature=0.1)

    if isinstance(result, dict):
        return result.get("valid", False), result.get("reason", "no reason")

    return False, "invalid LLM response"


def llm_validate(stage: str, content: str, state: dict) -> tuple[bool, str]:
    """
    LLM-based semantic validator.
    Returns (is_valid, reason)
    """

    prompt = f"""
You are a strict validation system for a structured cold email generation pipeline.

You are evaluating a {stage}.

You are given:

STATE:
- Failure Mode A: {state["failure_mode_A"]}
- Failure Mode B: {state["failure_mode_B"]}
- Contradiction: {state["contradiction"]}
- Decision Consequence: {state["decision_consequence"]}
- Solution Mechanism: {state.get("solution_mechanism", "")}

CONTENT TO VALIDATE:
{content}

TASK:
Check if the content correctly preserves meaning and logical constraints.

VALIDATION CRITERIA:

1. Semantic Preservation
- Does it preserve BOTH Failure Mode A and B accurately?
- Does it preserve contradiction meaning?

2. Logical Alignment
- Does it express the correct relationship (A vs B conflict)?

3. Stage-Specific Rules
- Hook: must express contradiction + consequence
- Tension: must compress contradiction only
- Authority: must resolve contradiction via solution mechanism


4. No Drift Rule
- Reject if it introduces new ideas not grounded in state

OUTPUT FORMAT (STRICT JSON):
{{
  "valid": true/false,
  "reason": "short explanation",
  "score": 0.0-1.0
}}
"""

    result = call_llm(prompt, temperature=0.1)

    if isinstance(result, dict):
        return result.get("valid", False), result.get("reason", "no reason")

    return False, "invalid LLM response"


# ============================================================
# BLUEPRINT ORCHESTRATOR — WITH CONTEXT ID CACHING
# ============================================================

def blueprint(problem: dict, context: RuntimeContext) -> dict:
    results = {}

    # --- STEP 1: REASONING STATE ---
    print("\n=== GENERATING REASONING STATES ===")
    reasoning_state, rs_history = generate_with_retry(
        generator_fn=generate_reasoning_states,
        validator_fn=validate_reasoning_state,
        generator_args=(problem, context),
        generator_kwargs={"temperature": 0.8},
        max_retries=5,
        context_id=context.id,
        stage="reasoning_state"
    )
    print(f"Reasoning state generated after {len(rs_history)} attempts")
    results["reasoning_state"] = reasoning_state

    state = {
        "system_context": context.industry,
        **reasoning_state,
        "failure_mode_A": problem["failure_mode_A"],
        "failure_mode_B": problem["failure_mode_B"],
        "solution_mechanism": problem["solution_mechanism"]
    }

    print("\n=== GENERATING SUBJECT LINE ===")

    subject, sl_history = generate_with_retry(
        generator_fn=generate_subject_line,
        validator_fn=lambda s: validate_subject_line(s["subject_line"], state),
        generator_args=(state,),
        generator_kwargs={"temperature": 0.7},
        max_retries=5,
        context_id=context.id,
        stage="subject_line"
    )
    print(f"subject line generated after {len(sl_history)} attempts")
    results["subject_line"] = subject

    # --- STEP 2: HOOK ---
    print("\n=== GENERATING HOOK ===")
    hook, hook_history = generate_with_retry(
        generator_fn=generate_hook,
        validator_fn=lambda h: validate_hook(h, state),
        generator_args=(state,),
        generator_kwargs={"temperature": 0.5},
        max_retries=5,
        context_id=context.id,
        stage="hook"
    )
    print(f"Hook generated after {len(hook_history)} attempts")
    results["hook"] = hook
    state["hook"] = hook

    # --- STEP 3: TENSION ---
    print("\n=== GENERATING TENSION ===")
    tension, tension_history = generate_with_retry(
        generator_fn=generate_tension,
        validator_fn=lambda t: validate_tension(t, state),
        generator_args=(hook, state),
        generator_kwargs={"temperature": 0.5},
        max_retries=5,
        context_id=context.id,
        stage="tension"
    )
    print(f"Tension generated after {len(tension_history)} attempts")
    results["tension"] = tension
    state["tension"] = tension

    # --- STEP 4: AUTHORITY ---
    print("\n=== GENERATING AUTHORITY ===")
    authority, auth_history = generate_with_retry(
        generator_fn=generate_authority,
        validator_fn=lambda a: validate_authority(a, state),
        generator_args=(state,),
        generator_kwargs={"temperature": 0.8},
        max_retries=5,
        context_id=context.id,
        stage="authority"
    )
    print(f"Authority generated after {len(auth_history)} attempts")
    results["authority"] = authority
    state["authority"] = authority

    # --- STEP 5: CTA ---
    print("\n=== GENERATING CTA ===")
    cta, cta_history = generate_with_retry(
        generator_fn=generate_cta,
        validator_fn=lambda c: validate_cta(c, state),
        generator_args=(state,),
        generator_kwargs={"temperature": 0.3},
        max_retries=5,
        context_id=context.id,
        stage="cta"
    )
    print(f"CTA generated after {len(cta_history)} attempts")
    results["cta"] = cta
    state["cta"] = cta

    # --- STEP 6: GLOBAL COHERENCE CHECK ---
    print("\n=== VALIDATING GLOBAL COHERENCE ===")
    coherence = validate_global_coherence(hook, tension, authority, cta, state)
    if coherence.is_valid:
        print("✓ Global coherence PASSED")
    else:
        print(f"✗ Global coherence FAILED: {coherence.reason}")

    # --- STEP 7: FINAL ASSEMBLY ---
    print("\n=== FINAL ASSEMBLY ===")
    final_email = final_assembly_stage(hook, tension, authority, cta)
    results["final_email"] = final_email
    print(final_email)

    return results


# ============================================================
# GLOBAL COHERENCE & FINAL ASSEMBLY
# ============================================================

def validate_global_coherence(hook: str, tension: str, authority: str, cta: str, state: dict) -> ValidationResult:
    if not all(isinstance(x, str) for x in [hook, tension, authority, cta]):
        return ValidationResult.invalid("One or more stages are not strings", None)

    hook_emb = embed(hook)
    tension_emb = embed(tension)
    hook_to_tension = cosine_similarity(hook_emb, tension_emb)
    if hook_to_tension < 0.55:
        return ValidationResult.invalid(f"Hook→Tension coherence too low ({hook_to_tension:.2f})", None)

    authority_emb = embed(authority)
    tension_to_authority = cosine_similarity(tension_emb, authority_emb)
    if tension_to_authority < 0.55:
        return ValidationResult.invalid(f"Tension→Authority coherence too low ({tension_to_authority:.2f})", None)

    cta_emb = embed(cta)
    authority_to_cta = cosine_similarity(authority_emb, cta_emb)
    if authority_to_cta < 0.50:
        return ValidationResult.invalid(f"Authority→CTA coherence too low ({authority_to_cta:.2f})", None)

    full_chain = " ".join([hook, tension, authority, cta])
    chain_emb = embed(full_chain)
    local_avg = (hook_to_tension + tension_to_authority + authority_to_cta) / 3
    global_coherence = cosine_similarity(chain_emb, embed(state["contradiction"]))
    if local_avg < 0.6:
        return ValidationResult.invalid(f"Low local flow coherence (avg={local_avg:.2f})", None)
    if global_coherence < 0.4:
        return ValidationResult.invalid(f"Email not anchored to contradiction (score={global_coherence:.2f})", None)
    return ValidationResult.valid()


def final_assembly_stage(hook: str, tension: str, authority: str, cta: str) -> dict:
    prompt = f"""
You are the final assembly stage of a constrained persuasion system.

You are NOT allowed to introduce new meaning.

You are ONLY allowed to improve flow.

INPUT COMPONENTS:

HOOK:
{hook}

TENSION:
{tension}

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
- Maintain Hook → Tension → Authority → CTA order

STRICT:
If meaning changes → invalid output

Output JSON:
{{
  "email": ""
}}
"""
    result = call_llm(prompt)
    return result.get("email", result.get("text", str(result)))


# ============================================================
# EXAMPLE DATA & RUN
# ============================================================

drop_all_tables()

problem = {
    "problem_name": "llm_output_instability_in_cold_outreach",
    "system": "automated outreach system",
    "core_problem": "LLM-generated cold emails produce inconsistent quality over time, forcing repeated manual prompt adjustments to maintain acceptable personalization",
    "causal_mechanism": "The system lacks structured grounding and control, so outputs depend on probabilistic generation rather than stable, reusable context representations, leading to variability in tone, specificity, and relevance",
    "failure_mode_A": "Temporary high-quality outputs that degrade into generic messaging",
    "failure_mode_B": "Endless prompt iteration loop without achieving stable performance",
    "failure_mode_A_mechanism": "Initial outputs benefit from favorable sampling or implicit alignment, but without structured retrieval or constraints, the model reverts to high-probability generic patterns over repeated generations",
    "failure_mode_B_mechanism": "the team attempt to compensate for instability by continuously modifying prompts, which introduces new variability instead of fixing the underlying lack of system control",
    "contradiction": "drop in personalisation leads the team to change/tweak prompts and add more context in order to restore specificity which increases variance which creates more unpredictability and drop in personalisation",
    "business_impact": "Significant time loss in prompt tweaking, inability to scale outreach reliably, reduced response rates due to inconsistent message quality",
    "solution_mechanism": "Replace single-pass LLM generation with a constrained, multi-stage system where outputs are produced within a structured representation of the problem, expanded into multiple candidate variants, and then filtered through a strict validation layer that enforces semantic, contextual, and structural correctness. Final outputs are not accepted based on plausibility but on whether they satisfy predefined constraints and outperform alternatives under evaluation, effectively removing randomness from final decision-making and turning generation into controlled selection within a bounded solution space",
    "solution_actor": "Ai Automation Engineer specialised in building automated outreach systems"
}
# {
#   "problem_id": "a453a210-dfe6-49e5-9267-e8937d0817eb",
#   "context_id": 1
# }

context = RuntimeContext(
    id="b2b-saas-growth-001",
    industry="B2B SaaS",
    company_size="10–200 employees",
    extra="the company is a start up and trying to expand aggressively using automated llm generated outreach system. They were funded recently and are looking to grow with ai and a lean team",
    constraints=[
        "Low tolerance for irrelevant or generic outreach due to high inbound noise and prior exposure to automated email",
        "Pressure to consistently generate qualified pipeline and hit aggressive growth targets",
        "Highly saturated market with many similar tools, leading to strong skepticism and differentiation challenges"
    ]
)

if __name__ == "__main__":
    # First run — hits API, caches validated results
    print("=== FIRST RUN ===")
    result1 = blueprint(problem, context)
    # print(json.dumps({k: str(v)[:400] for k, v in result1.items()}, indent=2))

    hook = result1["hook"]
    tension = result1["tension"]
    authority = result1["authority"]
    cta = result1["cta"]
    state = result1["reasoning_state"]
    subject = result1["subject_line"]

    print(f"\n{subject}")

    # print("\n{state}")
#
# print(f"\nhook: {result1['hook']}")
# print(f'\nauthority: {result1["authority"]}')

# print(final_assembly_stage(hook, tension, authority, cta))

## Second run — same context ID, all stages cache-hit
# print("\n=== SECOND RUN (should be all cache hits) ===")
# result2 = blueprint(problem, context)
# print(json.dumps({k: str(v)[:100] for k, v in result2.items()}, indent=2))
#
## Clear cache and run again — forces fresh API calls
# print("\n=== AFTER CACHE CLEAR ===")
# clear_validated_cache()
# result3 = blueprint(problem, context)
# print(json.dumps({k: str(v)[:100] for k, v in result3.items()}, indent=2))