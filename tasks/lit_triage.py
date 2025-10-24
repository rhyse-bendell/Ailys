#!/usr/bin/env python3
"""
Lite triage (zero-LLM) for literature candidates.

Routes each row from a deduped candidates CSV (e.g., search_results_final.csv) into:
  - <prefix>_candidates_ready_to_rank.csv
  - <prefix>_candidates_requires_amendment.csv

We NEVER discard rows. We add routing/diagnostic columns and do safe text cleaning.

Usage (module):
    from tasks.lit_triage import run_triage
    ok, msg = run_triage(
        input_csv=".../search_results_final.csv",
        save_prefix="collabLearning",     # optional (default 'relevance')
        write_md_preview=True             # optional
    )

Usage (CLI):
    python -m tasks.lit_triage --input "path/to/search_results_final.csv" --prefix "collabLearning"

Outputs are written under: <dirname(input_csv)>/<prefix or 'relevance'>/
"""

from __future__ import annotations

import os, csv, re, html, argparse
from typing import List, Dict, Tuple, Optional

# ---- Tunables (also check env for overrides) ---------------------------------
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip() not in ("0", "false", "False", "")

TRIAGE_ABS_MIN_CHARS = _env_int("TRIAGE_ABS_MIN_CHARS", 120)
TRIAGE_ABS_MAX_CHARS = _env_int("TRIAGE_ABS_MAX_CHARS", 6000)
TRIAGE_MOJIBAKE_MAX  = _env_int("TRIAGE_MOJIBAKE_MAX", 3)
TRIAGE_LANG_CHECK    = _env_bool("TRIAGE_LANG_CHECK", True)
TRIAGE_WRITE_MD_PREV = _env_bool("TRIAGE_WRITE_MD_PREVIEW", True)

# Common mojibake / encoding artifacts to de-gunk without LLM
MOJIBAKE_FIXES = {
    "â€™": "’", "â€˜": "‘", "â€œ": "“", "â€�": "”",
    "â€“": "–", "â€”": "—", "â€¢": "•", "Â": "",
    "â€•": "—", "â€": '"'
}
MOJIBAKE_PATTERN = re.compile("|".join(re.escape(k) for k in MOJIBAKE_FIXES.keys()))

TOC_HINTS = re.compile(
    r"(?:\bPreface\b|\bPART (?:ONE|TWO|THREE|FOUR|V|VI|VII|VIII|IX|X)\b|\bAppendix\b|\bIndex\b|\bContents\b)",
    re.I
)
CITATION_LIKE = re.compile(
    r"^\s*\(\d{4}\)\.\s+.+?\.\s+.+?\s+\d+(?:\(\d+\))?,\s*\d+(?:[-–]\d+)?\.?\s*$"
)

EN_STOPWORDS = set("""
the of and to a in for is on that with as by from at or an it be are was were this we our their
has have had not but if into more most may can also than other over under about during among
""".split())

CSV_HEADER_BASE = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score","first_author_last"
]

EXTRA_COLS = ["triage_bucket","triage_reasons|;|","abstract_cleaned"]


# ---- Utils -------------------------------------------------------------------
def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass

def _clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    # HTML entity decode then strip html tags
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    # targeted mojibake replacement
    s = MOJIBAKE_PATTERN.sub(lambda m: MOJIBAKE_FIXES.get(m.group(0), ""), s)
    # unicode norm-ish (lightweight)
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _count_mojibake(original: str) -> int:
    if not original:
        return 0
    return len(MOJIBAKE_PATTERN.findall(original))

def _looks_toc_like(text: str) -> bool:
    if not text:
        return False
    head = text[:600]
    if TOC_HINTS.search(head):
        return True
    # many short "heading-like" chunks with numbers
    lines = re.split(r"[.;:]\s+|\n", head)
    numbered = sum(1 for ln in lines if re.search(r"\b\d{1,3}\b", ln) and len(ln) < 80)
    return numbered >= 5

def _looks_citation_like(text: str) -> bool:
    if not text:
        return False
    head = text[:220]
    return bool(CITATION_LIKE.match(head))

def _looks_englishish(text: str) -> bool:
    if not text:
        return True  # don’t punish empties here; other rules will catch
    if not TRIAGE_LANG_CHECK:
        return True
    sample = text[:400]
    # crude ASCII ratio
    ascii_ratio = sum(1 for ch in sample if ord(ch) < 128) / max(1, len(sample))
    if ascii_ratio < 0.8:
        return False
    # crude stopword ratio
    toks = re.findall(r"[A-Za-z']+", sample.lower())
    if not toks:
        return True
    sw = sum(1 for t in toks if t in EN_STOPWORDS)
    return (sw / len(toks)) >= 0.05

def _read_rows(path: str) -> List[Dict[str,str]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def _ensure_header(path: str, header: List[str]):
    _ensure_dir(os.path.dirname(path) or ".")
    if os.path.exists(path):
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=header, extrasaction="ignore").writeheader()

def _write_rows(path: str, header: List[str], rows: List[Dict[str,str]]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)


# ---- Core triage -------------------------------------------------------------
def _route_row(r: Dict[str,str]) -> Tuple[str, List[str], str]:
    """
    Returns (bucket, reasons, abstract_cleaned)
    bucket ∈ {"ready_to_rank", "requires_amendment"}
    """
    title_raw = r.get("title", "") or ""
    abs_raw   = r.get("abstract", "") or ""

    title_c = _clean_text(title_raw)
    abs_c   = _clean_text(abs_raw)

    reasons = []

    if not abs_c.strip():
        reasons.append("no_abstract")

    if abs_c:
        if _looks_toc_like(abs_c):
            reasons.append("toc_like_abstract")
        if _looks_citation_like(abs_c):
            reasons.append("citation_like_abstract")
        if len(abs_c) < TRIAGE_ABS_MIN_CHARS:
            reasons.append("abstract_too_short")
        if len(abs_c) > TRIAGE_ABS_MAX_CHARS:
            reasons.append("abstract_too_long")

    # Mojibake count on original (before fixes)
    mojibake_n = _count_mojibake(abs_raw + " " + title_raw)
    if mojibake_n > TRIAGE_MOJIBAKE_MAX:
        reasons.append("mojibake")

    # Language heuristic
    if abs_c and not _looks_englishish(abs_c):
        reasons.append("likely_non_english")

    bucket = "requires_amendment" if reasons else "ready_to_rank"
    return bucket, reasons, abs_c


def run_triage(input_csv: str, save_prefix: Optional[str] = None,
               write_md_preview: bool = None) -> Tuple[bool, str]:
    """
    Execute triage on input_csv (expected columns: CSV_HEADER_BASE at minimum).
    Outputs are written to: <dirname(input_csv)>/<prefix or 'relevance'>/
    """
    if write_md_preview is None:
        write_md_preview = TRIAGE_WRITE_MD_PREV

    if not os.path.exists(input_csv):
        return False, f"Input CSV not found: {input_csv}"

    base_dir = os.path.dirname(os.path.abspath(input_csv)) or "."
    prefix   = (save_prefix or "relevance").strip() or "relevance"
    out_dir  = os.path.join(base_dir, prefix)
    _ensure_dir(out_dir)

    rows = _read_rows(input_csv)
    if not rows:
        return False, f"No rows in {input_csv}"

    # Output files
    ready_path   = os.path.join(out_dir, f"{prefix}_candidates_ready_to_rank.csv")
    amend_path   = os.path.join(out_dir, f"{prefix}_candidates_requires_amendment.csv")
    summary_path = os.path.join(out_dir, f"{prefix}_triage_summary.txt")
    preview_md   = os.path.join(out_dir, f"{prefix}_triage_preview.md")

    header = list(CSV_HEADER_BASE)
    for h in EXTRA_COLS:
        if h not in header:
            header.append(h)

    _ensure_header(ready_path, header)
    _ensure_header(amend_path, header)

    # Route
    ready_rows: List[Dict[str,str]] = []
    amend_rows: List[Dict[str,str]] = []

    reason_counts: Dict[str,int] = {}
    combo_counts: Dict[str,int]  = {}

    for r in rows:
        bucket, reasons, abs_clean = _route_row(r)
        rr = dict(r)
        rr["abstract_cleaned"] = abs_clean
        rr["triage_bucket"] = bucket
        rr["triage_reasons|;|"] = ";".join(reasons) if reasons else ""

        if bucket == "ready_to_rank":
            ready_rows.append(rr)
        else:
            amend_rows.append(rr)

        # stats
        if reasons:
            for k in reasons:
                reason_counts[k] = reason_counts.get(k, 0) + 1
            combo = ";".join(sorted(reasons))
            combo_counts[combo] = combo_counts.get(combo, 0) + 1

    if ready_rows:
        _write_rows(ready_path, header, ready_rows)
    if amend_rows:
        _write_rows(amend_path, header, amend_rows)

    # summary
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"Input: {input_csv}\n")
            f.write(f"Output dir: {out_dir}\n")
            f.write(f"Ready: {len(ready_rows)} | Requires amendment: {len(amend_rows)} | Total: {len(rows)}\n\n")
            f.write("Reason counts:\n")
            for k, v in sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0])):
                f.write(f"  {k}: {v}\n")
            f.write("\nTop reason combinations:\n")
            for k, v in sorted(combo_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]:
                f.write(f"  {k or '(none)'}: {v}\n")
    except Exception:
        pass

    # preview (small human-readable sample)
    if write_md_preview:
        try:
            def _sample(lst: List[Dict[str,str]], n: int = 10) -> List[Dict[str,str]]:
                return lst[:min(n, len(lst))]

            with open(preview_md, "w", encoding="utf-8") as f:
                f.write(f"# Triage preview — {prefix}\n\n")
                f.write(f"**Ready to rank** ({len(ready_rows)}):\n\n")
                for r in _sample(ready_rows, 10):
                    f.write(f"- **{r.get('title','').strip()}** ({r.get('year','')}) — {r.get('venue','')}\n")
                f.write("\n**Requires amendment** ({len}):\n\n".replace("{len}", str(len(amend_rows))))
                for r in _sample(amend_rows, 10):
                    f.write(f"- **{r.get('title','').strip()}** ({r.get('year','')}) — reasons: {r.get('triage_reasons|;|','')}\n")
        except Exception:
            pass

    return True, f"Ready={len(ready_rows)}, RequiresAmendment={len(amend_rows)} → {out_dir}"


# ---- CLI ---------------------------------------------------------------------
def _main():
    ap = argparse.ArgumentParser(description="Zero-LLM triage splitter for literature candidates.")
    ap.add_argument("--input", required=True, help="Path to search_results_final.csv")
    ap.add_argument("--prefix", default="relevance", help="Save prefix (also names the output folder)")
    ap.add_argument("--no-preview", action="store_true", help="Disable markdown preview")
    args = ap.parse_args()

    ok, msg = run_triage(args.input, save_prefix=args.prefix, write_md_preview=not args.no_preview)
    print(("✅ " if ok else "❌ ") + msg)

if __name__ == "__main__":
    _main()
