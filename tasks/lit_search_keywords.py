# tasks/lit_search_keywords.py
import os
import datetime
import json
import re
import io
import csv
from typing import Optional, Dict, List

from core.lit.utils import (
    make_run_id, run_dirs, write_csv_row, read_single_row_csv, from_list
)

# Route ALL cognition through Ailys' central brain (approval-gated internally).
from core import artificial_cognition as brain



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

    # Call LLM via central brain (approval-gated internally).
    print("Awaiting approval: 'Generate Keywords' request is queued in the Approvals pane.", flush=True)
    resp = brain.ask(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        description="Literature Search: augment existing keywords CSV",
        temperature=None,
        max_tokens=800,  # enough for a one-row CSV with lists
        timeout=None,
    )
    llm_reply = resp.raw_text
    if not llm_reply:
        raise RuntimeError("Empty model response.")

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

# --- Normalization helpers for CSV-1 schema ---------------------------------

# The canonical CSV-1 header (already defined as CSV_HEADER above)
_LIST_COLS = {"seed_terms|;|", "expanded_terms|;|", "boolean_queries|;|"}

def _norm_key(k: str) -> str:
    """
    Normalize a column name for matching:
    - lowercases
    - replaces spaces with underscores
    - strips any '|...|' list markers
    """
    kk = (k or "").strip().lower().replace(" ", "_")
    # remove things like "|;|" suffixes
    kk = re.sub(r"\|.*\|", "", kk)
    return kk

def _normalize_list_field(val: Optional[str]) -> str:
    """
    Accepts JSON arrays or delimited strings and emits the canonical ';' joined form
    used by from_list().
    """
    if val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # JSON array?
    if s.startswith("["):
        try:
            arr = json.loads(s)
            parts = [str(x).strip() for x in arr if str(x).strip()]
            return from_list(parts)
        except Exception:
            pass
    # Delimited by ; , or |
    parts = re.split(r"[;,|]\s*", s)
    parts = [p.strip().strip('"').strip("'") for p in parts if p.strip()]
    return from_list(parts)

def _read_first_row_as_dict(csv_text: str) -> Dict[str, str]:
    """
    Try to read the first row of a CSV string into a dict (case-insensitive keys).
    Returns {} on failure.
    """
    try:
        rdr = csv.DictReader(io.StringIO(csv_text))
        for row in rdr:
            return row or {}
    except Exception:
        pass
    return {}

def _coerce_to_csv1_schema(
    updated_csv_text: str,
    original_row: Dict[str, str],
    researcher_fallback: str = "Researcher"
) -> Dict[str, str]:
    """
    Coerce whatever the model returned into the exact CSV-1 schema (CSV_HEADER).
    Strategy:
      - parse model CSV's first row (if any)
      - build a normalized-key lookup
      - start from original_row as base and override known fields if present
      - ensure list columns are canonical ';' joined
      - fill missing non-list fields from original_row; timestamp is refreshed
    """
    # start with original as base
    base = dict(original_row or {})

    # ensure base has minimal keys
    for k in CSV_HEADER:
        base.setdefault(k, "")

    # refresh timestamp, keep run_id & prompt unless explicitly changed
    base["timestamp_utc"] = datetime.datetime.utcnow().isoformat()
    base["researcher"] = base.get("researcher") or researcher_fallback

    # parse model CSV (first row)
    model_row = _read_first_row_as_dict(updated_csv_text)
    norm_map: Dict[str, str] = {}
    for k, v in model_row.items():
        norm_map[_norm_key(k)] = v

    # mapping for list columns (model might omit '|;|' markers)
    list_key_alias = {
        "seed_terms|;|": "seed_terms",
        "expanded_terms|;|": "expanded_terms",
        "boolean_queries|;|": "boolean_queries",
    }

    # override from model where available
    for col in CSV_HEADER:
        if col in _LIST_COLS:
            alias = list_key_alias[_norm_key(col + "")] if _norm_key(col) in list_key_alias else list_key_alias.get(col, None)
            # prefer exact list column name in model header, else alias without marker
            val = None
            # try exact name
            if _norm_key(col) in norm_map:
                val = norm_map[_norm_key(col)]
            # try alias without marker
            elif alias and alias in norm_map:
                val = norm_map[alias]
            if val is not None:
                base[col] = _normalize_list_field(val)
            else:
                # keep whatever base had (already normalized)
                base[col] = _normalize_list_field(base.get(col, ""))
        else:
            # non-list column: try to map by normalized key (e.g., "clarifications")
            nk = _norm_key(col)
            if nk in norm_map and str(norm_map[nk]).strip():
                base[col] = str(norm_map[nk]).strip()

    return {k: base.get(k, "") for k in CSV_HEADER}

# ==== Augment an existing keywords CSV (START) ====
def augment_keywords_csv(
    existing_csv_path: str,
    clarification_prompt: str,
    output_csv_path: str,
    researcher: str = ""
) -> str:
    """
    Read an existing keywords CSV (CSV-1) and ask the central brain to augment/amend it
    based on a new clarification prompt. The brain is approval-gated internally.
    Writes a fully normalized CSV (exact CSV_HEADER) to output_csv_path and returns that path.
    """
    if not os.path.exists(existing_csv_path):
        raise FileNotFoundError(existing_csv_path)

    # Load the original single-row CSV-1 as base
    original_row = read_single_row_csv(existing_csv_path) or {}

    with open(existing_csv_path, "r", encoding="utf-8") as f:
        existing_csv_text = f.read()

    system = (
        "You are Ailys, assisting with literature search term design.\n"
        "You will be given an existing keywords CSV and a new clarification.\n\n"
        "Your task:\n"
        "• Update/amend the CSV to reflect the clarification.\n"
        "• Preserve the exact semantics of the original columns (do not invent new fields).\n"
        "• Keep existing useful content; add/modify/remove items only as needed to improve precision/recall.\n"
        "• Remove duplicates; preserve notes if present.\n\n"
        "Output rules:\n"
        "• Return a CSV including a header row (OK if header formatting differs; tooling will normalize).\n"
        "• Do NOT return JSON or prose, only CSV text.\n"
        "• Using plain commas is fine; tooling will normalize list separators.\n"
    )

    user = (
        f"Existing CSV (verbatim):\n{existing_csv_text}\n\n"
        f"Clarification / update from researcher '{researcher or 'Researcher'}':\n{clarification_prompt}\n\n"
        "Please return ONLY the updated CSV (with header)."
    )

    resp = brain.ask(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        description="Literature Search: augment existing keywords CSV",
        temperature=None,
        max_tokens=2000,  # plenty for a one-row CSV with lists
        timeout=None,
    )

    # Keep the raw text as-is in cognition memory; normalize only the file we save.
    updated_csv_raw = (resp.raw_text or "").strip()
    # If the model fenced the CSV, try to unwrap (best-effort)
    def _extract_csv_block(text: str) -> str:
        if not text:
            return text
        t = text.strip()
        m = re.search(r"```csv\s+(.*?)```", t, flags=re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m = re.search(r"```\s*(.*?)```", t, flags=re.DOTALL)
        if m:
            return m.group(1).strip()
        return t

    updated_csv_text = _extract_csv_block(updated_csv_raw)

    # Coerce to exact CSV-1 schema (header + single row), preserving original where absent
    normalized_row = _coerce_to_csv1_schema(
        updated_csv_text,
        original_row=original_row,
        researcher_fallback=(researcher or "Researcher")
    )

    # Ensure run_id and prompt survive unless explicitly changed
    normalized_row["run_id"] = original_row.get("run_id", normalized_row.get("run_id", make_run_id()))
    normalized_row["prompt"] = original_row.get("prompt", normalized_row.get("prompt", ""))

    # Write out a single-row CSV with our canonical header
    out_dir = os.path.dirname(output_csv_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    write_csv_row(output_csv_path, normalized_row, CSV_HEADER)

    return output_csv_path

