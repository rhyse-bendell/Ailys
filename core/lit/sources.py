# core/lit/sources.py
import os, time, json, math, xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Iterable, Tuple
import requests
from core.approval_queue import request_approval

# ---- throttling -------------------------------------------------------------
DEFAULT_SLEEP_SEC = float(os.getenv("LIT_RATE_LIMIT_SEC", "1.25"))  # ~1 req / 1.25s
def _sleep():
    time.sleep(DEFAULT_SLEEP_SEC)

# ---- approval-wrapped GET ---------------------------------------------------
def _get(url: str, params: Optional[Dict]=None, headers: Optional[Dict]=None, desc: Optional[str]=None):
    def _do():
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp
    approved = request_approval(description=desc or f"HTTP GET {url}", call_fn=_do)
    return approved

# ---- helpers ----------------------------------------------------------------
def _norm_authors(auths) -> List[str]:
    out = []
    for a in auths or []:
        if isinstance(a, str):
            out.append(a)
        else:
            name = a.get("name") or a.get("display_name") or a.get("author", {}).get("display_name")
            if name: out.append(name)
    return out

def _row(run_id: str, engine: str, query: str, term_origin: str, title: str, authors: List[str],
         year: Optional[int], venue: str, doi: str, url: str, abstract: str, source_score: Optional[float]) -> Dict[str,str]:
    return {
        "run_id": run_id,
        "engine": engine,
        "query": query,
        "term_origin": term_origin,
        "work_id": doi or (title.strip().lower() + f"::{year or ''}")[:200],
        "title": title or "",
        "authors|;|": " |;| ".join(authors or []),
        "year": str(year or ""),
        "venue": venue or "",
        "doi": doi or "",
        "url": url or "",
        "abstract": abstract or "",
        "source_score": "" if source_score is None else f"{source_score:.3f}",
    }


# ---- OpenAlex (robust, cursor-based) ---------------------------------------
import re
from json import JSONDecodeError

_BOOL_RE  = re.compile(r'\b(AND|OR|NOT)\b', flags=re.I)
_PAREN_RE = re.compile(r'[()]')
_QUOTE_RE = re.compile(r'["“”]+')

def _sanitize_bow(q: str) -> str:
    """Make a search-friendly bag-of-words for OpenAlex: drop booleans/parens, keep spacing."""
    if not q:
        return q
    s = q.strip()
    s = _BOOL_RE.sub(" ", s)
    s = _PAREN_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _strip_quotes(s: str) -> str:
    return _QUOTE_RE.sub("", s or "").strip()

def _reconstruct_abstract_from_inverted(inv: dict | None) -> str:
    """Rebuild OpenAlex abstract from abstract_inverted_index safely."""
    if not inv or not isinstance(inv, dict):
        return ""
    try:
        positions = []
        for token, idxs in inv.items():
            token = str(token)
            for i in idxs:
                positions.append((int(i), token))
        positions.sort(key=lambda x: x[0])
        return " ".join(tok for _, tok in positions)
    except Exception:
        return ""

def _openalex_headers() -> Dict[str, str]:
    # Be polite; include mailto in UA if provided.
    mailto = (os.getenv("OPENALEX_EMAIL", "") or os.getenv("CROSSREF_MAILTO","")).strip()
    ua = f"Ailys/1.0 (mailto:{mailto})" if mailto else "Ailys/1.0"
    return {"User-Agent": ua}

def _build_openalex_param_strategies(query: str) -> List[Dict[str, str]]:
    """
    Try a few tolerant strategies so brittle queries still work:
      1) search = sanitized original
      2) search = no-quotes version
      3) title.search = no-quotes
      4) abstract.search = no-quotes
    """
    s1 = _sanitize_bow(query)
    s2 = _strip_quotes(s1)
    tries: List[Dict[str, str]] = []
    if s1:
        tries.append({"search": s1})
    if s2 and s2 != s1:
        tries.append({"search": s2})
    if s2:
        tries.append({"title.search": s2})
        tries.append({"abstract.search": s2})
    return tries or [{"search": (s2 or s1 or query)}]

def search_openalex(
    run_id: str,
    query: str,
    term_origin: str,
    per_page: int = 20,
    max_pages: int = 1,
    mailto: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    OpenAlex works search with cursor pagination & resilient parsing.

    - per_page: total target rows to return for this query (we may fetch fewer).
    - max_pages: safety cap on cursor pages (each page can return up to 200).
    """
    base_url = "https://api.openalex.org/works"
    out: List[Dict[str, str]] = []

    # OpenAlex supports up to ~200 items per cursor page
    target_total = max(1, int(per_page))
    page_chunk   = min(200, max(25, target_total))

    # Build polite headers; keep using your approval-wrapped GET.
    headers = _openalex_headers()
    tries = _build_openalex_param_strategies(query)

    for param_try in tries:
        cursor = "*"
        pages_used = 0

        while pages_used < max_pages and len(out) < target_total:
            params = {
                "per_page": page_chunk,
                "cursor": cursor,
                "mailto": mailto or os.getenv("OPENALEX_EMAIL", "")
            }
            params.update(param_try)

            # Approval-wrapped call (same pattern as the rest of your sources)
            resp = _get(
                base_url,
                params=params,
                headers=headers,
                desc=f"OpenAlex search (page {pages_used+1}): {query}"
            )
            if not resp:
                # network/approval error → try next strategy
                break

            # Robust JSON decode guard
            try:
                data = resp.json()
            except JSONDecodeError:
                # Non-JSON (rare) → try next strategy
                break
            except Exception:
                break

            if not isinstance(data, dict):
                # Unexpected body → try next strategy
                break

            results = data.get("results") or []
            if not isinstance(results, list):
                # Unexpected shape → try next strategy
                break

            for it in results:
                try:
                    # Title
                    title = (it.get("display_name") or it.get("title") or "").strip()

                    # Authors
                    authors = []
                    for a in (it.get("authorships") or []):
                        nm = (a.get("author") or {}).get("display_name") or ""
                        if nm:
                            authors.append(nm)

                    # Year
                    year = it.get("publication_year") or it.get("from_year")

                    # Venue
                    venue = ""
                    primary = it.get("primary_location") or {}
                    if isinstance(primary, dict):
                        src = primary.get("source") or {}
                        if isinstance(src, dict):
                            venue = src.get("display_name") or venue
                    if not venue:
                        hv = it.get("host_venue") or {}
                        if isinstance(hv, dict):
                            venue = hv.get("display_name") or venue

                    # DOI
                    doi = ""
                    ids = it.get("ids") or {}
                    if isinstance(ids, dict):
                        doi = (ids.get("doi") or "").replace("https://doi.org/", "").strip().lower()
                    if not doi:
                        raw_doi = it.get("doi")
                        if isinstance(raw_doi, str):
                            doi = raw_doi.replace("https://doi.org/", "").strip().lower()

                    # URL (landing page preferred; fallbacks allowed)
                    url1 = ""
                    if isinstance(primary, dict):
                        url1 = primary.get("landing_page_url") or url1
                        if not url1 and isinstance(primary.get("source"), dict):
                            url1 = primary["source"].get("homepage_url") or url1
                    if not url1:
                        boa = it.get("best_oa_location")
                        if isinstance(boa, dict):
                            url1 = boa.get("url") or url1
                        elif isinstance(boa, str):
                            url1 = boa or url1
                    if not url1:
                        url1 = it.get("openaccess_url") or it.get("id") or ""

                    # Abstract
                    abstract = _reconstruct_abstract_from_inverted(it.get("abstract_inverted_index")) or (it.get("abstract") or "")

                    # Source score (cited_by_count is useful)
                    score = it.get("cited_by_count")

                    out.append(_row(run_id, "OpenAlex", query, term_origin, title, authors, year, venue, doi, url1, abstract, score))
                except Exception:
                    # Skip malformed record; continue
                    continue

            # Cursor advance
            meta = data.get("meta") or {}
            next_cursor = meta.get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor
            pages_used += 1

            _sleep()  # respect your global throttle

        # If we captured anything for this strategy, stop trying alternates
        if out:
            break

    # Trim to the requested total
    return out[:target_total]


# ---- Crossref ---------------------------------------------------------------
def search_crossref(run_id: str, query: str, term_origin: str, rows:int=20, mailto: Optional[str]=None) -> List[Dict[str,str]]:
    params = {"query": query, "rows": rows, "mailto": mailto or os.getenv("CROSSREF_MAILTO","")}
    url = "https://api.crossref.org/works"
    resp = _get(url, params=params, desc=f"Crossref search: {query}")
    if not resp:
        return []
    data = resp.json().get("message",{})
    out = []
    for it in data.get("items", []):
        title = " ".join(it.get("title",[]) or [])
        authors = _norm_authors([{"name": f"{a.get('given','')} {a.get('family','')}".strip()} for a in it.get("author",[])])
        year = None
        if it.get("issued",{}).get("date-parts"):
            year = it["issued"]["date-parts"][0][0]
        venue = it.get("container-title",[None])[0] or ""
        doi = (it.get("DOI") or "").strip()
        url1 = it.get("URL","")
        abstract = it.get("abstract","")
        score = it.get("score")
        out.append(_row(run_id,"Crossref",query,term_origin,title,authors,year,venue,doi,url1,abstract,score))
    _sleep()
    return out

# ---- arXiv ------------------------------------------------------------------
def search_arxiv(run_id: str, query: str, term_origin: str, max_results:int=20) -> List[Dict[str,str]]:
    # ArXiv uses a simple query language; we’ll pass boolean string as 'all:' wrapped
    base = "http://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    resp = _get(base, params=params, desc=f"arXiv search: {query}")
    if not resp:
        return []
    root = ET.fromstring(resp.text)
    ns = {"a":"http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns):
        title = (entry.find("a:title", ns).text or "").strip()
        authors = [e.find("a:name", ns).text for e in entry.findall("a:author", ns)]
        year = None
        if entry.find("a:published", ns) is not None:
            year = int(entry.find("a:published", ns).text[:4])
        venue = "arXiv"
        doi = ""
        for l in entry.findall("a:link", ns):
            if l.attrib.get("title") == "doi": doi = l.attrib.get("href","").replace("https://doi.org/","")
        url1 = ""
        for l in entry.findall("a:link", ns):
            if l.attrib.get("rel") == "alternate": url1 = l.attrib.get("href","")
        abstract = (entry.find("a:summary", ns).text or "").strip()
        out.append(_row(run_id,"arXiv",query,term_origin,title,authors,year,venue,doi,url1,abstract,None))
    _sleep()
    return out

# ---- PubMed (ESearch + EFetch) ---------------------------------------------
def search_pubmed(run_id: str, query: str, term_origin: str, retmax:int=20) -> List[Dict[str,str]]:
    # ESearch
    esearch = _get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db":"pubmed","term":query,"retmode":"json","retmax":str(retmax)},
        desc=f"PubMed ESearch: {query}"
    )
    if not esearch:
        return []
    ids = esearch.json().get("esearchresult",{}).get("idlist",[])
    if not ids:
        _sleep()
        return []
    # EFetch (abstracts)
    efetch = _get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db":"pubmed","id":",".join(ids),"retmode":"xml"},
        desc=f"PubMed EFetch {len(ids)} ids"
    )
    out = []
    if efetch:
        root = ET.fromstring(efetch.text)
        for art in root.findall(".//PubmedArticle"):
            artset = art.find(".//Article")
            if artset is None: continue
            title = "".join(artset.findtext("ArticleTitle",""))
            abstract = " ".join([t.text or "" for t in artset.findall(".//AbstractText")])
            year = None
            dp = artset.find("Journal/JournalIssue/PubDate/Year")
            if dp is not None:
                try: year = int(dp.text)
                except: pass
            venue = (artset.findtext("Journal/Title") or "")
            # Authors
            authors = []
            for a in artset.findall("AuthorList/Author"):
                last = (a.findtext("LastName") or "").strip()
                fore = (a.findtext("ForeName") or "").strip()
                nm = (fore + " " + last).strip()
                if nm: authors.append(nm)
            doi = ""
            for i in art.findall(".//ArticleIdList/ArticleId"):
                if i.attrib.get("IdType") == "doi":
                    doi = (i.text or "").strip()
            url1 = f"https://pubmed.ncbi.nlm.nih.gov/{art.findtext('.//PMID') or ''}/"
            out.append(_row(run_id,"PubMed",query,term_origin,title,authors,year,venue,doi,url1,abstract,None))
    _sleep()
    return out

# ---- Semantic Scholar -------------------------------------------------------
def search_semantic_scholar(run_id: str, query: str, term_origin: str, limit:int=20) -> List[Dict[str,str]]:
    key = os.getenv("SEMANTIC_SCHOLAR_KEY","")
    headers = {"x-api-key": key} if key else {}
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,externalIds,url"
    }
    resp = _get(url, params=params, headers=headers, desc=f"Semantic Scholar: {query}")
    if not resp:
        return []
    data = resp.json() or {}
    out = []
    for it in data.get("data", []):
        title = it.get("title","")
        authors = _norm_authors(it.get("authors",[]))
        year = it.get("year")
        venue = it.get("venue","")
        doi = ""
        ext = it.get("externalIds") or {}
        if ext.get("DOI"): doi = ext["DOI"]
        url1 = it.get("url","")
        abstract = it.get("abstract","")
        out.append(_row(run_id,"SemanticScholar",query,term_origin,title,authors,year,venue,doi,url1,abstract,None))
    _sleep()
    return out
