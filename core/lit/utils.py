# core/lit/utils.py
import os, csv, datetime
from typing import List, Dict, Optional

def make_run_id() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")

def run_dirs(run_id: str) -> Dict[str, str]:
    base = os.path.join("outputs", "lit_runs", run_id)
    paths = {
        "base": base,
        "csv": os.path.join(base, "csv"),
        "meta": os.path.join(base, "meta"),
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths

def write_csv_row(path: str, row: Dict[str, str], header: List[str]) -> None:
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)

def read_single_row_csv(path: str) -> Optional[Dict[str, str]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        return rows[-1] if rows else None

def to_list(cell: str) -> List[str]:
    return [s.strip() for s in (cell or "").split("|;|") if s.strip()]

def from_list(items: List[str]) -> str:
    return " |;| ".join(dict.fromkeys([s.strip() for s in items if s and s.strip()]))
