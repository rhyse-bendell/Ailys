# tasks/lit_review_relevance.py
from __future__ import annotations

import os, csv, json, time, re, hashlib, datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.lit.utils import run_dirs, to_list
from core import artificial_cognition as brain
import core.approval_queue as approvals

DEBUG = os.getenv("LIT_DEBUG", "1") != "0"

def _dbg(msg: str):
    if DEBUG:
        print(f"[debug] {msg}")

def _now_utc_stamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _read_last_row(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        if not rows:
            raise RuntimeError(f"No rows in: {path}")
        return rows[-1]

def _read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _wcsv(path: str, rows: List[Dict[str, str]], header: List[str]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)

def _clean(s: Optional[str]) -> str:
    if not s: return ""
    # cheap compaction
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _hash_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

@dataclass
class RelevanceConfig:
    batch_size: int = 15
    max_items: Optional[int] = None  # cap for debugging
    require_reason: bool = True
    # Score names & ranges (all 0-5)
    dimensions: Tuple[str, ...] = (
        "topical_fit",         # does this paper match the research topic?
        "method_fit",          # methods appropriate/useful to the need?
        "context_fit",         # domain/setting/population alignment?
        "recency_novelty",     # recent/novel/impactful wrt need?
        "quality_signal",      # venue/citations/signal of quality?
        "actionability",       # likely useful for synthesis/next steps?
    )

RELEVANCE_HEADER = [
    # provenance
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score",
    # scoring
    "overall_relevance",
    "topical_fit","method_fit","context_fit","recency_novelty","quality_signal","actionability",
    "exclusions","notes","llm_model","rated_at_utc"
]

PROMPT_TEMPLATE = """You are assisting with a literature triage. Read the need and the candidate records.
Return STRICT JSON ONLY matching the response schema. Do not include prose.

RESEARCH NEED (verbatim from the project context):
---
{need_text}
---

SCORING DIMENSIONS (0–5 integers only, higher is better):
- topical_fit: topical alignment to the need.
- method_fit: methods/designs are relevant and useful.
- context_fit: domain/setting/population matches or transfers.
- recency_novelty: recent or novel enough to matter now.
- quality_signal: likely quality (venue, citations, clarity).
- actionability: expected usefulness for synthesis/next steps.

Compute overall_relevance (0–100) as a calibrated aggregation (NOT a simple average).
If an item is clearly out-of-scope, you may set overall_relevance to 0 and list a short reason in 'exclusions'.

RESPONSE SCHEMA (JSON):
{{
  "items": [
    {{
      "work_id": "<string>",            # echo from input
      "overall_relevance": <int 0-100>,
      "topical_fit": <int 0-5>,
      "method_fit": <int 0-5>,
      "context_fit": <int 0-5>,
      "recency_novelty": <int 0-5>,
      "quality_signal": <int 0-5>,
      "actionability": <int 0-5>,
      "exclusions": "<short optional text>",
      "notes": "<1-2 concise bullets; optional>"
    }}
  ]
}}

CANDIDATE RECORDS:
{records_block}
"""

def _format_records_block(rows: List[Dict[str, str]]) -> str:
    # Keep it compact but sufficient for triage
    lines = []
    for r in rows:
        title = _clean(r.get("title",""))
        abs_ = _clean(r.get("abstract",""))
        if len(abs_) > 1500:  # avoid blowing token budget
            abs_ = abs_[:1500].rstrip() + " …"
        authors = _clean(r.get("authors|;|",""))
        y = _clean(r.get("year",""))
        venue = _clean(r.get("venue",""))
        doi = _clean(r.get("doi",""))
        url = _clean(r.get("url",""))
        work_id = r.get("work_id") or (doi if doi else f"{title.lower()}::{y}")
        block = {
            "work_id": work_id,
            "title": title,
            "authors": authors,
            "year": y,
            "venue": venue,
            "doi": doi,
            "url": url,
            "abstract": abs_,
        }
        lines.append(block)
    return json.dumps(lines, ensure_ascii=False, indent=2)

def _parse_json_safely(txt: str) -> Dict:
    """
    Try to parse strictly; if the model emitted leading/trailing text,
    grab the first JSON object with a quick brace match.
    """
    txt = txt.strip()
    try:
        return json.loads(txt)
    except Exception:
        pass

    # Fallback: find first {...} block
    m = re.search(r"\{(?:[^{}]|(?R))*\}", txt)  # recursive-ish via PCRE isn't in Python std; emulate simple block
    if not m:
        # simpler fallback: grab between first '{' and last '}'
        try:
            start = txt.index("{"); end = txt.rindex("}") + 1
            return json.loads(txt[start:end])
        except Exception:
            raise ValueError("Could not parse JSON from model output.")

    s = m.group(0)
    return json.loads(s)

def _score_batch(
    need_text: str,
    batch_rows: List[Dict[str, str]],
    batch_idx: int,
    batch_total: int,
    cfg: RelevanceConfig
) -> Tuple[List[Dict[str,str]], str]:
    """
    Calls the LLM via artificial cognition. Returns (scored_rows, model_id).
    """
    records_block = _format_records_block(batch_rows)
    prompt = PROMPT_TEMPLATE.format(need_text=need_text, records_block=records_block)

    desc = f"Lit relevance scoring batch {batch_idx+1}/{batch_total} (n={len(batch_rows)})"
    result = brain.ask(
        prompt=prompt,
        description=desc,
        temperature=0.1,            # bias toward consistency
        max_tokens=1800,            # plenty for JSON
        timeout=None                # approval-gated elsewhere
    )
    raw = result.raw_text
    data = _parse_json_safely(raw)
    items = data.get("items") or []

    # Build map by work_id for easy join
    by_id = { (_clean(i.get("work_id") or "")): i for i in items if isinstance(i, dict) }
    scored: List[Dict[str,str]] = []
    for r in batch_rows:
        work_id = r.get("work_id") or (r.get("doi") or f"{(r.get('title','').lower())}::{r.get('year','')}")
        j = by_id.get(_clean(work_id), {})
        out = dict(r)
        out["overall_relevance"] = str(int(j.get("overall_relevance", 0)))
        for k in ("topical_fit","method_fit","context_fit","recency_novelty","quality_signal","actionability"):
            out[k] = str(int(j.get(k, 0)))
        out["exclusions"] = _clean(j.get("exclusions",""))
        out["notes"] = _clean(j.get("notes",""))
        out["llm_model"] = result.model_id
        out["rated_at_utc"] = _now_utc_stamp()
        scored.append(out)
    return scored, result.model_id

def _unique_attempt_dirs(paths: Dict[str,str]) -> Dict[str,str]:
    stamp = datetime.datetime.utcnow().strftime("attempt_%Y-%m-%d_%H-%M-%S")
    out = {}
    for k in ("csv","raw","logs"):
        base = paths.get(k) or os.path.join(os.getcwd(), "runs", "unknown", k)
        p = os.path.join(base, stamp)
        _ensure_dir(p)
        out[k] = p
    return out

def run(
    csv1_path: str,                      # prompt_to_keywords.csv
    collected_csv_path: Optional[str]=None,  # defaults to search_results_final.csv in run dirs
    batch_size: Optional[int]=None,
    max_items: Optional[int]=None,
) -> Tuple[bool, str]:
    """
    Ingests CSVs from the search stage, scores relevance with LLM, and writes:
      - relevance_scored_partial.csv      (streaming)
      - relevance_scored_final.csv        (rank-ordered by overall_relevance desc)
    Returns (ok, message).
    """
    print("Task started...")

    if not os.path.exists(csv1_path):
        return False, f"prompt_to_keywords CSV not found: {csv1_path}"

    # --- Read context (need) ---------------------------------------------------
    try:
        row1 = _read_last_row(csv1_path)
    except Exception as e:
        return False, f"Failed to read CSV-1 context: {e}"

    run_id = (row1.get("run_id") or "").strip() or datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
    need_text_parts = []
    for k in ("research_need","user_prompt","prompt"):  # tolerate schema variations
        if row1.get(k):
            need_text_parts.append(str(row1[k]))
    # fallbacks: synthesize from fields if no direct prompt column exists
    if not need_text_parts:
        seeds = ", ".join(to_list(row1.get("seed_terms|;|","")))
        bools = "; ".join(to_list(row1.get("boolean_queries|;|","")))
        need_text_parts.append(f"Seed terms: {seeds}\nBoolean queries: {bools}")
    need_text = "\n".join([s for s in need_text_parts if s]).strip()

    # --- Resolve run directories the same way as the collection task ----------
    paths = run_dirs(run_id) or {}
    default_root = os.path.join(os.getcwd(), "runs", run_id)
    paths.setdefault("csv", os.path.join(default_root, "csv"))
    paths.setdefault("raw", os.path.join(default_root, "raw"))
    paths.setdefault("logs", os.path.join(default_root, "logs"))

    paths = _unique_attempt_dirs(paths)
    _dbg(f"Writing outputs to unique attempt folder: csv={paths['csv']} raw={paths['raw']} logs={paths['logs']}")

    # Input collection CSV default
    if not collected_csv_path:
        collected_csv_path = os.path.join(paths["csv"], "..", "..")  # up out of attempt folder
        collected_csv_path = os.path.abspath(os.path.join(collected_csv_path, "search_results_final.csv"))

    if not os.path.exists(collected_csv_path):
        return False, f"Collected results CSV not found: {collected_csv_path}"

    rows = _read_csv_rows(collected_csv_path)
    if max_items and max_items > 0:
        rows = rows[:max_items]

    # Normalize/ensure work_id presence
    for r in rows:
        wid = r.get("work_id") or (r.get("doi") or f"{(r.get('title','').lower())}::{r.get('year','')}")
        r["work_id"] = wid

    cfg = RelevanceConfig(
        batch_size = int(batch_size) if batch_size else int(os.getenv("LIT_RELEVANCE_BATCH", "15")),
        max_items = max_items
    )

    # --- Outputs ---------------------------------------------------------------
    out_partial = os.path.join(paths["csv"], "relevance_scored_partial.csv")
    out_final   = os.path.join(paths["csv"], "relevance_scored_final.csv")
    log_path    = os.path.join(paths["logs"], "relevance_scoring.log")

    def _log(line: str):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line.rstrip() + "\n")
        except Exception:
            pass

    # headers
    if not os.path.exists(out_partial):
        _wcsv(out_partial, [], RELEVANCE_HEADER)
    if not os.path.exists(out_final):
        _wcsv(out_final, [], RELEVANCE_HEADER)  # will be overwritten later

    # --- Batch & score ---------------------------------------------------------
    total = len(rows)
    if total == 0:
        msg = "No rows to score (input CSV empty)."
        print(msg)
        return True, msg

    batches: List[List[Dict[str,str]]] = []
    for i in range(0, total, cfg.batch_size):
        batches.append(rows[i:i+cfg.batch_size])

    all_scored: List[Dict[str,str]] = []
    model_seen = None

    # Approval is handled INSIDE artificial_cognition.ask for every batch.
    for bi, batch in enumerate(batches):
        if not batch:
            continue
        try:
            t0 = time.time()
            scored, model_id = _score_batch(need_text, batch, bi, len(batches), cfg)
            dt = time.time() - t0
            model_seen = model_seen or model_id
            _log(f"[OK] batch {bi+1}/{len(batches)} | n={len(batch)} | {dt:.2f}s | model={model_id}")
            _wcsv(out_partial, scored, RELEVANCE_HEADER)
            all_scored.extend(scored)
            print(f"[score] batch {bi+1}/{len(batches)}: +{len(scored)}")
        except Exception as e:
            _log(f"[ERR] batch {bi+1}/{len(batches)} | {type(e).__name__}: {e}")
            print(f"[score] ERROR in batch {bi+1}: {e}")

    if not all_scored:
        return False, "No items scored; see log."

    # --- Rank & write FINAL ----------------------------------------------------
    def _intval(s: str, default: int = 0) -> int:
        try:
            return int(str(s).strip())
        except Exception:
            return default

    ranked = sorted(all_scored, key=lambda r: _intval(r.get("overall_relevance", "0")), reverse=True)

    # overwrite final cleanly
    try:
        if os.path.exists(out_final):
            os.remove(out_final)
    except Exception:
        pass
    _wcsv(out_final, ranked, RELEVANCE_HEADER)

    msg = (f"RELEVANCE partial: {out_partial} | rows={len(all_scored)}\n"
           f"RELEVANCE final (ranked): {out_final} | rows={len(ranked)}")
    print(msg)
    return True, msg


# ------------------------------ CLI helper -----------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Score and rank literature relevance.")
    ap.add_argument("--csv1", required=True, help="Path to prompt_to_keywords.csv")
    ap.add_argument("--input", default=None, help="Path to collected results CSV (default: search_results_final.csv in run dirs)")
    ap.add_argument("--batch", type=int, default=None, help="Batch size (default env LIT_RELEVANCE_BATCH or 15)")
    ap.add_argument("--max-items", type=int, default=None, help="Optional cap for debugging")
    args = ap.parse_args()
    ok, msg = run(args.csv1, args.input, args.batch, args.max_items)
    print("✅" if ok else "❌", msg)
