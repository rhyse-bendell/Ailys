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

# ---- OpenAlex ---------------------------------------------------------------
def search_openalex(run_id: str, query: str, term_origin: str, per_page:int=20, max_pages:int=1, mailto: Optional[str]=None) -> List[Dict[str,str]]:
    rows = []
    for page in range(1, max_pages+1):
        params = {
            "search": query,
            "page": page,
            "per_page": per_page,
            "mailto": mailto or os.getenv("OPENALEX_EMAIL","")
        }
        url = "https://api.openalex.org/works"
        resp = _get(url, params=params, desc=f"OpenAlex search (page {page}): {query}")
        if not resp:
            break
        data = resp.json()
        for it in data.get("results", []):
            title = it.get("title","")
            authors = _norm_authors([a.get("author",{}) for a in it.get("authorships",[])])
            year = it.get("publication_year")
            venue = (it.get("host_venue") or {}).get("display_name","")
            doi = (it.get("doi") or "").replace("https://doi.org/","").strip()
            url1 = (it.get("primary_location") or {}).get("source",{}).get("host_venue_url") or it.get("open_access",{}).get("oa_url") or it.get("primary_location",{}).get("landing_page_url","")
            abstract = ""
            if it.get("abstract_inverted_index"):
                # reconstitute the abstract
                idx = it["abstract_inverted_index"]
                # build token list by positions
                maxpos = max(p for positions in idx.values() for p in positions)
                tokens = [""]*(maxpos+1)
                for word, poss in idx.items():
                    for p in poss: tokens[p]=word
                abstract = " ".join(t for t in tokens if t)
            score = None
            rows.append(_row(run_id,"OpenAlex",query,term_origin,title,authors,year,venue,doi,url1,abstract,score))
        _sleep()
    return rows

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
