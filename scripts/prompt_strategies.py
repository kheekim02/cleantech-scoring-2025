"""
Prompt Strategies Module for CTO Diligence Engine.
Implements:
- Strategy A: Zero-Shot Strict Constraint (Default)
- Strategy B: Forced Chain-of-Thought (Quotes -> Reasoning -> Score)
- Strategy C: Multi-Agent Debate (Extractor -> Critic -> Arbiter)
"""

import json
import re
import requests
import time
from typing import Dict, Any, List, Optional

LLM_API_URL = "http://127.0.0.1:46093/v1/chat/completions"

DEFAULT_RULES = [
    "1. Nullification on Zero: If you assign a score of 0.0, or if there is no explicit matching text, `citation` MUST be `null`. NEVER invent a citation.",
    "2. Score-Rationale Alignment (CRITICAL): Your `predicted_val` MUST perfectly match your `rationale`. If your rationale states \"The document does not explicitly state X\", you CANNOT award a 1.0. You must award a 0.0.",
    "3. Binary Existence vs. Depth: For simple yes/no questions (e.g. \"Is there a description of the target market?\"), if the founder provides ANY valid description (e.g., naming a specific industry like 'cold storage logistics'), you MUST award a 1.0. Do not penalize them for lacking deep metrics (like TAM/SAM size) unless the question explicitly asks for those metrics.",
    "4. Descriptive Deficits (Show Your Work): Your `rationale` MUST summarize the closest relevant information the founder actually provided (using concrete quotes/examples from the text) before stating whether it passes or fails. Never use generic filler like 'lacks concrete evidence'. For example, if they provided a list of competitors instead of a matrix, state: 'The founder listed competitors X and Y, but...'.",
    "5. Framework Agnosticism (DO NOT FAIL FOR LACK OF GRIDS): The rubric frequently asks for specific frameworks like \"BCG grid\" or \"benefits matrix\". YOU MUST TREAT THESE AS NON-EXCLUSIVE EXAMPLES. If the founder provides ANY competitor analysis or feature comparison, YOU MUST SCORE 1.0 IMMEDIATELY. NEVER PENALIZE A STARTUP FOR NOT DRAWING A LITERAL GRID OR MATRIX. NEVER write \"they didn't provide a matrix\" in your rationale if they provided a list of competitive features!",
    "6. Mathematical Deduction (No Literalism): You must use basic logic. If the criteria asks for a minimum threshold $X$, and the startup explicitly states a quantified metric $Y$ where $Y > X$, you must award the point.",
    "7. Clean Narrative Only: Do NOT quote competition questions, instructions, or template placeholders.",
    "8. Abstract Phrasing Agnosticism (CRITICAL): If you find the specific components required by the rubric options in the text, you MUST award the points regardless of whether the founder summarizes those components with the abstract terminology used in the question. For example, if the question asks for 'breadth of capabilities' and the founder lists 'Technical, Sales, and Finance' teams, you MUST award the point. Do not fail them for failing to use the word 'breadth'. Never write 'does not explicitly state the breadth' if the departments are clearly listed."
]

DEFAULT_QUESTION_REWRITES = {
    "BC_Q1": "Does the document provide a concrete, specific value proposition highlighting quantifiable customer cost savings or environmental impact?",
    "BC_Q4": "Does the document provide specific, concrete details for the core business model pillars (Key Partners, Value Propositions, Customer Segments, Cost Structure, Revenue Streams)?",
    "BC_Q5": "Does the document provide specific, concrete details for the operational business model connectors (Key Activities, Key Resources, Customer Relationships, Channels)?"
}

def query_llm(prompt: str, temperature: float = 0.0, max_tokens: int = 800, timeout: int = 120) -> Optional[str]:
    for attempt in range(3):
        try:
            resp = requests.post(LLM_API_URL, json={
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content'].strip()
        except Exception:
            time.sleep(2)
    return None

def clean_citation(cit: Optional[str]) -> Optional[str]:
    if not cit:
        return None
    cit_lower = cit.lower().strip()
    if (cit_lower.startswith("the document does not") or
        cit_lower.startswith("the founder does not") or
        cit_lower.startswith("no explicit mention") or
        cit_lower == "null" or
        cit_lower == "none"):
        return None
    return cit

# ==========================================
# STRATEGY A: Zero-Shot Strict Constraint
# ==========================================
def execute_strategy_a(q: Dict[str, Any], doc_text: str, rules: Optional[List[str]] = None, rewrites: Optional[Dict[str, str]] = None, few_shot_examples: Optional[str] = None) -> Dict[str, Any]:
    q_id = q.get('new_q_id', q.get('q_id'))
    rules = rules or DEFAULT_RULES
    rewrites = rewrites or DEFAULT_QUESTION_REWRITES

    q_text = rewrites.get(q_id, q['text'])
    q_simple = {
        'q_id': q_id,
        'category': q.get('cat_code'),
        'text': q_text,
        'options': [o['val'] for o in q['options']]
    }

    rules_str = "\n".join(rules)
    few_shot_block = f"\n<example_of_correct_grading>\n{few_shot_examples}\n</example_of_correct_grading>\n" if few_shot_examples else ""

    prompt = f"""You are a highly skeptical, rigorous financial and technical auditor conducting strict due diligence on a startup. Your default position is that the startup has failed to meet the criteria unless proven otherwise by concrete, specific evidence.
Evaluate this single criterion against the provided clean document text.
Output a valid JSON object. Do NOT wrap in markdown or backticks.

<document>
{doc_text[:12000]}
</document>

<question>
{json.dumps(q_simple, indent=2)}
</question>
{few_shot_block}
Output exactly one JSON object with these keys:
"q_id": "{q_id}"
"evidence_strength": "Explicit", "Implicit", or "Weak/Fluff"
"rationale": "A 2-4 sentence critique. MUST follow the 'Descriptive Deficits' rule below. Evaluate this BEFORE the score."
"missing_information": "If you score 0.0 or 0.5, explicitly state what exact data or metric the founder forgot to include. Otherwise, output null."
"predicted_val": exactly one numeric value chosen from the provided options array
"confidence": float between 0.0 and 1.0 representing certainty
"citation": An exact verbatim quote of 1 to 2 COMPLETE sentences from the document providing the full context for your verdict.

HARD FAIL CONSTRAINTS & STRICT GRADING RULES:
{rules_str}
"""
    raw_txt = query_llm(prompt)
    res = {'q_id': q_id, 'evidence_strength': None, 'rationale': None, 'missing_information': None, 'predicted_val': None, 'confidence': None, 'citation': None}

    if raw_txt:
        match = re.search(r'\{.*\}', raw_txt, re.DOTALL)
        if match:
            try:
                j = json.loads(match.group(0))
                cit = clean_citation(j.get('verbatim_citation', j.get('citation')))
                res = {
                    'q_id': q_id,
                    'evidence_strength': j.get('evidence_strength'),
                    'rationale': j.get('rationale'),
                    'missing_information': j.get('missing_information'),
                    'predicted_val': j.get('predicted_val'),
                    'confidence': j.get('confidence'),
                    'citation': cit
                }
            except Exception:
                pass
    return res

# ==========================================
# STRATEGY B: Forced Chain-of-Thought
# ==========================================
def execute_strategy_b(q: Dict[str, Any], doc_text: str, rules: Optional[List[str]] = None, rewrites: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    q_id = q.get('new_q_id', q.get('q_id'))
    rules = rules or DEFAULT_RULES
    rewrites = rewrites or DEFAULT_QUESTION_REWRITES

    q_text = rewrites.get(q_id, q['text'])
    q_simple = {
        'q_id': q_id,
        'category': q.get('cat_code'),
        'text': q_text,
        'options': [o['val'] for o in q['options']]
    }
    rules_str = "\n".join(rules)

    prompt = f"""You are a skeptical auditor conducting due diligence on a startup.
Follow a strict Step-by-Step Chain-of-Thought process before reaching your score.
Output a valid JSON object without markdown or backticks.

<document>
{doc_text[:12000]}
</document>

<question>
{json.dumps(q_simple, indent=2)}
</question>

Output exactly one JSON object with these keys in this exact order:
1. "extracted_quotes": [array of 1-3 exact verbatim quotes from the document directly addressing the question. Output [] if no evidence exists.]
2. "reasoning": "A 2-3 sentence evaluation explaining whether the extracted quotes fully satisfy the rubric options, noting any omissions."
3. "predicted_val": exactly one numeric value chosen from the provided options array
4. "confidence": float between 0.0 and 1.0 representing certainty
5. "citation": "The single most representative quote from extracted_quotes, or null if extracted_quotes is empty."

RULES:
{rules_str}
"""
    raw_txt = query_llm(prompt)
    res = {'q_id': q_id, 'evidence_strength': None, 'rationale': None, 'missing_information': None, 'predicted_val': None, 'confidence': None, 'citation': None}

    if raw_txt:
        match = re.search(r'\{.*\}', raw_txt, re.DOTALL)
        if match:
            try:
                j = json.loads(match.group(0))
                quotes = j.get('extracted_quotes', [])
                cit = quotes[0] if quotes else j.get('citation')
                cit = clean_citation(cit)
                val = j.get('predicted_val')
                if val == 0.0:
                    cit = None

                res = {
                    'q_id': q_id,
                    'evidence_strength': "Explicit" if (quotes and val and val > 0.5) else ("Implicit" if quotes else "Weak/Fluff"),
                    'rationale': j.get('reasoning', j.get('rationale')),
                    'missing_information': None if val == 1.0 else "Detailed metrics or required rubric fields omitted.",
                    'predicted_val': val,
                    'confidence': j.get('confidence'),
                    'citation': cit
                }
            except Exception:
                pass
    return res

# ==========================================
# STRATEGY C: Multi-Agent Debate
# ==========================================
def execute_strategy_c(q: Dict[str, Any], doc_text: str, rewrites: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    q_id = q.get('new_q_id', q.get('q_id'))
    rewrites = rewrites or DEFAULT_QUESTION_REWRITES
    q_text = rewrites.get(q_id, q['text'])
    options = [o['val'] for o in q['options']]

    # Call 1: Extractor Agent
    prompt_extract = f"""You are the Extractor Agent. Your ONLY job is to search the document and extract exact, verbatim quotes relevant to this question.
Question: {q_text}

<document>
{doc_text[:12000]}
</document>

Output valid JSON:
{{"relevant_quotes": ["quote 1", "quote 2"], "has_evidence": true/false}}
"""
    raw_1 = query_llm(prompt_extract, max_tokens=600)
    quotes = []
    if raw_1:
        m1 = re.search(r'\{.*\}', raw_1, re.DOTALL)
        if m1:
            try:
                quotes = json.loads(m1.group(0)).get('relevant_quotes', [])
            except Exception:
                pass

    # Call 2: Critic Agent
    prompt_critic = f"""You are the Critic Agent. Evaluate whether the extracted evidence fulfills the rubric criteria.
Question: {q_text}
Allowed Options: {options}
Extracted Evidence:
{json.dumps(quotes, indent=2)}

Output valid JSON:
{{"critique": "2-3 sentences analyzing depth, completeness, and adherence to rubric", "recommended_val": <numeric value from allowed options>}}
"""
    raw_2 = query_llm(prompt_critic, max_tokens=600)
    critique = ""
    rec_val = 0.0
    if raw_2:
        m2 = re.search(r'\{.*\}', raw_2, re.DOTALL)
        if m2:
            try:
                j2 = json.loads(m2.group(0))
                critique = j2.get('critique', '')
                rec_val = j2.get('recommended_val', 0.0)
            except Exception:
                pass

    # Call 3: Arbiter Agent
    prompt_arbiter = f"""You are the Lead Diligence Arbiter. Finalize the score and rationale.
Question: {q_text}
Allowed Options: {options}
Quotes: {json.dumps(quotes)}
Critic Analysis: {critique} (Recommended: {rec_val})

Output valid JSON:
{{
  "predicted_val": <numeric value from allowed options>,
  "confidence": <float 0.0-1.0>,
  "rationale": "Clear, grounded 2-3 sentence final judgment referencing founder data",
  "citation": "Best verbatim quote or null if score is 0.0"
}}
"""
    raw_3 = query_llm(prompt_arbiter, max_tokens=600)
    res = {'q_id': q_id, 'evidence_strength': None, 'rationale': None, 'missing_information': None, 'predicted_val': None, 'confidence': None, 'citation': None}
    if raw_3:
        m3 = re.search(r'\{.*\}', raw_3, re.DOTALL)
        if m3:
            try:
                j3 = json.loads(m3.group(0))
                val = j3.get('predicted_val')
                cit = clean_citation(j3.get('citation'))
                if val == 0.0:
                    cit = None
                res = {
                    'q_id': q_id,
                    'evidence_strength': "Explicit" if (quotes and val and val > 0.5) else "Weak/Fluff",
                    'rationale': j3.get('rationale', critique),
                    'missing_information': None if val == 1.0 else "Specific required metric or detail missing.",
                    'predicted_val': val,
                    'confidence': j3.get('confidence', 0.9),
                    'citation': cit
                }
            except Exception:
                pass
    return res
