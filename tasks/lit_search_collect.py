# tasks/lit_search_collect.py
import os, csv, datetime, re, time, html, unicodedata
from collections import defaultdict
from typing import Optional, Dict, List, Tuple
from core.lit.utils import to_list, run_dirs
import core.approval_queue as approvals

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
        meta = _read_keywords_csv(csv1_path)
    except Exception as e:
        # fallback run_id so we still create output folders and write files
        fallback_run_id = datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        print(f"[warn] Failed to read CSV-1: {e} — continuing with fallback run_id={fallback_run_id}")
        meta = {"run_id": fallback_run_id, "boolean_queries": []}

    run_id = (meta.get("run_id") or "").strip()
    if not run_id:
        run_id = datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        print(f"[warn] Empty run_id in CSV-1 — using fallback run_id={run_id}")

    qs = meta.get("boolean_queries") or []

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
        for q in qs:
            term_origin = "seed/expanded-mix"
            if "OpenAlex" in engines:
                try:
                    q_simple = _simplify_boolean(q)
                    new_rows: List[Dict[str,str]] = []

                    # Simple first
                    r1 = SRC.search_openalex(
                        run_id, q_simple, term_origin,
                        per_page=min(per_source, 25),
                        max_pages=_max_pages("OpenAlex")
                    )
                    r1 = _force_engine(r1, "OpenAlex")
                    new_rows += r1 or []

                    # Then try the original boolean if we want more
                    if len(new_rows) < per_source:
                        r2 = SRC.search_openalex(
                            run_id, q, term_origin,
                            per_page=min(per_source - len(new_rows), 25),
                            max_pages=_max_pages("OpenAlex")
                        )
                        r2 = _force_engine(r2, "OpenAlex")
                        new_rows += r2 or []

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts["OpenAlex"] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] OpenAlex: +{len(new_rows)} (simple→boolean).")

                except Exception as e:
                    engine_errors["OpenAlex"] += 1
                    print(f"[collect][OpenAlex] error: {e}")


            if "Crossref" in engines:
                try:
                    q_simple = _simplify_boolean(q)
                    new_rows: List[Dict[str,str]] = []

                    # Simple first (Crossref can handle boolean too, but simple boosts recall)
                    r1 = SRC.search_crossref(run_id, q_simple, term_origin, rows=min(per_source, 50))
                    r1 = _force_engine(r1, "Crossref")
                    new_rows += r1 or []

                    if len(new_rows) < per_source:
                        r2 = SRC.search_crossref(run_id, q, term_origin, rows=min(per_source - len(new_rows), 50))
                        r2 = _force_engine(r2, "Crossref")
                        new_rows += r2 or []

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts["Crossref"] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] Crossref: +{len(new_rows)} (simple→boolean).")

                except Exception as e:
                    engine_errors["Crossref"] += 1
                    print(f"[collect][Crossref] error: {e}")


            if "arXiv" in engines:
                try:
                    q_simple = _simplify_boolean(q)  # arXiv dislikes complex booleans
                    new_rows: List[Dict[str,str]] = []

                    r1 = SRC.search_arxiv(run_id, q_simple, term_origin, max_results=min(per_source, 50))
                    r1 = _force_engine(r1, "arXiv")
                    new_rows += r1 or []

                    if len(new_rows) < per_source:
                        # Try original text in case some phrases happen to work
                        r2 = SRC.search_arxiv(run_id, q, term_origin, max_results=min(per_source - len(new_rows), 50))
                        r2 = _force_engine(r2, "arXiv")
                        new_rows += r2 or []

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts["arXiv"] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] arXiv: +{len(new_rows)} (simple→boolean).")

                except Exception as e:
                    engine_errors["arXiv"] += 1
                    print(f"[collect][arXiv] error: {e}")


            if "PubMed" in engines:
                try:
                    q_simple = _simplify_boolean(q)  # PubMed ESearch: bag-of-words performs better
                    new_rows: List[Dict[str,str]] = []

                    r1 = SRC.search_pubmed(run_id, q_simple, term_origin, retmax=min(per_source, 50))
                    r1 = _force_engine(r1, "PubMed")
                    new_rows += r1 or []

                    if len(new_rows) < per_source:
                        r2 = SRC.search_pubmed(run_id, q, term_origin, retmax=min(per_source - len(new_rows), 50))
                        r2 = _force_engine(r2, "PubMed")
                        new_rows += r2 or []

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts["PubMed"] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] PubMed: +{len(new_rows)} (simple→boolean).")

                except Exception as e:
                    engine_errors["PubMed"] += 1
                    print(f"[collect][PubMed] error: {e}")


            if "SemanticScholar" in engines:
                try:
                    q_simple = _simplify_boolean(q)
                    new_rows: List[Dict[str,str]] = []

                    r1 = SRC.search_semantic_scholar(run_id, q_simple, term_origin, limit=min(per_source, 50))
                    r1 = _force_engine(r1, "SemanticScholar")
                    new_rows += r1 or []

                    if len(new_rows) < per_source:
                        r2 = SRC.search_semantic_scholar(run_id, q, term_origin, limit=min(per_source - len(new_rows), 50))
                        r2 = _force_engine(r2, "SemanticScholar")
                        new_rows += r2 or []

                    new_rows = [_normalize_row(r) for r in (new_rows or [])]
                    collected += new_rows
                    engine_counts["SemanticScholar"] += len(new_rows)
                    if new_rows:
                        _write_csv2(out_partial, new_rows)
                        since_last_cp += len(new_rows)
                        _maybe_checkpoint(False)
                    print(f"[collect] SemanticScholar: +{len(new_rows)} (simple→boolean).")

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


