# tasks/lit_dedupe.py
from __future__ import annotations

import os, csv, re, time, unicodedata
from typing import Optional, Dict, List, Tuple
import core.approval_queue as approvals

# ---------- Config knobs ----------
def _throttle_ms() -> int:
    # Sleep this many ms every _THROTTLE_EVERY rows
    try:
        return max(0, int(os.getenv("LIT_DEDUPE_SLEEP_MS", "25")))
    except Exception:
        return 25

def _throttle_every() -> int:
    try:
        return max(1, int(os.getenv("LIT_DEDUPE_THROTTLE_EVERY", "500")))
    except Exception:
        return 500

def _chunk_rows() -> int:
    # Re-dedupe + write progress every this many input rows
    try:
        return max(200, int(os.getenv("LIT_DEDUPE_CHUNK", "2000")))
    except Exception:
        return 2000

# ---------- Stop & logging ----------
def _should_stop(stop_flag_path: str | None = None) -> bool:
    try:
        if os.getenv("LIT_STOP", "") == "1":
            return True
        if stop_flag_path and os.path.exists(stop_flag_path):
            return True
    except Exception:
        pass
    return False

def _write_log_line(path: str, line: str):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass

# ---------- CSV helpers ----------
CSV2_HEADER = [
    "run_id","engine","query","term_origin","work_id","title","authors|;|",
    "year","venue","doi","url","abstract","source_score","first_author_last"
]

def _ensure_csv_header(path: str):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except Exception:
        pass
    if os.path.exists(path):
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore").writeheader()

def _write_csv(path: str, rows: List[Dict[str,str]]):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV2_HEADER, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)

# ---------- Normalizers (copied, minimal) ----------
def _clean_text(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"<[^>]+>", " ", s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    d = doi.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    return d.lower()

def _first_author_last(authors_field: str) -> str:
    if not authors_field:
        return ""
    s = _clean_text(authors_field)
    parts = re.split(r"[;|,]\s*(?=[A-Z][^;|,]*)|;\s+| \|\| |\|;|;", s) or [s]
    first = parts[0].strip()
    m = re.match(r"^\s*([A-Za-z'`-]+)\s*,\s*.+$", first)
    if m:
        last = m.group(1)
    else:
        tokens = re.split(r"\s+", first)
        tokens = [t for t in tokens if not re.match(r"^[A-Z]\.?$", t)]
        last = tokens[-1] if tokens else ""
    last = unicodedata.normalize("NFKC", last)
    last = re.sub(r"[^A-Za-z'`-]", "", last)
    return last.lower()

def _norm_title(title: str) -> str:
    if not title:
        return ""
    t = _clean_text(title).lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _title_prefix_key(norm_title: str, n: int = None) -> str:
    try:
        if n is None:
            n = int(os.getenv("LIT_TITLE_PREFIX", "12"))
    except Exception:
        n = 12
    return (norm_title or "")[:n]

def _fuzzy_sim(a: str, b: str) -> float:
    a = (a or "").strip(); b = (b or "").strip()
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz
        return fuzz.token_set_ratio(a, b) / 100.0
    except Exception:
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return 0.0
        inter = len(sa & sb); union = len(sa | sb)
        cont = inter / max(1, min(len(sa), len(sb)))
        jac = inter / max(1, union)
        return 0.5 * cont + 0.5 * jac

def _normalize_row(r: Dict[str, str]) -> Dict[str, str]:
    r = dict(r)
    r["title"] = _clean_text(r.get("title", ""))
    r["venue"] = _clean_text(r.get("venue", ""))
    r["abstract"] = _clean_text(r.get("abstract", ""))
    r["authors|;|"] = _clean_text(r.get("authors|;|", ""))
    r["doi"] = _normalize_doi(r.get("doi"))
    if not r.get("first_author_last"):
        r["first_author_last"] = _first_author_last(r.get("authors|;|", "")) or ""
    r["_norm_title"] = _norm_title(r.get("title", ""))
    r["_title_prefix"] = _title_prefix_key(r["_norm_title"])
    url = (r.get("url") or "").strip()
    url = re.sub(r"[\x00-\x1F\x7F]", "", url)
    r["url"] = url
    return r

def _merge_records(rows: List[Dict[str,str]]) -> Dict[str,str]:
    if not rows:
        return {}

    # Engine precedence (leftmost preferred for ties)
    engine_rank = {e: i for i, e in enumerate(["OpenAlex","Crossref","SemanticScholar","PubMed","arXiv"])}

    # Build comparable scores that never include dicts
    scored: List[Tuple[Tuple, Dict[str,str]]] = []
    for r in rows:
        rr = _normalize_row(r)

        abs_text = rr.get("abstract") or ""
        abs_len = len(abs_text)
        doi_present = 1 if rr.get("doi") else 0
        venue_present = 1 if (rr.get("venue") or "").strip() else 0
        authors_present = 1 if (rr.get("authors|;|") or "").strip() else 0
        year_present = 1 if (rr.get("year") or "").strip() else 0
        engine_score = -engine_rank.get(rr.get("engine",""), 99)

        # Prefer abstracts ≥120 chars
        abs_tier = 2 if abs_len >= 120 else (1 if abs_len > 0 else 0)

        # Stable string tie-breakers (safe to compare)
        engine_name = rr.get("engine","") or ""
        title_key = rr.get("title","") or ""

        score = (
            doi_present,     # 0
            abs_tier,        # 1
            abs_len,         # 2
            venue_present,   # 3
            authors_present, # 4
            year_present,    # 5
            engine_score,    # 6
            engine_name,     # 7  (string tiebreaker)
            title_key        # 8  (string tiebreaker)
        )
        scored.append((score, rr))

    # Pick the best by score (no dict comparison involved)
    best = dict(max(scored, key=lambda t: t[0])[1])

    # Fill missing fields from the others
    for _, rr in scored:
        for k in ["doi","url","title","venue","year","authors|;|","abstract",
                  "work_id","engine","query","term_origin","source_score","run_id"]:
            if not (best.get(k) or "").strip():
                v = (rr.get(k) or "").strip()
                if v:
                    best[k] = v

        # Prefer longer abstracts up to the 120-char threshold
        old_abs = best.get("abstract") or ""
        new_abs = rr.get("abstract") or ""
        if len(new_abs) >= 120 and len(old_abs) < 120:
            best["abstract"] = new_abs
        elif len(new_abs) > len(old_abs) and len(old_abs) < 120:
            best["abstract"] = new_abs

    # Drop internal fields
    best.pop("_norm_title", None)
    best.pop("_title_prefix", None)
    return best


def _merge_dedupe(rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
    with_doi: Dict[str, List[Dict[str,str]]] = {}
    no_doi: List[Dict[str,str]] = []
    for r in rows:
        rr = _normalize_row(r)
        (with_doi.setdefault(rr.get("doi",""), []).append(rr)) if rr.get("doi","") else no_doi.append(rr)
    merged: List[Dict[str,str]] = []
    for doi, bucket in with_doi.items():
        merged.append(_merge_records(bucket))
    try:
        FUZZY_THRESH = float(os.getenv("LIT_FUZZY_THRESH", "0.88"))
    except Exception:
        FUZZY_THRESH = 0.88
    primary_blocks: Dict[tuple, List[Dict[str,str]]] = {}
    for rr in no_doi:
        key = (rr.get("first_author_last") or "", (rr.get("year") or "").strip())
        primary_blocks.setdefault(key, []).append(rr)
    for _, p_bucket in primary_blocks.items():
        if len(p_bucket) == 1:
            merged.append(p_bucket[0]); continue
        secondary: Dict[str, List[Dict[str,str]]] = {}
        for rr in p_bucket:
            secondary.setdefault(rr.get("_title_prefix",""), []).append(rr)
        for _, s_bucket in secondary.items():
            if len(s_bucket) == 1:
                merged.append(s_bucket[0]); continue
            s_bucket = list(s_bucket)
            visited = [False]*len(s_bucket)
            for i in range(len(s_bucket)):
                if visited[i]: continue
                seed = s_bucket[i]; cluster = [seed]; visited[i] = True
                t0 = seed.get("_norm_title","")
                for j in range(i+1, len(s_bucket)):
                    if visited[j]: continue
                    cand = s_bucket[j]
                    if _fuzzy_sim(t0, cand.get("_norm_title","")) >= FUZZY_THRESH:
                        cluster.append(cand); visited[j] = True
                if len(cluster) == 1:
                    merged.append(seed)
                else:
                    merged.append(_merge_records(cluster))
    for r in merged:
        r.pop("_norm_title", None); r.pop("_title_prefix", None)
    return merged

# ---------- Core worker ----------
def _dedupe_streaming(input_csv_path: str, out_final: str, progress_csv: str, logs_dir: str) -> Tuple[bool, str]:
    """
    Stream the input CSV, merge/dedupe incrementally, throttle CPU, honor STOP, and
    ALWAYS write a status file that the caller can read to obtain (ok, msg).
    """
    stop_flag = os.path.join(logs_dir, "STOP")
    status_path = os.path.join(logs_dir, "status.txt")
    try:
        os.environ["LIT_STOP_FLAG_PATH"] = stop_flag
    except Exception:
        pass

    log_path = os.path.join(logs_dir, "dedupe.log")
    _write_log_line(log_path, f"START dedupe for {input_csv_path}")
    _ensure_csv_header(out_final)     # create immediately so UI sees the file
    _ensure_csv_header(progress_csv)  # progress file too

    rows_accum: List[Dict[str,str]] = []
    total_in = 0
    last_progress_write = 0
    THR_MS = _throttle_ms()
    THR_EVERY = _throttle_every()
    CHUNK = _chunk_rows()

    try:
        # utf-8-sig: handles BOM; errors='ignore' to be resilient to mixed encodings
        with open(input_csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                # Skip completely empty rows (all fields empty/whitespace)
                if not any((v or "").strip() for v in row.values()):
                    continue

                rows_accum.append(dict(row))
                total_in += 1

                # throttle (yield CPU)
                if THR_MS and (total_in % THR_EVERY == 0):
                    time.sleep(THR_MS / 1000.0)

                # check for stop regularly
                if _should_stop(stop_flag):
                    _write_log_line(log_path, f"STOP requested at input_row={total_in}; writing partial FINAL.")
                    try:
                        final_rows = _merge_dedupe(rows_accum)
                    except Exception:
                        final_rows = rows_accum  # worst-case fallback

                    try:
                        os.remove(out_final)
                    except Exception:
                        pass
                    _ensure_csv_header(out_final)
                    _write_csv(out_final, final_rows)

                    # mark interruption artifacts
                    try:
                        with open(os.path.join(logs_dir, "INTERRUPTED"), "w", encoding="utf-8") as g:
                            g.write("Stop requested during de-dup; wrote best partial FINAL.\n")
                    except Exception:
                        pass
                    try:
                        with open(status_path, "w", encoding="utf-8") as sf:
                            sf.write(f"OK ⛔ FINAL (partial) written: {out_final} | rows={len(final_rows)}\n")
                    except Exception:
                        pass
                    return True, f"⛔ FINAL (partial) written: {out_final} | rows={len(final_rows)}"

                # periodic progress snapshot (overwrites progress file)
                if total_in - last_progress_write >= CHUNK:
                    ded = _merge_dedupe(rows_accum)
                    try:
                        os.remove(progress_csv)
                    except Exception:
                        pass
                    _ensure_csv_header(progress_csv)
                    _write_csv(progress_csv, ded)
                    last_progress_write = total_in
                    _write_log_line(log_path, f"progress: input_rows={total_in} progress_rows={len(ded)}")
    except Exception as e:
        try:
            with open(status_path, "w", encoding="utf-8") as sf:
                sf.write(f"ERR Could not read CSV: {e}\n")
        except Exception:
            pass
        _write_log_line(log_path, f"ERR while streaming input at row ~{total_in}: {e}")
        return False, f"Could not read CSV: {e}"

    # final merge & write FINAL
    try:
        final_rows = _merge_dedupe(rows_accum)
    except Exception:
        # uniqueness fallback
        seen = set(); final_rows = []
        for r in rows_accum:
            doi = (r.get("doi","") or "").lower().strip()
            t = (_norm_title(r.get("title","")) or "")
            y = (r.get("year","") or "").strip()
            key = f"doi::{doi}" if doi else f"title::{t}::{y}"
            if key in seen: continue
            seen.add(key); final_rows.append(r)

    try:
        try:
            os.remove(out_final)
        except Exception:
            pass
        _ensure_csv_header(out_final)
        _write_csv(out_final, final_rows)
    except Exception as e:
        try:
            with open(status_path, "w", encoding="utf-8") as sf:
                sf.write(f"ERR Failed to write final CSV: {e}\n")
        except Exception:
            pass
        return False, f"Failed to write final CSV: {e}"

    _write_log_line(log_path, f"END dedupe: input_rows={total_in} final_rows={len(final_rows)}")
    try:
        with open(status_path, "w", encoding="utf-8") as sf:
            sf.write(f"OK FINAL (dedup+merged) written: {out_final} | rows={len(final_rows)}\n")
    except Exception:
        pass
    return True, f"FINAL (dedup+merged) written: {out_final} | rows={len(final_rows)}"


# ---------- Public entry (approval-gated, NO LLM TOKENS) ----------
def run(input_csv_path: str, output_dir: Optional[str] = None, save_prefix: Optional[str] = None) -> Tuple[bool, str]:
    """
    De-duplicate/merge an existing CSV of candidates.
    - Creates the FINAL file immediately with header (so you see progress has begun).
    - Shows an Approval: "NO LLM TOKENS" so you can set a timeout.
    - Obeys Stop (env LIT_STOP=1 or STOP file under logs dir).
    - Throttles CPU via LIT_DEDUPE_SLEEP_MS / LIT_DEDUPE_THROTTLE_EVERY.
    """
    if not os.path.exists(input_csv_path):
        return False, f"Input CSV not found: {input_csv_path}"

    out_dir = output_dir or os.path.dirname(os.path.abspath(input_csv_path)) or "."
    safe_prefix = re.sub(r"[^\w\-.]+", "_", (save_prefix or "").strip()) if save_prefix else ""
    # foldering: put logs alongside FINAL
    logs_dir = os.path.join(out_dir, "logs")
    try:
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        pass

    basename = f"{safe_prefix}_" if safe_prefix else ""
    out_final = os.path.join(out_dir, f"{basename}search_results_final.csv")
    progress_csv = os.path.join(out_dir, f"{basename}search_results_final.progress.csv")

    # ensure visible from the start
    _ensure_csv_header(out_final)
    _ensure_csv_header(progress_csv)

    # approval gate (NO LLM TOKENS)
    desc = f"De-duplicate Candidates — NO LLM TOKENS | input={os.path.basename(input_csv_path)}"
    status_path = os.path.join(logs_dir, "status.txt")

    def _call(_ov=None):
        # Run the worker; it will write status.txt for us to read
        return _dedupe_streaming(input_csv_path, out_final, progress_csv, logs_dir)

    ok = approvals.request_approval(
        description=desc,
        call_fn=_call,
        timeout=None  # user can set timeout override in Approvals pane
    )
    # approvals returns bool (approved/denied), not the worker result.
    # Read the worker's status file to get the real outcome.
    if not ok:
        return False, "Approval denied or failed."

    real_ok, real_msg = True, f"✅ De-duplication completed. See: {out_final}"
    try:
        with open(status_path, "r", encoding="utf-8") as sf:
            last = ""
            for ln in sf:
                if ln.strip():
                    last = ln.strip()
            if last:
                if last.startswith("ERR"):
                    real_ok = False
                    real_msg = last[3:].strip()
                elif last.startswith("OK"):
                    real_ok = True
                    real_msg = last[2:].strip()
    except Exception:
        # Fallback: count rows in out_final to give a truthful message
        try:
            with open(out_final, "r", encoding="utf-8-sig", errors="ignore") as f:
                r = csv.DictReader(f)
                n = sum(1 for _ in r)
            if n == 0:
                real_ok = False
                real_msg = f"No rows written (header only). Check logs at {logs_dir}."
            else:
                real_msg = f"FINAL written: {out_final} | rows={n}"
        except Exception as e:
            real_ok = False
            real_msg = f"Could not verify output: {e}"

    return real_ok, real_msg

