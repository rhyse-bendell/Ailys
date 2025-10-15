# tasks/lit_search_keywords.py
import os
import datetime
import json
import re
from typing import Optional, Dict, List

from core.lit.utils import (
    make_run_id, run_dirs, write_csv_row, read_single_row_csv, from_list
)

# IMPORTANT: import the MODULE, not a function copy.
# This guarantees we talk to the same queue object the GUI uses.
import core.approval_queue as approvals


CSV_HEADER = [
    "run_id", "timestamp_utc", "researcher", "prompt", "clarifications",
    "seed_terms|;|", "expanded_terms|;|", "boolean_queries|;|", "notes"
]

SYSTEM_HINT = (
    "You are Ailys, a research assistant focused on turning free-text literature needs into "
    "actionable search artifacts for academic engines (OpenAlex, Crossref, arXiv, PubMed, "
    "Semantic Scholar). "
    "Your job:\n"
    "1) Extract core 'seed terms' (compact, generalizable concepts).\n"
    "2) Expand with synonyms, near-neighbors, controlled-vocabulary terms (e.g., MeSH), acronyms, "
    "spelling variants (US/UK), hyphenation variants (e.g., co-creation vs cocreation), morphological "
    "variants (stems/wildcards like collaborat*), and cross-disciplinary labels.\n"
    "3) Produce 3–6 Boolean query variants covering three tiers:\n"
    "   • Precision (narrow, high signal)\n"
    "   • Balanced (trade-off)\n"
    "   • Recall (broader, exploratory)\n"
    "   Each query must be syntactically valid for common academic engines (quotes for phrases, "
    "AND/OR/NOT, parentheses, wildcards * when supported). Include inclusion/exclusion logic when helpful.\n\n"
    "Quality rules:\n"
    "- Be exhaustive – do not omit nuanced concepts.\n"
    "- Cover high-pressure domains explicitly where relevant: military, first responders, healthcare.\n"
    "- Prefer field-agnostic wording unless niche jargon is justified; if niche is needed, include both the niche and general term.\n"
    "- Include both conceptual and operational/measurement terms (e.g., 'shared mental models' and 'SMM', 'joint attention', 'after-action review').\n"
    "- Add common abbreviations and expansions (HAI, HRI, SMM, AAR).\n"
    "- Add negative keywords for typical confounds (e.g., education level filters if not relevant; consumer social media if off-topic).\n"
    "- Never invent references or IDs.\n"
    "- Output MUST be valid JSON exactly matching the schema below.\n\n"
    "Output schema (JSON):\n"
    "{\n"
    "  'seed_terms': string[10..20],\n"
    "  'expanded_terms': string[20..50],\n"
    "  'boolean_queries': string[3..6],\n"
    "  'notes': string\n"
    "}\n\n"
    "If the prompt is ambiguous, infer reasonable breadth and note assumptions in 'notes'. "
    "Return only JSON; no extra text or CSV."
)

USER_TEMPLATE = (
    "Research prompt (verbatim from researcher):\n{prompt}\n\n"
    "Additional clarifications (optional):\n{clarifications}\n\n"
    "Context & guardrails:\n"
    "- Prioritize literature on collaboration/learning with or without AI – centaur dyads, AI teammates, coaches, assistants – "
    "and effects on information seeking, knowledge-building, and team learning.\n"
    "- Ensure domain coverage for high-pressure settings (military, first responders, healthcare).\n"
    "- Include mechanisms (e.g., sensemaking, shared mental models, joint attention), processes (e.g., AARs, debriefs, knowledge sharing), "
    "and outcomes (e.g., learning, adaptation).\n"
    "- Add US/UK spelling variants, hyphenation variants, stems/wildcards, and acronyms.\n\n"
    "Return only a JSON object matching the schema from the system message. "
    "Do not include any prose before or after. "
    "Label Boolean tiers inline, e.g.:\n"
    "[Precision] (\"shared mental models\" AND team* AND (human-AI OR centaur) ...)\n"
)



def _build_messages(prompt: str, clarifications: str):
    return [
        {"role": "system", "content": SYSTEM_HINT},
        {"role": "user", "content": USER_TEMPLATE.format(
            prompt=(prompt or "").strip(),
            clarifications=(clarifications or "").strip()
        )},
    ]


def _call_gpt(messages: List[Dict[str, str]]) -> str:
    """
    Enqueue approval BEFORE touching secrets. After approval, read the key and
    call OpenAI with a timeout. Any problem is surfaced as a clear error that
    bubbles up to the GUI via the thread's exception handler.
    """

    def _do_call():
        # Only after approval do we attempt to read secrets / call OpenAI.
        try:
            from openai import OpenAI
        except Exception as e:
            return f"__ERROR__: OpenAI SDK not available: {e}"

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return "__ERROR__: OPENAI_API_KEY is not set. Open the Config tab to add it."

        try:
            # Prefer setting timeout on the client to avoid SDK kwargs mismatch.
            client = OpenAI(api_key=key, timeout=45)  # seconds
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            return content if content else "__ERROR__: Empty response from OpenAI."
        except Exception as e:
            return f"__ERROR__: OpenAI call failed: {e}"

    # --- Diagnostics so you can see exactly what's happening -----------------
    mode = (os.getenv("AILYS_APPROVAL_MODE") or "manual").strip().lower()
    try:
        print("TASK approval queue:", approvals._debug_id(), approvals._debug_counts(), flush=True)
    except Exception:
        # _debug helpers may not exist in older builds; that's fine.
        print(f"TASK approval queue: mode={mode}", flush=True)

    # --- Gate via approval queue; no key access yet. -------------------------
    result = approvals.request_approval(
        description="Use OpenAI to generate literature-search keywords/queries (cost: a few cents).",
        call_fn=_do_call,
        # No timeout here — this runs on a worker thread, so it's safe to wait.
        # (If you prefer a timeout, set a value and treat None as "not approved".)
        timeout=None,
    )

    # If the call function returned an error string, raise so the GUI shows ❌
    if isinstance(result, str) and result.startswith("__ERROR__"):
        raise RuntimeError(result)
    if not result:
        raise RuntimeError("Approval declined or failed; no result returned.")
    return result


def _parse_json_block(text: str) -> Dict[str, List[str]]:
    """
    Extract a JSON object from the model reply and normalize lists.
    Accepts raw JSON or JSON inside code fences / prose.
    """
    # Try raw JSON first
    try:
        data = json.loads(text)
    except Exception:
        # Fall back to first JSON-ish block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError("LLM did not return a JSON block.")
        data = json.loads(m.group(0))

    seed = [s.strip() for s in data.get("seed_terms", []) if isinstance(s, str) and s.strip()]
    expd = [s.strip() for s in data.get("expanded_terms", []) if isinstance(s, str) and s.strip()]
    bools = [s.strip() for s in data.get("boolean_queries", []) if isinstance(s, str) and s.strip()]

    if not seed or not bools:
        raise ValueError("Missing required fields in JSON (seed_terms and/or boolean_queries).")
    return {"seed_terms": seed, "expanded_terms": expd, "boolean_queries": bools}


def run(
    file_path: Optional[str] = None,
    guidance: str = "",
    recall_depth: int = 0,
    output_file: Optional[str] = None,
    researcher: str = " ",
    run_id: Optional[str] = None,
    clarifications_csv_path: Optional[str] = None,
):
    """
    Stage A – Prompt → Keywords (CSV-1).
    - file_path: unused (kept for TaskManager compatibility)
    - guidance: the research prompt
    - clarifications_csv_path: if provided, read last row to pick up 'clarifications'
    """
    prompt = (guidance or "").strip()
    if not prompt and not clarifications_csv_path:
        return False, "No prompt provided."

    # If user gave a prior CSV with clarifications, pick them up; else blank.
    clarifications = ""
    if clarifications_csv_path:
        row = read_single_row_csv(clarifications_csv_path)
        if row and row.get("clarifications"):
            clarifications = row.get("clarifications", "")

    # Call LLM (approval-gated). The GUI should show that we're waiting.
    print("Awaiting approval: 'Generate Keywords' request is queued in the Approvals tab.", flush=True)
    llm_reply = _call_gpt(_build_messages(prompt=prompt, clarifications=clarifications))

    parsed = _parse_json_block(llm_reply)

    # Write CSV-1
    rid = run_id or make_run_id()
    paths = run_dirs(rid)
    out_csv = os.path.join(paths["csv"], "prompt_to_keywords.csv")
    now = datetime.datetime.utcnow().isoformat()

    write_csv_row(out_csv, {
        "run_id": rid,
        "timestamp_utc": now,
        "researcher": researcher,
        "prompt": prompt,
        "clarifications": clarifications,
        "seed_terms|;|": from_list(parsed["seed_terms"]),
        "expanded_terms|;|": from_list(parsed["expanded_terms"]),
        "boolean_queries|;|": from_list(parsed["boolean_queries"]),
        "notes": ""
    }, CSV_HEADER)

    return True, f"CSV written: {out_csv}"
