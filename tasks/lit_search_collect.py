# tasks/lit_search_collect.py
import os, csv, datetime
from typing import Optional, Dict, List, Tuple
from core.lit.utils import to_list, run_dirs
from core.lit.sources import (
    search_openalex, search_crossref, search_arxiv,
    search_pubmed, search_semantic_scholar
)

CSV2_HEADER = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score"
]

def _read_keywords_csv(csv_path: str) -> Dict[str, List[str]]:
    with open(csv_path, "r", encoding="utf-8") as f:
        row = list(csv.DictReader(f))[-1]  # take most recent
    return {
        "run_id": row["run_id"],
        "boolean_queries": to_list(row.get("boolean_queries|;|","")),
        "seed_terms": to_list(row.get("seed_terms|;|","")),
        "expanded_terms": to_list(row.get("expanded_terms|;|","")),
    }

def _write_csv2(path: str, rows: List[Dict[str,str]]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)

def _dedupe(rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
    seen = set()
    out = []
    for r in rows:
        key = (r.get("doi") or "").lower().strip()
        if not key:
            key = (r.get("title","").lower().strip() + "::" + r.get("year","").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def run(
    csv1_path: str,
    researcher: Optional[str] = None,
    per_source: int = 20,
    include: Optional[List[str]] = None
):
    """
    csv1_path: path to prompt_to_keywords.csv (from Stage A)
    per_source: max items per engine per query (soft limit)
    include: subset of engines to use; default = all
    """
    if not os.path.exists(csv1_path):
        return False, f"CSV-1 not found: {csv1_path}"

    meta = _read_keywords_csv(csv1_path)
    run_id = meta["run_id"]
    qs = meta["boolean_queries"]
    if not qs:
        return False, "No boolean queries found in CSV-1."

    paths = run_dirs(run_id)
    out_csv = os.path.join(paths["csv"], "search_results_raw.csv")

    engines = include or ["OpenAlex","Crossref","arXiv","PubMed","SemanticScholar"]
    collected: List[Dict[str,str]] = []

    for q in qs:
        term_origin = "seed/expanded-mix"
        if "OpenAlex" in engines:
            collected += search_openalex(run_id, q, term_origin, per_page=min(per_source,25), max_pages=1)
        if "Crossref" in engines:
            collected += search_crossref(run_id, q, term_origin, rows=min(per_source, 20))
        if "arXiv" in engines:
            collected += search_arxiv(run_id, q, term_origin, max_results=min(per_source, 25))
        if "PubMed" in engines:
            collected += search_pubmed(run_id, q, term_origin, retmax=min(per_source, 20))
        if "SemanticScholar" in engines:
            collected += search_semantic_scholar(run_id, q, term_origin, limit=min(per_source, 20))

    deduped = _dedupe(collected)
    _write_csv2(out_csv, deduped)
    return True, f"CSV written: {out_csv}  (raw: {len(collected)}, deduped: {len(deduped)})"
