# tasks/lit_search_collect.py
from __future__ import annotations

import os, csv, datetime, re, time, html, unicodedata
from collections import defaultdict
from typing import Optional, Dict, List, Tuple
from core.lit.utils import to_list, run_dirs
import core.approval_queue as approvals


DEBUG_LIT = os.getenv("LIT_DEBUG", "1") != "0"

def _dbg(msg: str):
    if DEBUG_LIT:
        print(f"[debug] {msg}")

def _write_log_line(path: str, line: str):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass

def _should_stop(stop_flag_path: str | None = None) -> bool:
    """
    Returns True if a stop was requested via env var LIT_STOP=1 or a STOP file on disk.
    """
    try:
        if os.getenv("LIT_STOP", "") == "1":
            return True
        if stop_flag_path and os.path.exists(stop_flag_path):
            return True
    except Exception:
        pass
    return False
# === [PATCH Q END] ===


def _with_temp_approval_mode(temp_mode: str, fn):
    """
    Run fn() while the approval queue is temporarily set to `temp_mode`
    (e.g., 'auto'), then restore the previous mode. Used so that
    non-token, network-only child calls do NOT enqueue approvals.
    """
    prev_mode = None
    try:
        prev_mode = approvals.approval_queue.get_mode() if hasattr(approvals.approval_queue, "get_mode") else None
    except Exception:
        try:
            prev_mode = getattr(approvals.approval_queue, "mode", None)
        except Exception:
            prev_mode = None
    try:
        approvals.approval_queue.set_mode(temp_mode)
        return fn()
    finally:
        try:
            if prev_mode:
                approvals.approval_queue.set_mode(prev_mode)
        except Exception:
            pass
def _clean_text(s: str) -> str:
    if not s:
        return s
    # HTML entities
    s = html.unescape(s)
    # Strip tags (Crossref JATS etc.)
    s = re.sub(r"<[^>]+>", " ", s, flags=re.I)
    # Normalize unicode & remove control chars (except \n\t)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _throttle_seconds() -> float:
    try:
        return float(os.getenv("LIT_RATE_LIMIT_SEC", "1.5"))
    except Exception:
        return 1.5

def _http_get_json(url: str, headers: dict | None = None, params: dict | None = None) -> dict | None:
    try:
        import requests
    except Exception:
        return None
    try:
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    finally:
        time.sleep(_throttle_seconds())
    return None

def _strip_to_abstract(obj: dict | None) -> str | None:
    """
    Extract & clean an abstract from various APIs (Crossref/OpenAlex/S2/PubMed payloads).
    """
    if not obj or not isinstance(obj, dict):
        return None

    # Crossref: 'abstract' often JATS
    if "abstract" in obj and obj["abstract"]:
        return _clean_text(str(obj["abstract"]))

    # OpenAlex: 'abstract_inverted_index' => reconstruct
    inv = obj.get("abstract_inverted_index")
    if isinstance(inv, dict) and inv:
        # reconstruct: place each token at listed positions
        try:
            positions = []
            for token, idxs in inv.items():
                token = _clean_text(token)
                for i in idxs:
                    positions.append((i, token))
            if positions:
                positions.sort(key=lambda x: x[0])
                words = []
                last = -1
                for i, tok in positions:
                    # fill gaps with spaces
                    if i - last > 1:
                        pass
                    words.append(tok)
                    last = i
                return _clean_text(" ".join(words))
        except Exception:
            pass

    # Semantic Scholar (unified): 'abstract'
    if "abstract" in obj and obj["abstract"]:
        return _clean_text(str(obj["abstract"]))

    # PubMed EFetch (XML parsed as dict if any upstream converted) – we won't rely on it here
    return None

def _fetch_abstract_by_doi(doi: str) -> str | None:
    doi = (doi or "").strip()
    if not doi:
        return None

    # 1) Crossref
    mailto = os.getenv("CROSSREF_MAILTO", "") or os.getenv("OPENALEX_EMAIL", "")
    headers = {"User-Agent": f"Ailys/1.0 (mailto:{mailto})"} if mailto else {}
    cr = _http_get_json(f"https://api.crossref.org/works/{doi}", headers=headers)
    if cr and isinstance(cr.get("message"), dict):
        s = _strip_to_abstract(cr["message"])
        if s:
            return s

    # 2) OpenAlex
    # OpenAlex ID lookup by DOI
    oa = _http_get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
    if oa:
        s = _strip_to_abstract(oa)
        if s:
            return s

    # 3) Semantic Scholar (if key provided)
    s2_key = os.getenv("SEMANTIC_SCHOLAR_KEY", "").strip()
    if s2_key:
        s2 = _http_get_json(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            headers={"x-api-key": s2_key},
            params={"fields": "title,abstract,year,venue,externalIds,url"}
        )
        s = _strip_to_abstract(s2)
        if s:
            return s

    return None

def _extract_pmid_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"ncbi.nlm.nih.gov/(?:pubmed|pmid)/(\d+)", url, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url, flags=re.I)
    if m:
        return m.group(1)
    return None

def _fetch_pubmed_abstract(pmid: str) -> str | None:
    pmid = (pmid or "").strip()
    if not pmid:
        return None
    try:
        import requests
    except Exception:
        return None
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    if api_key:
        params["api_key"] = api_key
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                         params=params, timeout=20)
        if r.status_code == 200:
            # very light XML → text pull
            txt = r.text
            # collect all <AbstractText>…</AbstractText>
            parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", txt, flags=re.I | re.S)
            if parts:
                joined = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in parts)
                return _clean_text(joined)
    except Exception:
        return None
    finally:
        time.sleep(_throttle_seconds())
    return None

def _scrape_page_for_abstract(url: str) -> str | None:
    """
    Very light fallback using BeautifulSoup if available.
    We only try obvious places; if bs4 isn't installed we skip silently.
    """
    try:
        from bs4 import BeautifulSoup  # optional
        import requests
    except Exception:
        return None
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Ailys/1.0"})
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        # candidates: schema.org, meta description, obvious CSS classes/ids
        sel = [
            '[itemprop="abstract"]',
            'section.abstract, div.abstract, #abstract, .article__abstract',
            'meta[name="description"]',
        ]
        text = ""
        for css in sel:
            for el in soup.select(css):
                if el.name == "meta":
                    text = el.get("content", "") or ""
                else:
                    text = el.get_text(" ", strip=True) or ""
                text = _clean_text(text)
                if text and len(text) > 120:
                    return text
        return None
    except Exception:
        return None
    finally:
        time.sleep(_throttle_seconds())

def _simplify_boolean(q: str) -> str:
    """
    Relax a complex boolean string into a generic keyword bag that most public APIs tolerate better.
    - drop quotes and parentheses
    - keep OR/AND as spaces (bias to recall)
    - collapse to single spaces
    """
    if not q:
        return q
    s = re.sub(r'["()]', " ", q)
    s = re.sub(r"\bAND\b", " ", s, flags=re.I)
    s = re.sub(r"\bOR\b", " ", s, flags=re.I)
    s = re.sub(r"\bNOT\b", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s



def _build_pubmed_queries(spec: QuerySpec, base_boolean: str) -> List[str]:
    """PubMed: preserve Boolean + phrases; tag Title/Abstract; chunk OR lists."""
    queries = []
    must = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.must_phrases or []) if p.strip()]
    anys = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.any_phrases or []) if p.strip()]
    nots = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.exclude_terms or []) if p.strip()]
    any_chunks = _chunk(anys, 4) if anys else [[]]
    for ch in any_chunks:
        parts = []
        if must: parts.append("(" + " AND ".join(must) + ")")
        if ch:   parts.append("(" + " OR ".join(ch) + ")")
        if base_boolean: parts.append(f"({base_boolean})")
        if nots: parts.append("NOT (" + " OR ".join(nots) + ")")
        q = " AND ".join([p for p in parts if p])
        if q.strip(): queries.append(q)
    return queries or ([base_boolean] if base_boolean else [])

def _build_arxiv_queries(spec: QuerySpec, base_boolean: str) -> List[str]:
    """arXiv: ti:/abs: fields, optional categories; keep phrases; avoid over-nesting."""
    tiabs = []
    for p in (spec.must_phrases or []):
        if p.strip():
            tiabs.append(f'ti:{_phrase(p)} OR abs:{_phrase(p)}')
    anys = [f'ti:{_phrase(p)} OR abs:{_phrase(p)}' for p in (spec.any_phrases or []) if p.strip()]
    any_chunks = _chunk(anys, 3) if anys else [[]]
    cats = []
    for d in (spec.domains or []):
        dl = d.strip().lower()
        if dl in ("cs.ai","ai","artificial intelligence"): cats.append("cat:cs.AI")
        elif dl in ("cs.hc","hci","human-computer interaction"): cats.append("cat:cs.HC")
        elif dl in ("stat.ml","ml"): cats.append("cat:stat.ML")
    cat_clause = ("(" + " OR ".join(cats) + ")") if cats else ""
    queries = []
    for ch in any_chunks:
        parts = []
        if tiabs: parts.append("(" + " AND ".join([f"({c})" for c in tiabs]) + ")")
        if ch:    parts.append("(" + " OR ".join([f"({c})" for c in ch]) + ")")
        if base_boolean: parts.append(f"({_clean_text(base_boolean)})")
        if cat_clause: parts.append(cat_clause)
        q = " AND ".join([p for p in parts if p])
        if q.strip(): queries.append(q)
    return queries or ([base_boolean] if base_boolean else [])

def _build_openalex_queries(spec: QuerySpec, base_boolean: str) -> List[str]:
    """OpenAlex: avoid AND/OR/parens; use a trimmed bag-of-words string with quoted phrases OK."""
    seeds = []
    seeds += [p for p in (spec.must_phrases or []) if p.strip()]
    seeds += [p for p in (spec.any_phrases or []) if p.strip()]
    seeds += [p for p in (spec.title_bias_terms or []) if p.strip()]
    # Convert base_boolean to a bag for OpenAlex
    base_bow = _bag_of_words(base_boolean)
    # Pack small groups to probe recall while staying under length limits
    packs = _chunk(seeds, 5) or [[]]
    queries = []
    for pack in packs:
        parts = []
        if pack: parts.append(" ".join(_phrase(p) for p in pack))
        if base_bow: parts.append(base_bow)
        q = _trim_len(" ".join(parts).strip(), 300)
        if q: queries.append(q)
    # Ensure at least one
    return queries or ([base_bow] if base_bow else [])


def _build_crossref_queries(spec: QuerySpec, base_boolean: str) -> List[str]:
    """Crossref: tolerant; quoted phrases + venue/type hints; boolean optional."""
    hints = []
    if spec.venues:    hints += [f'"{v}"' for v in spec.venues if v.strip()]
    if spec.doc_types: hints += [t for t in spec.doc_types if t.strip()]
    seeds = []
    seeds += [p for p in (spec.must_phrases or []) if p.strip()]
    seeds += [p for p in (spec.any_phrases or []) if p.strip()]
    base_soft = _strip_label_and_parens(base_boolean)  # Crossref will tolerate operators, but soft is safer
    packs = _chunk(seeds, 6) or [[]]
    queries = []
    for pack in packs:
        parts = []
        if pack: parts.append(" ".join(_phrase(p) for p in pack))
        if hints: parts.append(" ".join(hints))
        if base_soft: parts.append(base_soft)
        q = _trim_len(" ".join(parts).strip(), 500)
        if q: queries.append(q)
    return queries or ([base_soft] if base_soft else [])


def _build_s2_queries(spec: QuerySpec, base_boolean: str) -> List[str]:
    """Semantic Scholar: prefer plain text/quoted phrases; avoid boolean operators."""
    seeds = []
    seeds += [p for p in (spec.must_phrases or []) if p.strip()]
    seeds += [p for p in (spec.any_phrases or []) if p.strip()]
    base_bow = _bag_of_words(base_boolean)
    packs = _chunk(seeds, 6) or [[]]
    queries = []
    for pack in packs:
        parts = []
        if pack: parts.append(" ".join(_phrase(p) for p in pack))
        if base_bow: parts.append(base_bow)
        q = _trim_len(" ".join(parts).strip(), 300)
        if q: queries.append(q)
    return queries or ([base_bow] if base_bow else [])


def _plan_queries_for_engine(engine: str, spec: QuerySpec, base_boolean: str) -> List[str]:
    e = engine.lower()
    if e == "pubmed":           return _build_pubmed_queries(spec, base_boolean)
    if e == "arxiv":            return _build_arxiv_queries(spec, base_boolean)
    if e == "openalex":         return _build_openalex_queries(spec, base_boolean)
    if e == "crossref":         return _build_crossref_queries(spec, base_boolean)
    if e == "semanticscholar":  return _build_s2_queries(spec, base_boolean)
    return [base_boolean] if base_boolean else []



def _force_engine(rows, engine_name: str):
    """Ensure every row has the engine field correctly set."""
    if not rows:
        return rows
    for r in rows:
        if not r.get("engine"):
            r["engine"] = engine_name
    return rows

def _normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    d = doi.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    return d.lower()

def _normalize_row(r: Dict[str, str]) -> Dict[str, str]:
    # Normalize common fields to reduce dupes + weird chars
    r = dict(r)
    r["title"] = _clean_text(r.get("title", ""))
    r["venue"] = _clean_text(r.get("venue", ""))
    r["abstract"] = _clean_text(r.get("abstract", ""))
    r["authors|;|"] = _clean_text(r.get("authors|;|", ""))
    r["doi"] = _normalize_doi(r.get("doi"))
    # Trim url whitespace/control chars but don't over-process
    url = (r.get("url") or "").strip()
    url = re.sub(r"[\x00-\x1F\x7F]", "", url)
    r["url"] = url
    return r

def _max_pages(engine: str) -> int:
    # Allow engine-specific override, else global, else 10
    eng_key = f"LIT_{engine.upper()}_MAX_PAGES"
    try:
        if os.getenv(eng_key):
            return int(os.getenv(eng_key))
        if os.getenv("LIT_MAX_PAGES"):
            return int(os.getenv("LIT_MAX_PAGES"))
    except Exception:
        pass
    return 10


def _ensure_csv2_header(path: str):
    """
    Create the CSV file with header if it doesn't exist yet, and create parent dir.
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except Exception as e:
        print(f"[io] mkdirs for {path} failed: {e}")
    if os.path.exists(path):
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore")
        w.writeheader()


CSV2_HEADER = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score"
]


from dataclasses import dataclass

@dataclass
class QuerySpec:
    run_id: str
    boolean_queries: List[str]
    seed_terms: List[str]
    expanded_terms: List[str]
    # Optional structured fields (safe defaults):
    years_from: Optional[int] = None
    years_to: Optional[int] = None
    must_phrases: List[str] = None
    any_phrases: List[str] = None
    exclude_terms: List[str] = None
    title_bias_terms: List[str] = None
    domains: List[str] = None
    doc_types: List[str] = None
    venues: List[str] = None

def _to_int_or_none(v: str | None) -> Optional[int]:
    if not v: return None
    v = str(v).strip()
    return int(v) if v.isdigit() else None

def _get_list(row: Dict[str,str], key: str) -> List[str]:
    # tolerant: return [] if column not present
    if key in row:
        return to_list(row.get(key,""))
    return []

def _read_keywords_csv_rich(csv_path: str) -> QuerySpec:
    with open(csv_path, "r", encoding="utf-8") as f:
        last = list(csv.DictReader(f))[-1]  # take most recent row
    return QuerySpec(
        run_id = last.get("run_id","").strip(),
        boolean_queries = to_list(last.get("boolean_queries|;|","")),
        seed_terms = to_list(last.get("seed_terms|;|","")),
        expanded_terms = to_list(last.get("expanded_terms|;|","")),
        years_from = _to_int_or_none(last.get("years_from")),
        years_to = _to_int_or_none(last.get("years_to")),
        must_phrases = _get_list(last, "must_phrases|;|"),
        any_phrases = _get_list(last, "any_phrases|;|"),
        exclude_terms = _get_list(last, "exclude_terms|;|"),
        title_bias_terms = _get_list(last, "title_bias_terms|;|"),
        domains = _get_list(last, "domains|;|"),
        doc_types = _get_list(last, "doc_types|;|"),
        venues = _get_list(last, "venues|;|"),
    )

def _phrase(s: str) -> str:
    s = s.strip()
    if not s: return s
    # keep existing quotes; else quote multi-word phrases
    return s if (s.startswith('"') and s.endswith('"')) or (" " not in s) else f'"{s}"'

def _chunk(lst: List[str], n: int) -> List[List[str]]:
    # chunk list into groups of n (for micro-queries)
    return [lst[i:i+n] for i in range(0, len(lst), n)]

# === Engine-specific query sanitizers ===
_BOOL_OP = re.compile(r'\b(AND|OR|NOT)\b', re.I)

def _strip_label_and_parens(q: str) -> str:
    """Drop a leading [Label] and outer parens; keep quotes; collapse whitespace."""
    if not q: return q
    q = re.sub(r'^\s*\[[^\]]+\]\s*', '', q).strip()
    # remove a single pair of wrapping parentheses if they wrap the whole string
    if q.startswith("(") and q.endswith(")"):
        # only if balanced at top-level
        depth=0; balanced=True
        for i,ch in enumerate(q):
            if ch=="(":
                depth+=1
            elif ch==")":
                depth-=1
                if depth<0: balanced=False; break
            if i<len(q)-1 and depth==0 and i!=len(q)-2:
                balanced=False
        if balanced:
            q = q[1:-1].strip()
    return re.sub(r'\s+', ' ', q).strip()

def _bag_of_words(q: str) -> str:
    """Remove boolean/parens → space-separated terms, keep quoted phrases."""
    if not q: return q
    s = _strip_label_and_parens(q)
    s = _BOOL_OP.sub(' ', s)
    s = re.sub(r'[()]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def _trim_len(s: str, max_len: int = 300) -> str:
    """APIs like OpenAlex/S2 tolerate ~200-500 chars. Trim politely."""
    if not s or len(s) <= max_len: return s
    return s[:max_len].rstrip()


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
        r = _normalize_row(r)
        doi = r["doi"]
        title = r["title"].lower()
        year = (r.get("year", "") or "").strip()
        if doi:
            key = f"doi::{doi}"
        else:
            key = f"title::{title}::{year}"
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out



def run(
    csv1_path: str,
    researcher: Optional[str] = None,
    per_source: int = 500,
    include: Optional[List[str]] = None
):
    """
    csv1_path: path to prompt_to_keywords.csv (from Stage A)
    per_source: max items per engine per query (soft limit)
    include: subset of engines to use; default = all
    """
    if not os.path.exists(csv1_path):
        return False, f"CSV-1 not found: {csv1_path}"

    # Read CSV-1 and guarantee we have a run_id even if CSV-1 read fails
    try:
        spec = _read_keywords_csv_rich(csv1_path)
    except Exception as e:
        fallback_run_id = datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        print(f"[warn] Failed to read CSV-1: {e} — continuing with fallback run_id={fallback_run_id}")
        spec = QuerySpec(run_id=fallback_run_id, boolean_queries=[], seed_terms=[], expanded_terms=[])


    run_id = (spec.run_id or "").strip()
    if not run_id:
        run_id = datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        print(f"[warn] Empty run_id in CSV-1 — using fallback run_id={run_id}")

    qs = spec.boolean_queries or []

    if not qs:
        return False, "No boolean queries found in CSV-1."

    # Lazy import so we can surface clear dependency errors in the GUI
    try:
        from core.lit import sources as SRC
    except Exception as e:
        msg = str(e)
        if "No module named 'requests'" in msg:
            return False, ("Dependency missing: 'requests'. Install it in this environment and retry.\n"
                           "Example (PowerShell):\n"
                           '  & "C:\\Post-doc Work\\Ailys\\venv\\Scripts\\python.exe" -m pip install requests')
        return False, f"Could not import search sources: {msg}"

    paths = run_dirs(run_id) or {}
    # Hard fallback if the helper failed or returned blanks
    default_root = os.path.join(os.getcwd(), "runs", run_id)
    paths.setdefault("csv", os.path.join(default_root, "csv"))
    paths.setdefault("raw", os.path.join(default_root, "raw"))
    paths.setdefault("logs", os.path.join(default_root, "logs"))

    # ensure dirs
    for key in ("csv", "raw", "logs"):
        try:
            os.makedirs(paths[key], exist_ok=True)
        except Exception as e:
            print(f"[io] could not create output dir for {key}: {e}")


    # Create a fresh, unique subfolder per invocation to avoid overwrites.
    # Example: runs/<run_id>/attempt_2025-10-21_15-03-42
    attempt_stamp = datetime.datetime.utcnow().strftime("attempt_%Y-%m-%d_%H-%M-%S")
    for key in ("csv", "raw", "logs"):
        # Re-root each path into a unique attempt folder
        base_dir = paths[key]
        unique_dir = os.path.join(base_dir, attempt_stamp)
        try:
            os.makedirs(unique_dir, exist_ok=True)
            paths[key] = unique_dir
        except Exception as e:
            print(f"[io] could not create unique attempt dir for {key}: {e}")
    _dbg(f"Writing outputs to unique attempt folder: csv={paths['csv']} raw={paths['raw']} logs={paths['logs']}")


    queries_log_path = os.path.join(paths["logs"], "queries_emitted.log")
    results_log_path = os.path.join(paths["logs"], "results_summary.log")

    stop_flag_path = os.path.join(paths["logs"], "STOP")
    # expose to GUI so a Stop button can touch the file
    try: os.environ["LIT_STOP_FLAG_PATH"] = stop_flag_path
    except Exception: pass

    out_csv = os.path.join(paths["csv"], "search_results_raw.csv")

    # Streaming (append-as-we-go) file for progress monitoring (non-deduped)
    out_partial = os.path.join(paths["csv"], "search_results_partial.csv")
    _ensure_csv2_header(out_partial)

    # Streaming enrichment (as abstracts get filled)
    out_enriched = os.path.join(paths["csv"], "search_results_enriched_partial.csv")
    _ensure_csv2_header(out_enriched)

    engines = include or ["OpenAlex","Crossref","arXiv","PubMed","SemanticScholar"]
    collected: List[Dict[str,str]] = []

    engine_counts = defaultdict(int)
    engine_errors = defaultdict(int)

    engine_attempts = defaultdict(int)
    engine_success = defaultdict(int)

    # checkpoint controls (env overrideable)
    try:
        _CP_ROWS = max(1, int(os.getenv("LIT_CHECKPOINT_ROWS", "200")))
    except Exception:
        _CP_ROWS = 200
    try:
        _CP_SEC = max(5, int(os.getenv("LIT_CHECKPOINT_SEC", "60")))
    except Exception:
        _CP_SEC = 60

    last_cp_ts = time.time()
    since_last_cp = 0

    def _maybe_checkpoint(force: bool = False):
        nonlocal last_cp_ts, since_last_cp
        now = time.time()
        if force or (since_last_cp >= _CP_ROWS) or ((now - last_cp_ts) >= _CP_SEC):
            # Write a deduped snapshot to a checkpoint file and ensure final file exists
            try:
                snapshot = _dedupe(collected)
                cp_path = os.path.join(paths["csv"], "search_results_raw.checkpoint.csv")
                _write_csv2(cp_path, snapshot)
            except Exception as e:
                print(f"[checkpoint] failed: {e}")
            last_cp_ts = now
            since_last_cp = 0


    # Helpful hints if missing identifiers (some APIs throttle or behave oddly)
    if not (os.getenv("OPENALEX_EMAIL", "").strip()):
        print("[hint] OPENALEX_EMAIL not set; consider adding a mailto for OpenAlex polite usage.")
    if not (os.getenv("CROSSREF_MAILTO", "").strip()):
        print("[hint] CROSSREF_MAILTO not set; consider adding a mailto for Crossref polite usage.")
    if not (os.getenv("NCBI_API_KEY", "").strip()):
        print("[hint] NCBI_API_KEY not set; PubMed E-utilities may be slower/limited.")


    def _enrich_missing_abstracts(rows: List[Dict[str, str]]) -> None:
        """
        Fills missing/short abstracts in-place using DOI/PMID lookups and a light scrape fallback.
        Streams progress to 'search_results_enriched_partial.csv'.
        """
        for r in rows:
            # Clean title/venue that may have weird chars
            r["title"] = _clean_text(r.get("title", ""))
            r["venue"] = _clean_text(r.get("venue", ""))
            r["authors|;|"] = _clean_text(r.get("authors|;|", ""))

            # If an abstract exists and looks real, keep it
            existing = _clean_text(r.get("abstract", ""))
            if existing and len(existing) >= 120:
                r["abstract"] = existing
                continue

            doi = (r.get("doi") or "").strip().lower()
            url = r.get("url") or ""
            new_abs = None

            # Try DOI-based lookups first
            if doi:
                new_abs = _fetch_abstract_by_doi(doi)

            # PubMed by PMID if present in URL (or if Crossref mapped it in DOI lookup path)
            if not new_abs:
                pmid = _extract_pmid_from_url(url)
                if pmid:
                    new_abs = _fetch_pubmed_abstract(pmid)

            # Fallback: quick page scrape
            if (not new_abs) and url:
                new_abs = _scrape_page_for_abstract(url)

            if new_abs:
                r["abstract"] = new_abs
                # Stream this improved row so you can see enrichment progress
                _write_csv2(out_enriched, [r])


    # ---- Approval gate (network-only; NO LLM TOKENS) -------------------------
    def _collect():
        nonlocal collected, since_last_cp

        if _should_stop(stop_flag_path):
            _dbg("Stop requested before collection started; exiting early.")
            return True

        # helper to write queries to a log file so we can inspect real requests
        def _log_query(engine: str, q: str):
            try:
                with open(queries_log_path, "a", encoding="utf-8") as lf:
                    lf.write(f"[{engine}] {q}\n")
            except Exception:
                pass

        for base_q in qs:
            term_origin = "seed/expanded-mix"

            # Normalize a base query once; planners will customize further.
            base_q_clean = _strip_label_and_parens(base_q)

            if "OpenAlex" in engines:
                try:
                    engine = "OpenAlex"
                    new_rows: List[Dict[str,str]] = []
                    for q in _plan_queries_for_engine(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break

                        if len(new_rows) >= per_source: break
                        _log_query(engine, q)
                        engine_attempts[engine] += 1
                        t0 = time.time()
                        try:
                            r = SRC.search_openalex(
                                run_id, q, term_origin,
                                per_page=min(per_source - len(new_rows), 25),
                                max_pages=_max_pages("OpenAlex")
                            )
                            n = len(r or [])
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] OK | {n} rows | {secs:.2f}s | {q}")
                            _dbg(f"{engine} OK {n} rows in {secs:.2f}s :: {q}")
                            engine_success[engine] += 1
                        except Exception as e:
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] ERR | 0 rows | {secs:.2f}s | {q} | {type(e).__name__}: {e}")
                            _dbg(f"{engine} ERR {secs:.2f}s :: {type(e).__name__}: {e} :: {q}")
                            r = None

                        r = _force_engine(r, engine)
                        new_rows += (r or [])
                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return True

                except Exception as e:
                    engine_errors["OpenAlex"] += 1
                    print(f"[collect][OpenAlex] error: {e}")

            if "Crossref" in engines:
                try:
                    engine = "Crossref"
                    new_rows: List[Dict[str,str]] = []
                    for q in _plan_queries_for_engine(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break

                        if len(new_rows) >= per_source: break
                        _log_query(engine, q)
                        engine_attempts[engine] += 1
                        t0 = time.time()
                        try:
                            r = SRC.search_crossref(
                                run_id, q, term_origin,
                                rows=min(per_source - len(new_rows), 50)
                            )
                            n = len(r or [])
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] OK | {n} rows | {secs:.2f}s | {q}")
                            _dbg(f"{engine} OK {n} rows in {secs:.2f}s :: {q}")
                            engine_success[engine] += 1
                        except Exception as e:
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] ERR | 0 rows | {secs:.2f}s | {q} | {type(e).__name__}: {e}")
                            _dbg(f"{engine} ERR {secs:.2f}s :: {type(e).__name__}: {e} :: {q}")
                            r = None

                        r = _force_engine(r, engine)
                        new_rows += (r or [])
                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return True

                except Exception as e:
                    engine_errors["Crossref"] += 1
                    print(f"[collect][Crossref] error: {e}")

            if "arXiv" in engines:
                try:
                    engine = "arXiv"
                    new_rows: List[Dict[str,str]] = []
                    # IMPORTANT: do NOT simplify; use planner output
                    for q in _plan_queries_for_engine(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break

                        if len(new_rows) >= per_source: break
                        _log_query(engine, q)
                        engine_attempts[engine] += 1
                        t0 = time.time()
                        try:
                            r = SRC.search_arxiv(
                                run_id, q, term_origin,
                                max_results=min(per_source - len(new_rows), 50)
                            )
                            n = len(r or [])
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] OK | {n} rows | {secs:.2f}s | {q}")
                            _dbg(f"{engine} OK {n} rows in {secs:.2f}s :: {q}")
                            engine_success[engine] += 1
                        except Exception as e:
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] ERR | 0 rows | {secs:.2f}s | {q} | {type(e).__name__}: {e}")
                            _dbg(f"{engine} ERR {secs:.2f}s :: {type(e).__name__}: {e} :: {q}")
                            r = None

                        r = _force_engine(r, engine)
                        new_rows += (r or [])
                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return True

                except Exception as e:
                    engine_errors["arXiv"] += 1
                    print(f"[collect][arXiv] error: {e}")

            if "PubMed" in engines:
                try:
                    engine = "PubMed"
                    new_rows: List[Dict[str,str]] = []
                    # IMPORTANT: do NOT simplify; use planner output with field tags
                    for q in _plan_queries_for_engine(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break

                        if len(new_rows) >= per_source: break
                        _log_query(engine, q)
                        _log_query(engine, q)
                        engine_attempts[engine] += 1
                        t0 = time.time()
                        try:
                            r = SRC.search_pubmed(
                                run_id, q, term_origin,
                                retmax=min(per_source - len(new_rows), 50)
                            )
                            n = len(r or [])
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] OK | {n} rows | {secs:.2f}s | {q}")
                            _dbg(f"{engine} OK {n} rows in {secs:.2f}s :: {q}")
                            engine_success[engine] += 1
                        except Exception as e:
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] ERR | 0 rows | {secs:.2f}s | {q} | {type(e).__name__}: {e}")
                            _dbg(f"{engine} ERR {secs:.2f}s :: {type(e).__name__}: {e} :: {q}")
                            r = None

                        r = _force_engine(r, engine)
                        new_rows += (r or [])
                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return True

                except Exception as e:
                    engine_errors["PubMed"] += 1
                    print(f"[collect][PubMed] error: {e}")

            if "SemanticScholar" in engines:
                try:
                    engine = "SemanticScholar"
                    new_rows: List[Dict[str,str]] = []
                    for q in _plan_queries_for_engine(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break

                        if len(new_rows) >= per_source: break
                        _log_query(engine, q)
                        engine_attempts[engine] += 1
                        t0 = time.time()
                        try:
                            r = SRC.search_semantic_scholar(
                                run_id, q, term_origin,
                                limit=min(per_source - len(new_rows), 50)
                            )
                            n = len(r or [])
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] OK | {n} rows | {secs:.2f}s | {q}")
                            _dbg(f"{engine} OK {n} rows in {secs:.2f}s :: {q}")
                            engine_success[engine] += 1
                        except Exception as e:
                            secs = time.time() - t0
                            _write_log_line(results_log_path, f"[{engine}] ERR | 0 rows | {secs:.2f}s | {q} | {type(e).__name__}: {e}")
                            _dbg(f"{engine} ERR {secs:.2f}s :: {type(e).__name__}: {e} :: {q}")
                            r = None

                        r = _force_engine(r, engine)
                        new_rows += (r or [])
                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return True

                except Exception as e:
                    engine_errors["SemanticScholar"] += 1
                    print(f"[collect][SemanticScholar] error: {e}")

        return True


    # Make the approval description explicit: no LLM spend; show scale
    req_count = len(qs) * len(engines)
    desc = (f"Literature Collection (CSV-2) — NO LLM TOKENS | "
            f"engines={','.join(engines)} | queries={len(qs)} | requests≈{req_count}")

    # Approve once for CSV-2; then run all downstream non-token API calls without
    # further approvals by temporarily switching the queue to 'auto' for _collect.
    ok = approvals.request_approval(
        description=desc,
        call_fn=lambda ov=None: _with_temp_approval_mode("auto", _collect),
        timeout=None
    )
    if not ok:
        return False, "Approval denied or failed."

    # ---- Enrichment phase (no LLM) --------------------------------------------
    # Only enrich items that are missing/short abstracts.
    try:
        _enrich_missing_abstracts(collected)

    except Exception as e:
        print(f"[enrich] non-fatal error: {e}")

    # Always produce a final CSV (even if empty), and force one last checkpoint
    try:
        _maybe_checkpoint(True)
    except Exception:
        pass

    # ---- Finalize outputs -----------------------------------------------------
    try:
        deduped = _dedupe(collected)
    except Exception as e:
        print(f"[finalize] dedupe failed, writing raw collected: {e}")
        deduped = list(collected)

    try:
        # ensure header exists, then overwrite cleanly
        _ensure_csv2_header(out_csv)
        try:
            if os.path.exists(out_csv):
                os.remove(out_csv)
        except Exception:
            pass
        _write_csv2(out_csv, deduped)
    except Exception as e:
        print(f"[finalize] write failed: {e}")

    # Coverage summary
    try:
        total = sum(engine_counts.values())
        print("[summary] Engine totals:", dict(engine_counts), "grand_total:", total)

        try:
            attempts = dict(engine_attempts)
            success = dict(engine_success)
            failures = {k: attempts.get(k, 0) - success.get(k, 0) for k in attempts.keys()}
            print("[summary] Engine attempts:", attempts)
            print("[summary] Engine success:", success)
            print("[summary] Engine failures:", failures)
        except Exception:
            pass


        if any(engine_errors.values()):
            print("[summary] Engine errors:", dict(engine_errors))
    except Exception:
        pass

    # Last-chance safety: guarantee folder + at least headers exist if we crashed before writing
    try:
        if paths.get('csv'):
            os.makedirs(paths['csv'], exist_ok=True)
            _ensure_csv2_header(os.path.join(paths['csv'], 'search_results_partial.csv'))
            _ensure_csv2_header(os.path.join(paths['csv'], 'search_results_enriched_partial.csv'))
            _ensure_csv2_header(os.path.join(paths['csv'], 'search_results_raw.csv'))
    except Exception as e:
        print(f"[guard] could not ensure output files: {e}")

    msg = f"CSV written: {out_csv}  (raw: {len(collected)}, deduped: {len(deduped)})"
    print(msg)
    return True, msg


