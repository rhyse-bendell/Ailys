# tasks/lit_enrich_candidates.py
from __future__ import annotations
import os, csv, re, time, html, unicodedata
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- Lightweight text repair ----
_RE_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
def _repair_text(s: str) -> str:
    if not s: return s
    # common mojibake: cp1252→utf-8 and latin1 glitches
    fixes = {
        "â€”": "—", "â€“": "–", "â€“": "–", "â€¢": "•", "â€¦": "…",
        "â€˜": "‘", "â€™": "’", "â€œ": "“", "â€": "”", "â€": "”",
        "Ã©": "é", "Ã¨": "è", "Ãª": "ê", "Ã«": "ë",
        "Ã¡": "á", "Ã ": "à", "Ã¢": "â", "Ã£": "ã", "Ã¤": "ä",
        "Ã³": "ó", "Ã²": "ò", "Ã´": "ô", "Ãµ": "õ", "Ã¶": "ö",
        "Ãº": "ú", "Ã¹": "ù", "Ã»": "û", "Ã¼": "ü", "Ã±": "ñ",
        "Â©": "©", "Â®": "®", "Â±": "±", "Âµ": "µ", "Â·": "·",
        "Â°": "°", "Â§": "§", "Â¶": "¶", "Â": "",  # stray non-breaking-space marker
    }
    for k,v in fixes.items():
        s = s.replace(k, v)

    # if we still see a lot of Ã…-style, try a best-effort round-trip
    if "Ã" in s:
        try:
            s2 = s.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
            if s2 and len(s2) >= 0.8*len(s):
                s = s2
        except Exception:
            pass

    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = _RE_CTRL.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)  # strip tags/jats just in case
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _clean_text(s: str) -> str:
    return _repair_text(s)

# ---- STOP handling ----
def _should_stop() -> bool:
    try:
        if os.getenv("LIT_STOP","") == "1": return True
        p = os.getenv("LIT_STOP_FLAG_PATH","")
        return bool(p and os.path.exists(p))
    except Exception:
        return False

# ---- HTTP helpers (same pattern as collector, minimal deps) ----
def _throttle_seconds() -> float:
    try: return float(os.getenv("LIT_RATE_LIMIT_SEC", "1.5"))
    except Exception: return 1.5

def _http_get_json(url: str, headers: dict | None = None, params: dict | None = None) -> dict | None:
    try: import requests
    except Exception: return None
    try:
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    finally:
        time.sleep(_throttle_seconds())
    return None

def _strip_to_abstract(obj: dict | None) -> Optional[str]:
    if not obj or not isinstance(obj, dict): return None
    if "abstract" in obj and obj["abstract"]:
        return _clean_text(str(obj["abstract"]))

    inv = obj.get("abstract_inverted_index")
    if isinstance(inv, dict) and inv:
        try:
            positions = []
            for tok, idxs in inv.items():
                tok = _clean_text(tok)
                for i in idxs:
                    positions.append((i, tok))
            if positions:
                positions.sort(key=lambda x: x[0])
                return _clean_text(" ".join(t for _,t in positions))
        except Exception:
            pass
    return None

def _fetch_abstract_by_doi(doi: str) -> Optional[str]:
    doi = (doi or "").strip().lower()
    if not doi: return None
    mailto = os.getenv("CROSSREF_MAILTO", "") or os.getenv("OPENALEX_EMAIL", "")
    headers = {"User-Agent": f"Ailys/1.0 (mailto:{mailto})"} if mailto else {}
    cr = _http_get_json(f"https://api.crossref.org/works/{doi}", headers=headers)
    if cr and isinstance(cr.get("message"), dict):
        s = _strip_to_abstract(cr["message"])
        if s: return s
    oa = _http_get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
    if oa:
        s = _strip_to_abstract(oa)
        if s: return s
    s2key = os.getenv("SEMANTIC_SCHOLAR_KEY","").strip()
    if s2key:
        s2 = _http_get_json(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            headers={"x-api-key": s2key},
            params={"fields":"title,abstract"}
        )
        s = _strip_to_abstract(s2)
        if s: return s
    return None

def _extract_pmid_from_url(url: str) -> Optional[str]:
    if not url: return None
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url, re.I)
    if m: return m.group(1)
    m = re.search(r"ncbi.nlm.nih.gov/(?:pubmed|pmid)/(\d+)", url, re.I)
    return m.group(1) if m else None

def _fetch_pubmed_abstract(pmid: str) -> Optional[str]:
    pmid = (pmid or "").strip()
    if not pmid: return None
    try: import requests
    except Exception: return None
    params = {"db":"pubmed","id":pmid,"retmode":"xml"}
    api_key = os.getenv("NCBI_API_KEY","").strip()
    if api_key: params["api_key"] = api_key
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=params, timeout=20)
        if r.status_code == 200:
            txt = r.text
            parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", txt, flags=re.I | re.S)
            if parts:
                merged = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in parts)
                return _clean_text(merged)
    except Exception:
        return None
    finally:
        time.sleep(_throttle_seconds())
    return None

# ---- CSV IO ----
CSV2_HEADER = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score","first_author_last"
]

def _ensure_csv2_header(path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path): return
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore").writeheader()

def _read_rows(path: str) -> List[Dict[str,str]]:
    rows: List[Dict[str,str]] = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    return rows

def _write_rows(path: str, rows: List[Dict[str,str]]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore")
        if not exists: w.writeheader()
        for r in rows: w.writerow(r)

# ---- Worker ----
def _enrich_one(r: Dict[str,str], min_len: int) -> Dict[str,str]:
    # always repair noisy fields
    for k in ("title","venue","authors|;|","abstract"):
        r[k] = _clean_text(r.get(k,""))

    existing = r.get("abstract","") or ""
    if len(existing) >= min_len:
        return r

    doi = (r.get("doi") or "").strip().lower()
    url = r.get("url") or ""
    new_abs: Optional[str] = None

    if doi:
        new_abs = _fetch_abstract_by_doi(doi)
    if not new_abs:
        pmid = _extract_pmid_from_url(url)
        if pmid:
            new_abs = _fetch_pubmed_abstract(pmid)

    if new_abs:
        r["abstract"] = _clean_text(new_abs)
    return r

# ---- Public entrypoint -------------------------------------------------------
def enrich_candidates(
    input_csv_path: str,
    output_dir: Optional[str] = None,
    save_prefix: str = "",
    min_len: int = 120,
    max_workers: int = 4,
) -> Tuple[bool,str]:
    """
    Read a deduplicated FINAL CSV, repair text fields, and fetch missing/short abstracts.
    Writes '<prefix>_search_results_enriched.csv' in output_dir (default: alongside input).
    STOP-safe and throttled.
    """
    if not os.path.exists(input_csv_path):
        return False, f"Input CSV not found: {input_csv_path}"

    out_dir = output_dir or os.path.dirname(os.path.abspath(input_csv_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    prefix = (re.sub(r"[^\w\-.]+","_", save_prefix.strip()) if save_prefix else "").strip()
    def pf(n: str) -> str: return f"{prefix}_{n}" if prefix else n

    # choose target
    out_path = os.path.join(out_dir, pf("search_results_enriched.csv"))
    _ensure_csv2_header(out_path)

    rows = _read_rows(input_csv_path)
    if not rows:
        return True, f"No rows found in {input_csv_path}; wrote header-only enriched file: {out_path}"

    # do work
    repaired_batch: List[Dict[str,str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_enrich_one, dict(r), min_len): i for i, r in enumerate(rows)}
        for fut in as_completed(futs):
            if _should_stop():
                break
            try:
                repaired_batch.append(fut.result())
                # stream every ~200 rows to keep progress visible
                if len(repaired_batch) >= 200:
                    _write_rows(out_path, repaired_batch)
                    repaired_batch.clear()
            except Exception:
                pass

    if repaired_batch:
        _write_rows(out_path, repaired_batch)

    return True, f"Enriched file written: {out_path}"
