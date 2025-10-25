# tasks/lit_search_collect.py
from __future__ import annotations

import os, csv, datetime, re, time, html, unicodedata, itertools
# Optional .env loader (no hard dependency). If python-dotenv is installed,
# this will read a local .env so os.getenv(...) works without exporting shell vars.
try:
    from dotenv import load_dotenv
    # override=False so real OS env stays authoritative if both are present
    load_dotenv(override=False)
except Exception:
    pass

from collections import defaultdict
from typing import Optional, Dict, List, Tuple
from core.lit.utils import to_list, run_dirs
import core.approval_queue as approvals

def _infer_prefixed_run_root(csv_path: str) -> str | None:
    """
    Walk up from csv_path to find a directory named like
    YYYY-MM-DDTHH-MM-SSZ or YYYY-MM-DDTHH-MM-SSZ_<prefix>, and return that path.
    If none found, return None.
    """
    try:
        p = os.path.abspath(csv_path or "")
        d = os.path.dirname(p)
        stamp_re = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z(?:_.+)?$')
        while d and d != os.path.dirname(d):
            base = os.path.basename(d)
            if stamp_re.match(base):
                return d
            d = os.path.dirname(d)
    except Exception:
        pass
    return None


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
    """
    PubMed:
      - Primary (strict) set: preserve boolean/phrases; Title/Abstract tags; chunk OR lists.
      - Fallback (relaxed) set: add a small number of "bag-of-words in Title/Abstract"
        queries that DO NOT over-constrain by aggressively combining many terms.
    Both sets are returned (strict first), and later de-dup will handle overlaps.
    Tune via env:
      - LIT_PUBMED_RELAXED: "0" to disable relaxed fallback (default enabled)
      - LIT_PUBMED_ANY_CHUNK: size for OR chunking (default 4)
    """
    queries: List[str] = []

    # --- strict set ---
    try:
        any_chunk_n = max(1, int(os.getenv("LIT_PUBMED_ANY_CHUNK", "4")))
    except Exception:
        any_chunk_n = 4

    must = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.must_phrases or []) if p.strip()]
    anys = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.any_phrases or []) if p.strip()]
    nots = [f'{_phrase(p)}[Title/Abstract]' for p in (spec.exclude_terms or []) if p.strip()]
    any_chunks = _chunk(anys, any_chunk_n) if anys else [[]]

    base_part = f"({base_boolean})" if base_boolean else ""

    for ch in any_chunks:
        parts = []
        if must: parts.append("(" + " AND ".join(must) + ")")
        if ch:   parts.append("(" + " OR ".join(ch) + ")")
        if base_part: parts.append(base_part)
        if nots: parts.append("NOT (" + " OR ".join(nots) + ")")
        q = " AND ".join([p for p in parts if p])
        if q.strip():
            queries.append(q)

    # If there were no strict queries constructed, at least include base_boolean
    if not queries and base_boolean:
        queries.append(base_boolean)

    # --- relaxed fallback ---
    relaxed_enabled = (os.getenv("LIT_PUBMED_RELAXED", "1") != "0")
    if relaxed_enabled:
        # Build a small set of simpler TA queries that broaden recall.
        seeds = []
        seeds += [p for p in (spec.must_phrases or []) if p.strip()]
        seeds += [p for p in (spec.any_phrases or []) if p.strip()]
        seeds += [p for p in (spec.title_bias_terms or []) if p.strip()]

        # Keep it compact: unique phrases, first ~10 singles and a few pairs
        seen = set()
        singles = []
        for s in seeds:
            k = s.strip().lower()
            if k and k not in seen:
                seen.add(k)
                singles.append(s)
            if len(singles) >= 10:
                break

        # Singles
        for s in singles:
            queries.append(f'{_phrase(s)}[Title/Abstract]')

        # A handful of pairs to loosen conjunction effects
        pair_limit = 8
        c = 0
        for i in range(len(singles)):
            for j in range(i+1, len(singles)):
                if c >= pair_limit:
                    break
                a = _phrase(singles[i])
                b = _phrase(singles[j])
                queries.append(f'({a}[Title/Abstract]) AND ({b}[Title/Abstract])')
                c += 1
            if c >= pair_limit:
                break

        # Finally, a plain bag-of-words base (unfielded) to catch strays
        bow = _bag_of_words(base_boolean)
        if bow:
            queries.append(bow)

    # De-duplicate while preserving order
    uniq = []
    seen = set()
    for q in queries:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k); uniq.append(q)
    return uniq


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

def _first_author_last(authors_field: str) -> str:
    """
    Extract a cleaned 'first author last name' from an authors field like:
    'Fiore, Stephen M.; Smith, J.; ...' or 'Stephen M. Fiore; J. Smith'
    Best-effort, tolerant to separators and ordering.
    """
    if not authors_field:
        return ""
    s = _clean_text(authors_field)
    # Split on common delimiters between authors
    parts = re.split(r"[;|,]\s*(?=[A-Z][^;|,]*)|;\s+| \|\| |\|;|;", s)
    if not parts:
        parts = [s]
    first = parts[0].strip()

    # Handle "Last, First" vs "First Last"
    # Case 1: "Fiore, Stephen M."
    m = re.match(r"^\s*([A-Za-z'`-]+)\s*,\s*.+$", first)
    if m:
        last = m.group(1)
    else:
        # Case 2: "Stephen M. Fiore"
        tokens = re.split(r"\s+", first)
        # drop initials like M., J., etc.
        tokens = [t for t in tokens if not re.match(r"^[A-Z]\.?$", t)]
        last = tokens[-1] if tokens else ""

    last = unicodedata.normalize("NFKC", last)
    last = re.sub(r"[^A-Za-z'`-]", "", last)
    return last.lower()

def _norm_title(title: str) -> str:
    """Lightweight normalization for titles for hashing/blocking."""
    if not title:
        return ""
    t = _clean_text(title)
    t = t.lower()
    # remove punctuation, keep letters/digits/spaces
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _title_prefix_key(norm_title: str, n: int = None) -> str:
    """
    Use the first N characters of the normalized title as a blocking key.
    Tunable via env LIT_TITLE_PREFIX (default 12).
    """
    try:
        if n is None:
            n = int(os.getenv("LIT_TITLE_PREFIX", "12"))
    except Exception:
        n = 12
    if not norm_title:
        return ""
    return norm_title[:n]

def _fuzzy_sim(a: str, b: str) -> float:
    """
    Similarity (0..1). Use rapidfuzz if available; fallback to a simple token overlap.
    """
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return 0.0
    # Try rapidfuzz (fast and robust)
    try:
        from rapidfuzz import fuzz
        return fuzz.token_set_ratio(a, b) / 100.0
    except Exception:
        pass
    # Fallback: token Jaccard+ containment
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    cont = inter / max(1, min(len(sa), len(sb)))
    jac = inter / max(1, union)
    return 0.5 * cont + 0.5 * jac


def _normalize_row(r: Dict[str, str]) -> Dict[str, str]:
    # Normalize common fields to reduce dupes + weird chars
    r = dict(r)
    r["title"] = _clean_text(r.get("title", ""))
    r["venue"] = _clean_text(r.get("venue", ""))
    r["abstract"] = _clean_text(r.get("abstract", ""))
    r["authors|;|"] = _clean_text(r.get("authors|;|", ""))
    r["doi"] = _normalize_doi(r.get("doi"))

    # First author last (for blocking); safe if authors|;| is absent/empty
    if not r.get("first_author_last"):
        r["first_author_last"] = _first_author_last(r.get("authors|;|", "")) or ""

    # Normalized title + prefix (used only inside dedupe; no need to emit both)
    r["_norm_title"] = _norm_title(r.get("title", ""))
    r["_title_prefix"] = _title_prefix_key(r["_norm_title"])

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

def _filter_kwargs_for_fn(fetch_fn, kwargs: dict) -> dict:
    """
    Keep only kwargs that the target function actually accepts.
    Prevents TypeError: got an unexpected keyword argument 'page'/ 'offset' / etc.
    """
    try:
        import inspect
        sig = inspect.signature(fetch_fn)
        allowed = set(sig.parameters.keys())
        return {k: v for k, v in (kwargs or {}).items() if k in allowed}
    except Exception:
        # If introspection fails, pass only the bare minimum common args
        safe = {}
        for k in ("run_id", "q", "term_origin", "per_page", "rows", "max_results", "retmax", "limit", "max_pages"):
            if k in kwargs:
                safe[k] = kwargs[k]
        return safe


def _effective_per_source(per_source: int, engine: str) -> int:
    """
    Final per-engine cap. Prefers env overrides if larger.
    - LIT_PER_SOURCE_MAX applies globally.
    - LIT_<ENGINE>_PER_SOURCE_MAX applies per engine (e.g., LIT_PUBMED_PER_SOURCE_MAX).
    Defaults to a very high limit to avoid silently truncating recall.
    """
    try:
        eng_key = f"LIT_{engine.upper()}_PER_SOURCE_MAX"
        env_eng = int(os.getenv(eng_key, "0") or "0")
        env_global = int(os.getenv("LIT_PER_SOURCE_MAX", "0") or "0")
    except Exception:
        env_eng = 0
        env_global = 0
    hard_default = 100000  # super-high cap that you asked for
    cap = max(per_source or 0, env_global, env_eng, hard_default)
    return cap


def _engine_page_size(engine: str, remaining: int) -> int:
    """
    Decide a sensible page size per engine while respecting remaining budget.
    Tuned conservatively to stay within public API norms.
    """
    e = (engine or "").lower()
    # Safe upper-bounds per call
    defaults = {
        "openalex": 200,        # cursor pages up to ~200
        "crossref": 1000,       # Crossref rows can be large; 1000 is safe & performant
        "arxiv": 200,           # arXiv returns 200/page comfortably
        "pubmed": 10000,        # ESearch/EFetch can handle large retmax; still govern by STOP
        "semanticscholar": 100  # S2 Graph API: typical public cap ~100/page
    }
    page_size = defaults.get(e, 200)
    if remaining > 0:
        page_size = min(page_size, remaining)
    return max(1, page_size)

def _call_source_positional(fetch_fn, run_id: str, q: str, term_origin: str, **kwargs):
    """
    Call source with the first three args positionally to match legacy SRC signatures.
    Remaining parameters (per_page/rows/retmax/limit/page/offset/max_pages, etc.) go as kwargs.
    """
    return fetch_fn(run_id, q, term_origin, **kwargs)


def _page_loop(fetch_fn, engine: str, run_id: str, query: str, term_origin: str,
               base_kwargs: dict, size_param: str,
               max_pages: int, per_source_cap: int, results_log_path: str,
               queries_log_path: str, engine_attempts, engine_success) -> list:
    """
    Generic pagination loop that repeatedly calls the engine fetch function.

    IMPORTANT: We pass (run_id, query, term_origin) POSITIONALLY to preserve the
    original SRC.search_* calling convention. Only paging knobs go as kwargs.

    SAFETY:
      - Only pass kwargs the function accepts (signature-aware).
      - Stop if no growth in unique items to avoid infinite loops on non-paginating sources.
    """
    if not (query or "").strip():
        _write_log_line(results_log_path, f"[{engine}] SKIP | empty query")
        return []

    rows: list = []
    page = 1
    offset = 0
    seen_keys = set()  # to detect growth; work_id/doi/title tuple

    # We’ll compute page_size per iteration based on remaining budget
    while True:
        if _should_stop(os.getenv("LIT_STOP_FLAG_PATH", "")):
            _write_log_line(results_log_path, f"[{engine}] STOP requested; halting pagination.")
            break
        if len(rows) >= per_source_cap:
            _write_log_line(results_log_path, f"[{engine}] per_source_cap reached ({per_source_cap}); halting.")
            break
        if page > max_pages:
            _write_log_line(results_log_path, f"[{engine}] max_pages reached ({max_pages}); halting.")
            break

        remaining = max(0, per_source_cap - len(rows))
        page_size = _engine_page_size(engine, remaining)

        # Compose kwargs for this call
        kwargs = dict(base_kwargs or {})
        kwargs[size_param] = page_size
        kwargs.setdefault("page", page)
        kwargs.setdefault("offset", offset)
        # Only send kwargs the function can accept
        kwargs = _filter_kwargs_for_fn(fetch_fn, kwargs)

        engine_attempts[engine] += 1
        t0 = time.time()
        try:
            res = _call_source_positional(fetch_fn, run_id, query, term_origin, **kwargs) or []
            n = len(res)
            secs = time.time() - t0
            _write_log_line(results_log_path, f"[{engine}] OK | page={page} size={page_size} rows={n} | {secs:.2f}s | {query}")
            engine_success[engine] += 1
        except TypeError as e:
            # Signature mismatch: retry WITHOUT page/offset entirely
            try:
                kwargs2 = {k: v for k, v in kwargs.items() if k not in ("page", "offset")}
                res = _call_source_positional(fetch_fn, run_id, query, term_origin, **kwargs2) or []
                n = len(res)
                secs = time.time() - t0
                _write_log_line(results_log_path, f"[{engine}] OK(no-page) | size={page_size} rows={n} | {secs:.2f}s | {query} | note: {e}")
                engine_success[engine] += 1
            except Exception as e2:
                secs = time.time() - t0
                _write_log_line(results_log_path, f"[{engine}] ERR | size={page_size} | {secs:.2f}s | {query} | {type(e2).__name__}: {e2}")
                break
        except Exception as e:
            secs = time.time() - t0
            _write_log_line(results_log_path, f"[{engine}] ERR | page={page} size={page_size} | {secs:.2f}s | {query} | {type(e).__name__}: {e}")
            break

        if not res:
            # Nothing returned → stop
            break

        # Append only new items to detect growth for pagination safety
        new_any = False
        for r in res:
            doi = ((r or {}).get("doi") or "").strip().lower()
            wid = ((r or {}).get("work_id") or "").strip().lower()
            title = _norm_title((r or {}).get("title") or "")
            key = (doi, wid, title)
            if key not in seen_keys:
                seen_keys.add(key)
                rows.append(r)
                new_any = True

        # If we got fewer than requested OR no new unique items, stop
        if len(res) < page_size or not new_any:
            break

        page += 1
        offset += len(res)

    return rows

def _log_fetch_signature(fetch_fn, engine: str, results_log_path: str):
    try:
        import inspect
        allowed = sorted(list(inspect.signature(fetch_fn).parameters.keys()))
        _write_log_line(results_log_path, f"[{engine}] accepts kwargs: {allowed}")
    except Exception:
        pass


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


# Include a convenience column for blocking/dedup:
# - first_author_last: cleaned last name of first author (if parseable)
CSV2_HEADER = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score",
    "first_author_last"
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

def _is_simple_word_or_phrase(s: str) -> bool:
    """
    True if s is a single token or a 2-word phrase (after stripping quotes).
    We allow hyphenated words as 1 token.
    """
    if not s:
        return False
    s = s.strip().strip('"').strip("'")
    if not s:
        return False
    # collapse whitespace and split
    parts = re.sub(r'\s+', ' ', s).split(' ')
    return 1 <= len(parts) <= 2

def _simple_starter_terms(spec: QuerySpec) -> List[str]:
    """
    Build a pool of 1–2 word terms from CSV-1 fields.
    Priority: seed_terms > must_phrases > title_bias_terms > expanded_terms > any_phrases
    (We keep order and uniqueness.)
    """
    pools = [
        spec.seed_terms or [],
        spec.must_phrases or [],
        spec.title_bias_terms or [],
        spec.expanded_terms or [],
        spec.any_phrases or [],
    ]
    seen = set()
    out = []
    for pool in pools:
        for t in pool:
            t = (t or "").strip()
            if not t:
                continue
            # keep original phrase quoting if present
            if _is_simple_word_or_phrase(t):
                key = t.strip().lower()
                if key not in seen:
                    seen.add(key)
                    out.append(t)
    return out

def _merge_records(rows: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Merge duplicate records for the same work into a single best row.
    Preference order:
      - DOI present over missing
      - Longer abstract (cleaned), with a soft threshold preference (>=120 chars)
      - Non-empty venue/year/authors
      - Engine precedence as final tie-breaker
    """
    if not rows:
        return {}

    # Engine precedence (leftmost is preferred for ties on remaining fields)
    engine_rank = {e: i for i, e in enumerate(["OpenAlex","Crossref","SemanticScholar","PubMed","arXiv"])}

    # Normalize and collect candidates
    cands = []
    for r in rows:
        rr = _normalize_row(r)
        abs_text = rr.get("abstract") or ""
        abs_len = len(abs_text)
        doi_present = 1 if rr.get("doi") else 0
        venue_present = 1 if (rr.get("venue") or "").strip() else 0
        authors_present = 1 if (rr.get("authors|;|") or "").strip() else 0
        year_present = 1 if (rr.get("year") or "").strip() else 0
        engine_score = -engine_rank.get(rr.get("engine",""), 99)  # higher is better

        # Prefer abstracts over 120 chars; use two-tier score
        abs_tier = 2 if abs_len >= 120 else (1 if abs_len > 0 else 0)

        cands.append((
            doi_present,   # 0
            abs_tier,      # 1
            abs_len,       # 2
            venue_present, # 3
            authors_present,# 4
            year_present,  # 5
            engine_score,  # 6
            rr             # 7 actual row
        ))

    # Sort by tuple descending to pick the best
    cands.sort(reverse=True)
    best = dict(cands[0][7])  # start with the best base row

    # Fill any missing fields from others (do not overwrite non-empty)
    for _,_,_,_,_,_,_, rr in cands[1:]:
        for k in ["doi","url","title","venue","year","authors|;|","abstract","work_id","engine","query","term_origin","source_score","run_id"]:
            if not (best.get(k) or "").strip():
                v = (rr.get(k) or "").strip()
                if v:
                    best[k] = v
        # Replace abstract if the new one is clearly better
        old_abs = best.get("abstract") or ""
        new_abs = rr.get("abstract") or ""
        if len(new_abs) >= 120 and len(old_abs) < 120:
            best["abstract"] = new_abs
        elif len(new_abs) > len(old_abs) and len(old_abs) < 120:
            best["abstract"] = new_abs

    return _normalize_row(best)


def _merge_dedupe(rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
    """
    Two-stage, efficient dedup:
      1) Group by DOI (exact) → merge
      2) For items without DOI, block by:
         a) (first_author_last, year), and
         b) title prefix (first N chars of normalized title)
         Then run fuzzy compare WITHIN each block (threshold env: LIT_FUZZY_THRESH, default 0.88).
    This massively reduces pairwise comparisons while preserving duplicate recall
    (esp. DOI/no-DOI variants of the same paper).
    """
    # Normalize and split by DOI present vs absent
    with_doi: Dict[str, List[Dict[str,str]]] = {}
    no_doi: List[Dict[str,str]] = []

    for r in rows:
        rr = _normalize_row(r)
        doi = rr.get("doi", "")
        if doi:
            with_doi.setdefault(doi, []).append(rr)
        else:
            no_doi.append(rr)

    merged: List[Dict[str,str]] = []

    # --- Stage 1: DOI merges (fast path)
    for doi, bucket in with_doi.items():
        merged.append(_merge_records(bucket))

    if not no_doi:
        return merged

    # Threshold tuning via env
    try:
        FUZZY_THRESH = float(os.getenv("LIT_FUZZY_THRESH", "0.88"))
    except Exception:
        FUZZY_THRESH = 0.88

    # --- Stage 2: Block non-DOI items
    # Primary block: (first_author_last, year)
    # Secondary block inside that: _title_prefix
    primary_blocks: Dict[tuple, List[Dict[str,str]]] = {}
    for rr in no_doi:
        key = (
            (rr.get("first_author_last") or ""),
            (rr.get("year") or "").strip()
        )
        primary_blocks.setdefault(key, []).append(rr)

    # Merge each primary block
    for primary_key, p_bucket in primary_blocks.items():
        if len(p_bucket) == 1:
            merged.append(p_bucket[0])
            continue

        # Secondary blocks by title prefix
        secondary: Dict[str, List[Dict[str,str]]] = {}
        for rr in p_bucket:
            secondary.setdefault(rr.get("_title_prefix", ""), []).append(rr)

        # For each secondary bucket, do local fuzzy clustering
        for sec_key, s_bucket in secondary.items():
            if len(s_bucket) == 1:
                merged.append(s_bucket[0])
                continue

            # Greedy clustering: pick a seed, pull in all above threshold, merge → repeat
            s_bucket = list(s_bucket)  # shallow copy
            visited = [False] * len(s_bucket)

            for i in range(len(s_bucket)):
                if visited[i]:
                    continue
                seed = s_bucket[i]
                cluster = [seed]
                visited[i] = True
                t0 = seed.get("_norm_title", "")
                for j in range(i + 1, len(s_bucket)):
                    if visited[j]:
                        continue
                    cand = s_bucket[j]
                    # Require same year and strong title similarity
                    sim = _fuzzy_sim(t0, cand.get("_norm_title", ""))
                    if sim >= FUZZY_THRESH:
                        cluster.append(cand)
                        visited[j] = True
                if len(cluster) == 1:
                    merged.append(seed)
                else:
                    merged.append(_merge_records(cluster))

    # Final clean-up: drop transient internal fields before writing
    for r in merged:
        r.pop("_norm_title", None)
        r.pop("_title_prefix", None)
    return merged



def _build_simple_queries(spec: QuerySpec, max_single: int = 30, max_pairs: int = 30) -> List[str]:
    """
    Produce a list of very simple queries to probe breadth first:
      - Single 1–2 word tokens/phrases (capped)
      - Then 2-term combos (joined with space), also capped
    The engines will interpret these as broad bag-of-words / ti/abs matches depending on their API.
    """
    terms = _simple_starter_terms(spec)
    singles = terms[:max_single]

    # build 2-term combos while avoiding very long phrases
    pairs = []
    for a, b in itertools.combinations(singles, 2):
        a_clean = a.strip().strip('"')
        b_clean = b.strip().strip('"')
        # keep pair if each element is itself "simple"
        if _is_simple_word_or_phrase(a_clean) and _is_simple_word_or_phrase(b_clean):
            pairs.append(f'{_phrase(a_clean)} {_phrase(b_clean)}')
        if len(pairs) >= max_pairs:
            break

    # Keep quoting on multi-word elements, overall query is just space-joined tokens.
    starters = []
    starters.extend([_phrase(s) for s in singles])
    starters.extend(pairs)

    # Trim overlong starters (very rare, but safe)
    starters = [_trim_len(q, 200) for q in starters if q and q.strip()]
    # Deduplicate while preserving order
    seen = set(); uniq = []
    for q in starters:
        k = q.strip().lower()
        if k not in seen:
            seen.add(k); uniq.append(q)
    return uniq

def _plan_queries_staged(engine: str, spec: QuerySpec, base_boolean: str) -> List[str]:
    """
    Stage 1: super-simple starters (1–2 word queries).
    Stage 2: existing engine-specific planned queries (complex).
    We return starters first, then the planned set, de-duplicated.
    """
    # Allow environment overrides for scaling
    try:
        max_single = int(os.getenv("LIT_SIMPLE_SINGLE_MAX", "30"))
    except Exception:
        max_single = 30
    try:
        max_pairs = int(os.getenv("LIT_SIMPLE_PAIRS_MAX", "30"))
    except Exception:
        max_pairs = 30

    starters = _build_simple_queries(spec, max_single=max_single, max_pairs=max_pairs)
    planned  = _plan_queries_for_engine(engine, spec, base_boolean)

    # Merge starters first, then planned (unique, in order)
    seen = set(); out = []
    for q in starters + planned:
        if not q:
            continue
        k = q.strip().lower()
        if k not in seen:
            seen.add(k); out.append(q)
    return out


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

# def run_dedupe_only(
#     input_csv: str,
#     out_dir: Optional[str] = None,
#     label: str = "manual"
# ) -> Tuple[bool, str]:
#     """
#     Dedupe/merge an existing CSV of candidate rows (checkpoint, partial, or manually assembled).
#     - input_csv: path to a CSV with headers compatible with CSV2_HEADER (extra columns are ignored).
#     - out_dir: if provided, final CSV will be written there; else next to input.
#     - label: suffix to distinguish output (e.g., 'manual', 'checkpoint').
#
#     Produces:
#       - <out_dir>/search_results_final.<label>.csv
#     Returns (ok, message).
#     """
#     if not os.path.exists(input_csv):
#         return False, f"Input CSV not found: {input_csv}"
#
#     try:
#         rows = _read_csv_rows(input_csv)
#     except Exception as e:
#         return False, f"Could not read input CSV: {e}"
#
#     try:
#         deduped = _merge_dedupe(rows)
#     except Exception as e:
#         print(f"[dedupe_only] merge-dedupe failed, using simple dedupe: {e}")
#         try:
#             deduped = _dedupe(rows)
#         except Exception as e2:
#             return False, f"Simple dedupe failed: {e2}"
#
#     out_dir = out_dir or os.path.dirname(os.path.abspath(input_csv)) or "."
#     try:
#         os.makedirs(out_dir, exist_ok=True)
#     except Exception:
#         pass
#
#     out_final = os.path.join(out_dir, f"search_results_final.{label}.csv")
#     try:
#         if os.path.exists(out_final):
#             os.remove(out_final)
#     except Exception:
#         pass
#
#     _ensure_csv2_header(out_final)
#     _write_csv2(out_final, deduped)
#     return True, f"FINAL (dedup+merged) written: {out_final} | rows={len(deduped)}"


def run(
    csv1_path: str,
    researcher: Optional[str] = None,
    per_source: int = 500,
    include: Optional[List[str]] = None,
    save_prefix: Optional[str] = None,
):
    """
    csv1_path: path to prompt_to_keywords.csv (from Stage A)
    per_source: max items per engine per query (soft limit)
    include: subset of engines to use; default = all

    Foldering rules:
      • If csv1_path is under .../lit_runs/<timestamp>_<prefix>/prompt to keyword outputs/<prefix>/,
        the collection outputs will be written under that SAME prefixed run root:
          <timestamp>_<prefix>/candidate collection output/<prefix>/attempt_<UTC>/
          <timestamp>_<prefix>/candidate collection logs/<prefix>/attempt_<UTC>/
          <timestamp>_<prefix>/candidate collection raw/<prefix>/attempt_<UTC>/
      • If csv1_path does not live under a prefixed run root, we fall back to
        .../lit_runs/<timestamp> (from run_dirs), and append _<save_prefix> if provided.
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

    # Preferred: derive the *prefixed* run root from the actual CSV location the user loaded.
    inferred_root = _infer_prefixed_run_root(csv1_path)
    # sanitize the provided prefix (if any)
    safe_prefix = re.sub(r"[^\w\-.]+", "_", (save_prefix or "").strip()) if save_prefix else ""

    if inferred_root:
        # Use the prefixed root that the CSV lives under (e.g., .../2025-10-24T19-40-30Z_hat-colearning)
        prefixed_root = inferred_root

        # If no explicit save_prefix was passed, try to derive it from the root folder name.
        # Example folder name: 2025-10-24T19-40-30Z_hat-colearning  -> prefix = hat-colearning
        if not safe_prefix:
            m = re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z_(.+)$', os.path.basename(inferred_root))
            if m and m.group(1).strip():
                safe_prefix = m.group(1).strip()
    else:
        # Fallback to the un-prefixed run root from run_dirs(), and append _<prefix> for clarity if provided.
        run_root = os.path.dirname(paths["csv"])  # typically .../lit_runs/<timestamp>
        prefixed_root = f"{run_root}_{safe_prefix}" if safe_prefix else run_root

    # Stage-specific roots under the (prefixed) run root — clear names instead of generic csv/raw/logs
    stage_csv_root  = os.path.join(prefixed_root, "candidate collection output")
    stage_logs_root = os.path.join(prefixed_root, "candidate collection logs")
    stage_raw_root  = os.path.join(prefixed_root, "candidate collection raw")

    # If a prefix exists, add it as a subfolder under each stage root (for visual grouping).
    if safe_prefix:
        stage_csv_root  = os.path.join(stage_csv_root,  safe_prefix)
        stage_logs_root = os.path.join(stage_logs_root, safe_prefix)
        stage_raw_root  = os.path.join(stage_raw_root,  safe_prefix)

    # Replace the generic paths with stage roots
    paths["csv"]  = stage_csv_root
    paths["logs"] = stage_logs_root
    paths["raw"]  = stage_raw_root

    # Ensure stage directories exist
    for key in ("csv", "raw", "logs"):
        try:
            os.makedirs(paths[key], exist_ok=True)
        except Exception as e:
            print(f"[io] could not create stage dir for {key}: {e}")

    # Create a fresh, unique subfolder per invocation to avoid overwrites.
    attempt_stamp = datetime.datetime.utcnow().strftime("attempt_%Y-%m-%d_%H-%M-%S")
    for key in ("csv", "raw", "logs"):
        base_dir = paths[key]
        unique_dir = os.path.join(base_dir, attempt_stamp)
        try:
            os.makedirs(unique_dir, exist_ok=True)
            paths[key] = unique_dir
        except Exception as e:
            print(f"[io] could not create unique attempt dir for {key}: {e}")

    _dbg(
        "Writing outputs to unique attempt folder: "
        f"csv={paths['csv']} raw={paths['raw']} logs={paths['logs']}"
    )



    # Helper: apply prefix to filenames as well as folders
    def _pf(name: str) -> str:
        return f"{safe_prefix}_{name}" if safe_prefix else name


    # Summarize a few relevant env knobs we rely on (debug-only)
    try:
        _dbg("Env summary: "
             f"LIT_RATE_LIMIT_SEC={os.getenv('LIT_RATE_LIMIT_SEC', '')} "
             f"LIT_MAX_PAGES={os.getenv('LIT_MAX_PAGES', '')} "
             f"LIT_OPENALEX_MAX_PAGES={os.getenv('LIT_OPENALEX_MAX_PAGES', '')} "
             f"LIT_PER_SOURCE_MAX={os.getenv('LIT_PER_SOURCE_MAX', '')} "
             f"LIT_OPENALEX_PER_SOURCE_MAX={os.getenv('LIT_OPENALEX_PER_SOURCE_MAX', '')} "
             f"LIT_CROSSREF_PER_SOURCE_MAX={os.getenv('LIT_CROSSREF_PER_SOURCE_MAX', '')} "
             f"LIT_ARXIV_PER_SOURCE_MAX={os.getenv('LIT_ARXIV_PER_SOURCE_MAX', '')} "
             f"LIT_PUBMED_PER_SOURCE_MAX={os.getenv('LIT_PUBMED_PER_SOURCE_MAX', '')} "
             f"LIT_SEMANTICSCHOLAR_PER_SOURCE_MAX={os.getenv('LIT_SEMANTICSCHOLAR_PER_SOURCE_MAX', '')} "
             f"LIT_PUBMED_RELAXED={os.getenv('LIT_PUBMED_RELAXED', '')} "
             f"LIT_PUBMED_ANY_CHUNK={os.getenv('LIT_PUBMED_ANY_CHUNK', '')}"
             )
    except Exception:
        pass

    queries_log_path = os.path.join(paths["logs"], _pf("queries_emitted.log"))
    results_log_path = os.path.join(paths["logs"], _pf("results_summary.log"))

    stop_flag_path = os.path.join(paths["logs"], "STOP")
    # expose to GUI so a Stop button can touch the file
    try: os.environ["LIT_STOP_FLAG_PATH"] = stop_flag_path
    except Exception: pass

    # True RAW (legacy name kept, but now truly "all rows"): every collected row, no dedupe/merge
    out_all = os.path.join(paths["csv"], _pf("search_results_raw.csv"))
    _ensure_csv2_header(out_all)

    # Final, de-duplicated + merged file (placeholder during collect; de-dup step writes real one)
    out_final = os.path.join(paths["csv"], _pf("search_results_final.csv"))
    # (header ensured later right before writing)

    # Streaming (append-as-we-go) file for progress monitoring (non-deduped, handy for tails)
    out_partial = os.path.join(paths["csv"], _pf("search_results_partial.csv"))
    _ensure_csv2_header(out_partial)

    # # Streaming enrichment (as abstracts get filled)
    # out_enriched = os.path.join(paths["csv"], _pf("search_results_enriched_partial.csv"))
    # _ensure_csv2_header(out_enriched)

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
            # Write a RAW (non-deduped) snapshot for progress monitoring
            try:
                cp_path = os.path.join(paths["csv"], _pf("search_results_raw.checkpoint.csv"))
                _ensure_csv2_header(cp_path)
                # append-as-we-go snapshot of current collected rows (no dedupe)
                if collected:
                    _write_csv2(cp_path, list(collected))
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


    # def _enrich_missing_abstracts(rows: List[Dict[str, str]]) -> None:
    #     """
    #     Fills missing/short abstracts in-place using DOI/PMID lookups and a light scrape fallback.
    #     Streams progress to 'search_results_enriched_partial.csv'.
    #     """
    #     for r in rows:
    #         # Clean title/venue that may have weird chars
    #         r["title"] = _clean_text(r.get("title", ""))
    #         r["venue"] = _clean_text(r.get("venue", ""))
    #         r["authors|;|"] = _clean_text(r.get("authors|;|", ""))
    #
    #         # If an abstract exists and looks real, keep it
    #         existing = _clean_text(r.get("abstract", ""))
    #         if existing and len(existing) >= 120:
    #             r["abstract"] = existing
    #             continue
    #
    #         doi = (r.get("doi") or "").strip().lower()
    #         url = r.get("url") or ""
    #         new_abs = None
    #
    #         # Try DOI-based lookups first
    #         if doi:
    #             new_abs = _fetch_abstract_by_doi(doi)
    #
    #         # PubMed by PMID if present in URL (or if Crossref mapped it in DOI lookup path)
    #         if not new_abs:
    #             pmid = _extract_pmid_from_url(url)
    #             if pmid:
    #                 new_abs = _fetch_pubmed_abstract(pmid)
    #
    #         # Fallback: quick page scrape
    #         if (not new_abs) and url:
    #             new_abs = _scrape_page_for_abstract(url)
    #
    #         if new_abs:
    #             r["abstract"] = new_abs
    #             # Stream this improved row so you can see enrichment progress
    #             _write_csv2(out_enriched, [r])


    # ---- Approval gate (network-only; NO LLM TOKENS) -------------------------
    def _collect():
        nonlocal collected, since_last_cp

        if _should_stop(stop_flag_path):
            _dbg("Stop requested before collection started; exiting early.")
            return "stopped"

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
                    new_rows: List[Dict[str, str]] = []
                    cap = _effective_per_source(per_source, engine)
                    for q in _plan_queries_staged(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break
                        if len(new_rows) >= cap: break

                        _log_query(engine, q)
                        base_kwargs = dict(run_id=run_id, q=q, term_origin=term_origin,
                                           per_page=_engine_page_size(engine, cap - len(new_rows)),
                                           max_pages=_max_pages("OpenAlex"))
                        rows_pagewise = _page_loop(
                            fetch_fn=SRC.search_openalex,
                            engine=engine,
                            run_id=run_id,
                            query=q,
                            term_origin=term_origin,
                            base_kwargs=dict(
                                per_page=_engine_page_size(engine, cap - len(new_rows)),
                                max_pages=_max_pages("OpenAlex")
                            ),
                            size_param="per_page",
                            max_pages=_max_pages("OpenAlex"),
                            per_source_cap=cap - len(new_rows),
                            results_log_path=results_log_path,
                            queries_log_path=queries_log_path,
                            engine_attempts=engine_attempts,
                            engine_success=engine_success
                        )

                        new_rows += rows_pagewise

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        _write_csv2(out_all, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return "stopped"
                except Exception as e:
                    engine_errors["OpenAlex"] += 1
                    print(f"[collect][OpenAlex] error: {e}")

            if "Crossref" in engines:
                try:
                    engine = "Crossref"
                    new_rows: List[Dict[str, str]] = []
                    cap = _effective_per_source(per_source, engine)
                    for q in _plan_queries_staged(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break
                        if len(new_rows) >= cap: break

                        _log_query(engine, q)
                        base_kwargs = dict(run_id=run_id, q=q, term_origin=term_origin,
                                           rows=_engine_page_size(engine, cap - len(new_rows)))
                        rows_pagewise = _page_loop(
                            fetch_fn=SRC.search_crossref,
                            engine=engine,
                            run_id=run_id,
                            query=q,
                            term_origin=term_origin,
                            base_kwargs=dict(
                                rows=_engine_page_size(engine, cap - len(new_rows))
                            ),
                            size_param="rows",
                            max_pages=_max_pages("Crossref"),
                            per_source_cap=cap - len(new_rows),
                            results_log_path=results_log_path,
                            queries_log_path=queries_log_path,
                            engine_attempts=engine_attempts,
                            engine_success=engine_success
                        )

                        new_rows += rows_pagewise

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        _write_csv2(out_all, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return "stopped"
                except Exception as e:
                    engine_errors["Crossref"] += 1
                    print(f"[collect][Crossref] error: {e}")

            if "arXiv" in engines:
                try:
                    engine = "arXiv"
                    new_rows: List[Dict[str, str]] = []
                    cap = _effective_per_source(per_source, engine)
                    # IMPORTANT: do NOT simplify; use planner output
                    for q in _plan_queries_staged(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break
                        if len(new_rows) >= cap: break

                        _log_query(engine, q)
                        base_kwargs = dict(run_id=run_id, q=q, term_origin=term_origin,
                                           max_results=_engine_page_size(engine, cap - len(new_rows)))
                        rows_pagewise = _page_loop(
                            fetch_fn=SRC.search_arxiv,
                            engine=engine,
                            run_id=run_id,
                            query=q,
                            term_origin=term_origin,
                            base_kwargs=dict(
                                max_results=_engine_page_size(engine, cap - len(new_rows))
                            ),
                            size_param="max_results",
                            max_pages=_max_pages("arXiv"),
                            per_source_cap=cap - len(new_rows),
                            results_log_path=results_log_path,
                            queries_log_path=queries_log_path,
                            engine_attempts=engine_attempts,
                            engine_success=engine_success
                        )

                        new_rows += rows_pagewise

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        _write_csv2(out_all, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return "stopped"
                except Exception as e:
                    engine_errors["arXiv"] += 1
                    print(f"[collect][arXiv] error: {e}")

            if "PubMed" in engines:
                try:
                    engine = "PubMed"
                    new_rows: List[Dict[str, str]] = []
                    cap = _effective_per_source(per_source, engine)
                    # IMPORTANT: keep planner output (now strict+relaxed) and walk pages
                    for q in _plan_queries_staged(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break
                        if len(new_rows) >= cap: break

                        _log_query(engine, q)
                        base_kwargs = dict(run_id=run_id, q=q, term_origin=term_origin,
                                           retmax=_engine_page_size(engine, cap - len(new_rows)))
                        rows_pagewise = _page_loop(
                            fetch_fn=SRC.search_pubmed,
                            engine=engine,
                            run_id=run_id,
                            query=q,
                            term_origin=term_origin,
                            base_kwargs=dict(
                                retmax=_engine_page_size(engine, cap - len(new_rows))
                            ),
                            size_param="retmax",
                            max_pages=_max_pages("PubMed"),
                            per_source_cap=cap - len(new_rows),
                            results_log_path=results_log_path,
                            queries_log_path=queries_log_path,
                            engine_attempts=engine_attempts,
                            engine_success=engine_success
                        )

                        new_rows += rows_pagewise

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        _write_csv2(out_all, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return "stopped"
                except Exception as e:
                    engine_errors["PubMed"] += 1
                    print(f"[collect][PubMed] error: {e}")

            if "SemanticScholar" in engines:
                try:
                    engine = "SemanticScholar"
                    new_rows: List[Dict[str, str]] = []
                    cap = _effective_per_source(per_source, engine)
                    for q in _plan_queries_staged(engine, spec, base_q_clean):
                        if _should_stop(stop_flag_path): break
                        if len(new_rows) >= cap: break

                        _log_query(engine, q)
                        base_kwargs = dict(run_id=run_id, q=q, term_origin=term_origin,
                                           limit=_engine_page_size(engine, cap - len(new_rows)))
                        rows_pagewise = _page_loop(
                            fetch_fn=SRC.search_semantic_scholar,
                            engine=engine,
                            run_id=run_id,
                            query=q,
                            term_origin=term_origin,
                            base_kwargs=dict(
                                limit=_engine_page_size(engine, cap - len(new_rows))
                            ),
                            size_param="limit",
                            max_pages=_max_pages("SemanticScholar"),
                            per_source_cap=cap - len(new_rows),
                            results_log_path=results_log_path,
                            queries_log_path=queries_log_path,
                            engine_attempts=engine_attempts,
                            engine_success=engine_success
                        )

                        new_rows += rows_pagewise

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts[engine] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        _write_csv2(out_all, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] {engine}: +{len(new_rows)} (planned queries).")
                    if _should_stop(stop_flag_path):
                        _dbg(f"Stop requested after {engine} block; exiting early.")
                        return "stopped"
                except Exception as e:
                    engine_errors["SemanticScholar"] += 1
                    print(f"[collect][SemanticScholar] error: {e}")

        return "completed"

    # ----------------------- Stop-safe finalize (always) -----------------------
    def _finalize_and_write() -> Tuple[bool, str]:
        """
        End-of-run finalize for the *collection* task:
          - DO NOT de-duplicate here.
          - Ensure RAW/partial/enriched CSVs exist with headers.
          - Create an empty-header 'search_results_final.csv' placeholder only (no data).
          - Write INTERRUPTED markers if STOP was requested.
          - Log a clear RAW-only summary with guidance to run de-dup later.
        """
        interrupted = _should_stop(os.getenv("LIT_STOP_FLAG_PATH", ""))

        # Force a last checkpoint (RAW snapshot)
        try:
            _maybe_checkpoint(True)
        except Exception:
            pass

        # Ensure output files exist (headers only if empty)
        try:
            if paths.get('csv'):
                os.makedirs(paths['csv'], exist_ok=True)
                raw_path = os.path.join(paths["csv"], _pf('search_results_raw.csv'))
                partial_path = os.path.join(paths["csv"], _pf('search_results_partial.csv'))
                enriched_path = os.path.join(paths["csv"], _pf('search_results_enriched_partial.csv'))
                final_placeholder = os.path.join(paths["csv"], _pf('search_results_final.csv'))

                _ensure_csv2_header(raw_path)
                _ensure_csv2_header(partial_path)
                _ensure_csv2_header(enriched_path)
                # Placeholder for downstream compatibility; *not* populated here
                _ensure_csv2_header(final_placeholder)
        except Exception as e:
            print(f"[guard] could not ensure output files: {e}")

        # INTERRUPTED marker (lets the GUI show a yellow “completed (stopped)” state)
        try:
            if interrupted and paths.get("logs"):
                with open(os.path.join(paths["logs"], "INTERRUPTED"), "w", encoding="utf-8") as f:
                    f.write("STOP was requested; finalize() ran. RAW collection complete; no de-dup performed.\n")
        except Exception:
            pass

        # Summaries for console/log
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

        # Compose final message (RAW-only)
        try:
            raw_rows = len(collected)
        except Exception:
            raw_rows = -1

        out_all = os.path.join(paths["csv"], _pf("search_results_raw.csv"))
        out_final_placeholder = os.path.join(paths["csv"], _pf("search_results_final.csv"))

        results_log_path = os.path.join(paths["logs"], _pf("results_summary.log"))

        msg = (
            f"{'⛔ ' if interrupted else ''}RAW (all rows) written/appended: {out_all} | rows≈{raw_rows}\n"
            f"   Next: Run De-duplicate (Cleanup tab) to create FINAL, then run Enrich Abstracts on that FINAL.\n"
            f"   Placeholder FINAL: {out_final_placeholder} (empty until de-dup writes it)."
        )

        print(msg)
        try:
            _write_log_line(
                results_log_path,
                f"[FINAL{' [INTERRUPTED]' if interrupted else ''}] raw≈{raw_rows} | out_all={out_all} | final_placeholder={out_final_placeholder} (no de-dup)"
            )
        except Exception:
            pass

        return True, msg

    # ----------------------- Orchestration: try/finally ------------------------
    ok_collect = False
    try:
        # Make the approval description explicit: no LLM spend; show scale
        req_count = len(qs) * len(engines)
        desc = (f"Literature Collection (CSV-2) — NO LLM TOKENS | "
                f"engines={','.join(engines)} | queries={len(qs)} | requests≈{req_count}")

        # Single approval; temporarily switch approvals to 'auto' so
        # downstream network-only calls don’t enqueue new prompts.
        ok = approvals.request_approval(
            description=desc,
            call_fn=lambda ov=None: _with_temp_approval_mode("auto", _collect),
            timeout=None
        )
        if not ok:
            return False, "Approval denied or failed."

        ok_collect = True

        # (enrichment moved to standalone task; collector stops fast)
        print("[collect] Skipping enrichment; run it later from the Cleanup tab.")


    finally:
        # No matter what (STOP, error, normal finish), produce FINAL.
        _ok, _msg = _finalize_and_write()

    return (ok_collect and _ok), _msg

def run_dedupe_only(input_csv_path: str, output_dir: Optional[str] = None, save_prefix: Optional[str] = None) -> Tuple[bool, str]:
    """
    DEPRECATED: moved to tasks.lit_dedupe.run.
    Kept for compatibility. Supports the same behavior but delegates.
    """
    try:
        from tasks.lit_dedupe import run as _dedupe_run
    except Exception as e:
        return False, f"Could not import tasks.lit_dedupe: {e}"
    return _dedupe_run(input_csv_path=input_csv_path, output_dir=output_dir, save_prefix=save_prefix)


