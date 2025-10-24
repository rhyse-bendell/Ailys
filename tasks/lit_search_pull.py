# tasks/lit_search_pull.py
from __future__ import annotations

import os, csv, re, time, datetime, html, unicodedata, hashlib
from typing import Dict, List, Optional, Tuple

import core.approval_queue as approvals

# ---------------- Config & helpers ----------------

DEBUG_PULL = os.getenv("LIT_PULL_DEBUG", "1") != "0"

def _dbg(msg: str):
    if DEBUG_PULL:
        print(f"[pull:dbg] {msg}")

def _throttle_seconds() -> float:
    try:
        return float(os.getenv("LIT_RATE_LIMIT_SEC", "1.5"))
    except Exception:
        return 1.5

def _sleep():
    try:
        time.sleep(_throttle_seconds())
    except Exception:
        pass

def _clean(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _safe_name(s: str, fallback: str) -> str:
    s = (s or "").strip()
    if not s:
        s = (fallback or "untitled").strip()
    s = s[:150]
    s = re.sub(r"[^\w.\-]+", "_", s, flags=re.UNICODE)
    s = s.strip("._")
    return s or "untitled"

def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:10]

def _norm_doi(doi: Optional[str]) -> str:
    if not doi: return ""
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi

def _ensure_dir(p: str):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception as e:
        print(f"[pull:io] mkdir {p} failed: {e}")

def _write_log_line(path: str, line: str):
    try:
        _ensure_dir(os.path.dirname(path) or ".")
        with open(path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass

def _content_looks_pdf(bytes_start: bytes) -> bool:
    # PDF files begin with %PDF-
    try:
        return bytes_start.startswith(b"%PDF-")
    except Exception:
        return False

def _is_pdf_content_type(ct: str | None) -> bool:
    if not ct: return False
    return "application/pdf" in ct.lower()

def _requests():
    try:
        import requests  # local import so missing dep errors surface cleanly
        return requests
    except Exception as e:
        raise RuntimeError(f"Dependency missing: requests — {e}")

def _bs4_optional():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except Exception:
        return None

def _download_pdf(url: str, out_path: str, timeout: float = 25.0) -> Tuple[bool, int, str]:
    """Stream a URL to file and verify it's a PDF by header or magic bytes."""
    req = _requests()
    try:
        r = req.get(url, stream=True, timeout=timeout, headers={"User-Agent":"Ailys/1.0"})
    except Exception as e:
        return False, 0, f"req-error: {type(e).__name__}: {e}"

    try:
        http_code = r.status_code
        if http_code != 200:
            return False, http_code, f"status={http_code}"

        ct = r.headers.get("Content-Type", "")
        # Peek first bytes to confirm PDF
        peek = b""
        try:
            peek = next(r.iter_content(chunk_size=4096))
        except StopIteration:
            peek = b""
        except Exception:
            pass

        if not (_is_pdf_content_type(ct) or _content_looks_pdf(peek)):
            # Not a PDF — do not save binary junk
            return False, http_code, f"not-pdf content-type={ct or '?'}"

        _ensure_dir(os.path.dirname(out_path) or ".")
        with open(out_path, "wb") as f:
            if peek:
                f.write(peek)
            for chunk in r.iter_content(chunk_size=64*1024):
                if chunk:
                    f.write(chunk)
        return True, http_code, "ok"
    finally:
        try:
            r.close()
        except Exception:
            pass
        _sleep()

# ---------------- Sources (no LLM; API-only) ----------------

def _try_unpaywall(doi: str) -> Optional[str]:
    """
    Returns a URL to a PDF if Unpaywall has an OA location.
    Requires UNPAYWALL_EMAIL set.
    """
    email = (os.getenv("UNPAYWALL_EMAIL","") or os.getenv("OPENALEX_EMAIL","")).strip()
    if not email:
        return None
    req = _requests()
    url = f"https://api.unpaywall.org/v2/{doi}"
    try:
        r = req.get(url, params={"email": email}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        # best_oa_location.url_for_pdf, fallback to .url
        loc = (data or {}).get("best_oa_location") or {}
        pdf = loc.get("url_for_pdf") or loc.get("url")
        if pdf:
            return pdf
        # scan other locations
        for loc in (data or {}).get("oa_locations") or []:
            pdf = loc.get("url_for_pdf") or loc.get("url")
            if pdf:
                return pdf
    except Exception:
        return None
    finally:
        _sleep()
    return None

def _try_openalex(doi: str) -> Optional[str]:
    req = _requests()
    # OpenAlex work by DOI
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    try:
        r = req.get(url, timeout=20, headers={"User-Agent":"Ailys/1.0"})
        if r.status_code != 200:
            return None
        data = r.json()
        # Prefer best_oa_location -> pdf_url
        best = data.get("best_oa_location") or {}
        pdf = best.get("pdf_url") or best.get("url")
        if pdf:
            return pdf
        # scan locations array
        for loc in data.get("oa_locations") or []:
            pdf = loc.get("pdf_url") or loc.get("url")
            if pdf:
                return pdf
    except Exception:
        return None
    finally:
        _sleep()
    return None

def _try_crossref_pdf(doi: str) -> Optional[str]:
    req = _requests()
    mailto = (os.getenv("CROSSREF_MAILTO","") or os.getenv("OPENALEX_EMAIL","")).strip()
    headers = {"User-Agent": f"Ailys/1.0 (mailto:{mailto})"} if mailto else {"User-Agent": "Ailys/1.0"}
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = req.get(url, timeout=20, headers=headers)
        if r.status_code != 200:
            return None
        msg = (r.json() or {}).get("message") or {}
        for link in msg.get("link") or []:
            ct = (link.get("content-type") or "").lower()
            if "application/pdf" in ct and link.get("URL"):
                return link["URL"]
    except Exception:
        return None
    finally:
        _sleep()
    return None

def _try_doi_pdf(doi: str) -> Optional[str]:
    """Content negotiation: ask DOI resolver for a PDF by Accept: application/pdf."""
    req = _requests()
    try:
        r = req.get(f"https://doi.org/{doi}", timeout=25,
                    headers={"Accept": "application/pdf", "User-Agent":"Ailys/1.0"},
                    allow_redirects=True)
        if r.status_code == 200 and (_is_pdf_content_type(r.headers.get("Content-Type")) or _content_looks_pdf(r.content[:8])):
            # The resolver actually returned the file; we need a synthetic URL to re-download streaming
            # but many times this content is the PDF already. We can store to a temp file.
            # Instead, return final URL (after redirects) to stream a second call to keep a uniform path
            return r.url
        # If we landed on publisher page but not PDF, some publishers use 302->HTML.
        # Nothing more we can do here without scraping.
        return None
    except Exception:
        return None
    finally:
        _sleep()

def _try_pubmed_pmc(url_or_id: str) -> Optional[str]:
    """
    If we have a PMCID or a PubMedCentral article URL, return direct PDF link.
    Supports:
      - https://www.ncbi.nlm.nih.gov/pmc/articles/PMCxxxxxx/
      - PMCID like 'PMC1234567'
    """
    if not url_or_id:
        return None
    # extract PMCID from URL
    m = re.search(r"/pmc/articles/(PMC\d+)", url_or_id, flags=re.I)
    pmcid = m.group(1) if m else None
    if not pmcid and url_or_id.upper().startswith("PMC"):
        pmcid = url_or_id
    if not pmcid:
        return None
    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf"

def _try_arxiv(url_or_id: str) -> Optional[str]:
    """Return the arXiv PDF URL if we detect an arXiv id or page."""
    if not url_or_id:
        return None
    # arXiv page -> build pdf link
    m = re.search(r"arxiv\.org/(abs|pdf)/([0-9]+\.[0-9]+)(v\d+)?", url_or_id, flags=re.I)
    if m:
        return f"https://arxiv.org/pdf/{m.group(2)}.pdf"
    # raw id:
    if re.fullmatch(r"[0-9]+\.[0-9]+(v\d+)?", url_or_id):
        return f"https://arxiv.org/pdf/{url_or_id}.pdf"
    return None

def _try_semanticscholar(doi: str) -> Optional[str]:
    key = (os.getenv("SEMANTIC_SCHOLAR_KEY","") or "").strip()
    if not key:
        return None
    req = _requests()
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    try:
        r = req.get(url, params={"fields":"title,openAccessPdf,url"}, headers={"x-api-key":key}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json() or {}
        pdf = (data.get("openAccessPdf") or {}).get("url")
        return pdf
    except Exception:
        return None
    finally:
        _sleep()

def _try_direct_pdf_in_url(url: str) -> Optional[str]:
    if not url:
        return None
    if re.search(r"\.pdf($|\?)", url, flags=re.I):
        return url
    # lightweight sniff of HTML for <link type="application/pdf" href="...">
    BS = _bs4_optional()
    if BS is None:
        return None
    try:
        req = _requests()
        r = req.get(url, timeout=20, headers={"User-Agent":"Ailys/1.0"})
        if r.status_code != 200:
            return None
        soup = BS(r.text, "html.parser")
        # common patterns
        # <a ... href="...pdf">, or <link rel="alternate" type="application/pdf" href="...">
        link = soup.find("link", attrs={"type":"application/pdf"}) or soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if link:
            href = link.get("href") if link.name == "link" else link.get("href")
            if href and not href.lower().startswith("http"):
                # resolve relative
                from urllib.parse import urljoin
                href = urljoin(r.url, href)
            if href:
                return href
    except Exception:
        return None
    finally:
        _sleep()
    return None

# ---------------- Core runner ----------------

OUT_CSV_HEADER = [
    "title","doi","url","year","venue",
    "pdf_status","pdf_path","pdf_source","http_status","note"
]

def _candidate_sources(row: Dict[str,str]) -> List[Tuple[str, Optional[str]]]:
    """
    Build an ordered list of (source_name, url_or_id) attempts for a row.
    Prioritizes strong OA signals first.
    """
    title = _clean(row.get("title",""))
    doi = _norm_doi(row.get("doi",""))
    url = (row.get("url","") or "").strip()

    sources: List[Tuple[str, Optional[str]]] = []

    # If arXiv obvious, do it first (almost guaranteed success)
    a = _try_arxiv(url)
    if a:
        sources.append(("arXiv", a))

    # PubMed Central from URL hint
    pmc = _try_pubmed_pmc(url)
    if pmc:
        sources.append(("PubMedCentral", pmc))

    # Unpaywall/OpenAlex (best OA), then Crossref link, then S2
    if doi:
        sources.append(("Unpaywall", doi))
        sources.append(("OpenAlex", doi))
        sources.append(("CrossrefPDF", doi))
        sources.append(("SemanticScholar", doi))
        sources.append(("DOI-PDF", doi))

    # If URL looks like a direct PDF
    if url and re.search(r"\.pdf($|\?)", url, flags=re.I):
        sources.append(("DirectURL", url))

    # As very last resort, sniff the landing page
    if url:
        sources.append(("HTMLSniff", url))

    return sources

def _resolve_to_pdf_url(kind: str, token: str) -> Optional[str]:
    try:
        if kind == "Unpaywall":
            return _try_unpaywall(token)
        if kind == "OpenAlex":
            return _try_openalex(token)
        if kind == "CrossrefPDF":
            return _try_crossref_pdf(token)
        if kind == "SemanticScholar":
            return _try_semanticscholar(token)
        if kind == "DOI-PDF":
            return _try_doi_pdf(token)
        if kind == "PubMedCentral":
            return token  # already a PDF URL
        if kind == "arXiv":
            return token
        if kind == "DirectURL":
            return token
        if kind == "HTMLSniff":
            return _try_direct_pdf_in_url(token)
    except Exception:
        return None
    return None

def _pick_filename(row: Dict[str,str], final_url: str) -> str:
    doi = _norm_doi(row.get("doi",""))
    title = _clean(row.get("title",""))
    base = ""
    if doi:
        base = _safe_name(doi, "")
    if not base and title:
        base = _safe_name(title, "")
    if not base:
        base = _safe_name(_sha1(final_url), "article")
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base

def _read_csv_rows(path: str) -> List[Dict[str,str]]:
    with open(path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        return [dict(r) for r in rdr]

def _write_out_csv(path: str, rows: List[Dict[str,str]]):
    exists = os.path.exists(path)
    _ensure_dir(os.path.dirname(path) or ".")
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_CSV_HEADER, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)

def _with_temp_approval_mode(temp_mode: str, fn):
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

def run(
    input_csv: str,
    out_root: Optional[str] = None,
    max_items: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Mechanical puller: tries to acquire PDFs for rows in a CSV (ranked/edited).
    - input_csv: path to the CSV with at least title and preferably doi/url.
    - out_root: optional root output folder; default under runs/<run_id>/pdfs
    - max_items: optional cap on number of rows to process
    """
    if not os.path.exists(input_csv):
        return False, f"Input CSV not found: {input_csv}"

    rows = _read_csv_rows(input_csv)
    if not rows:
        return False, "No rows to process."

    # Build a run folder
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    run_id = os.path.basename(os.path.dirname(input_csv)) or f"pull_{ts}"

    if not out_root:
        # put next to the input CSV inside a sibling 'pdf_pull' folder
        parent = os.path.dirname(input_csv)
        out_root = os.path.join(parent, "pdf_pull")

    pdf_dir = os.path.join(out_root, "pdfs")
    logs_dir = os.path.join(out_root, "logs")
    out_csv_path = os.path.join(out_root, "pdf_pull_results.csv")
    _ensure_dir(pdf_dir)
    _ensure_dir(logs_dir)

    results_log = os.path.join(logs_dir, "pull.log")
    _write_log_line(results_log, f"--- PDF Pull start {ts} | rows={len(rows)} | input={input_csv}")

    # friendly hints
    if not (os.getenv("UNPAYWALL_EMAIL","").strip()):
        print("[hint] UNPAYWALL_EMAIL not set; Unpaywall OA lookups will be skipped.")
    if not (os.getenv("OPENALEX_EMAIL","").strip()):
        print("[hint] OPENALEX_EMAIL not set; OpenAlex rate limits may be tighter.")
    if not (os.getenv("SEMANTIC_SCHOLAR_KEY","").strip()):
        print("[hint] SEMANTIC_SCHOLAR_KEY not set; S2 OA PDFs will be skipped.")

    processed = 0
    successes = 0
    out_rows: List[Dict[str,str]] = []

    # Single approval protecting all network calls (no LLM tokens)
    desc = (f"PDF Acquisition (NO LLM TOKENS) — rows={len(rows)} input={os.path.basename(input_csv)}")

    def _pull_all():
        nonlocal processed, successes, out_rows

        for i, r in enumerate(rows, start=1):
            if max_items and processed >= max_items:
                break
            title = _clean(r.get("title",""))
            doi = _norm_doi(r.get("doi",""))
            url = (r.get("url","") or "").strip()

            label = f"{i}/{len(rows)}: {title[:90]}{'...' if len(title)>90 else ''}"
            _dbg(f"Row {label} doi={doi or '∅'} url={url or '∅'}")

            attempts = _candidate_sources(r)
            pdf_got = False
            http_code = 0
            final_pdf_url = None
            source_name = ""
            note = ""

            for kind, token in attempts:
                final_pdf_url = _resolve_to_pdf_url(kind, token)
                if not final_pdf_url:
                    _dbg(f"  {kind}: no URL")
                    continue

                fname = _pick_filename(r, final_pdf_url)
                out_path = os.path.join(pdf_dir, fname)

                ok, http_code, why = _download_pdf(final_pdf_url, out_path)
                _dbg(f"  {kind} -> GET {final_pdf_url} :: ok={ok} http={http_code} note={why}")

                if ok:
                    pdf_got = True
                    source_name = kind
                    note = why
                    _write_log_line(results_log, f"[OK] {label} via {kind} → {fname}")
                    break
                else:
                    # remove partial file if any
                    try:
                        if os.path.exists(out_path) and os.path.getsize(out_path) < 1024:
                            os.remove(out_path)
                    except Exception:
                        pass
                    _write_log_line(results_log, f"[MISS] {label} {kind}: {why}")

            out_rows.append({
                "title": title,
                "doi": doi,
                "url": url,
                "year": _clean(r.get("year","")),
                "venue": _clean(r.get("venue","")),
                "pdf_status": "success" if pdf_got else "miss",
                "pdf_path": os.path.join("pdfs", os.path.basename(_pick_filename(r, final_pdf_url or title))) if pdf_got else "",
                "pdf_source": source_name,
                "http_status": str(http_code or ""),
                "note": note,
            })

            processed += 1
            if pdf_got:
                successes += 1

            # write progress incrementally
            if processed % 10 == 0:
                try:
                    _write_out_csv(out_csv_path, out_rows[-10:])
                except Exception as e:
                    _write_log_line(results_log, f"[warn] could not write chunk: {e}")

        # write any tail rows not flushed yet
        try:
            last_chunk = processed % 10
            if last_chunk:
                _write_out_csv(out_csv_path, out_rows[-last_chunk:])
        except Exception as e:
            _write_log_line(results_log, f"[warn] final chunk write failed: {e}")

        return True

    ok = approvals.request_approval(
        description=desc,
        call_fn=lambda ov=None: _with_temp_approval_mode("auto", _pull_all),
        timeout=None
    )
    if not ok:
        return False, "Approval denied or failed."

    # Summary
    _write_log_line(results_log, f"[FINAL] processed={processed} success={successes} out_csv={out_csv_path}")
    msg = (f"PDFs saved to: {pdf_dir}  | results CSV: {out_csv_path}  | "
           f"processed={processed}  success={successes}")
    print(msg)
    return True, msg

if __name__ == "__main__":
    # Minimal CLI usage:
    #   python tasks/lit_search_pull.py <input_csv> [max_items]
    import sys
    inp = sys.argv[1] if len(sys.argv) > 1 else ""
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    ok, msg = run(inp, None, cap)
    print("OK" if ok else "ERR", msg)
