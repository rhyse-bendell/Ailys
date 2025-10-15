# -*- coding: utf-8 -*-
#!/usr/bin/.env python3
"""
ailys_snapshot.py
Local repo introspector for "Ailys" with GUI folder picker (Tkinter) and safe fallbacks.

Outputs:
- ailys_report.md   (human-readable summary)
- ailys_report.json (structured machine-readable dump)

Only uses Python standard library.
"""

import argparse
import fnmatch
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional

# Optional GUI folder picker (fallbacks to console prompt if unavailable)
try:
    from tkinter import Tk, filedialog  # type: ignore
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False


# =========================
# Helpers
# =========================

def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    s = float(n)
    for u in units:
        if s < 1024 or u == units[-1]:
            return f"{s:.1f} {u}"
        s /= 1024.0

def safe_read_text(p: Path, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        if not p.exists() or not p.is_file():
            return None
        if p.stat().st_size > max_bytes:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def run_pip_freeze(timeout_sec: int = 30) -> List[str]:
    try:
        cmd = [sys.executable, "-m", "pip", "freeze"]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout_sec)
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []

def detect_python_env() -> Dict[str, str]:
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "platform": sys.platform,
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, "base_prefix", ""),
        "virtual_env_var": os.environ.get("VIRTUAL_ENV", ""),
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
    }

def iter_tree(root: Path, max_depth: int) -> List[Dict]:
    results = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        depth = Path(dirpath).relative_to(root).parts
        if len(depth) > max_depth:
            dirnames[:] = []
            continue
        dirnames.sort()
        filenames.sort()
        entry = {
            "dir": str(Path(dirpath)),
            "dirs": dirnames[:],
            "files": [],
        }
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                size = fp.stat().st_size
            except Exception:
                size = 0
            entry["files"].append({"name": f, "size_bytes": size})
        results.append(entry)
    return results

def render_tree_md(root: Path, tree_data: List[Dict], max_depth: int) -> str:
    lines = [f"**Root:** `{root}`  ", f"**Max depth:** {max_depth}", ""]
    for chunk in tree_data:
        rel = Path(chunk["dir"]).relative_to(root)
        indent_level = 0 if str(rel) == "." else len(rel.parts)
        lines.append(f"{'  ' * indent_level}- 📁 {rel if str(rel)!='.' else root.name}")
        for f in chunk["files"]:
            lines.append(f"{'  ' * (indent_level+1)}- {f['name']} ({human_size(f['size_bytes'])})")
    return "\n".join(lines)

MAIN_GUARDS = re.compile(r"if\s+__name__\s*==\s*[\"']__main__[\"']\s*:", re.IGNORECASE)
ARGPARSE_IMPORT = re.compile(r"^\s*import\s+argparse\b|^\s*from\s+argparse\s+import\b", re.IGNORECASE | re.MULTILINE)
CLICK_IMPORT = re.compile(r"^\s*import\s+click\b|^\s*from\s+click\s+import\b", re.IGNORECASE | re.MULTILINE)
GUI_HINTS = [
    ("tkinter", re.compile(r"\bimport\s+tkinter\b|\bfrom\s+tkinter\s+import\b")),
    ("PyQt5", re.compile(r"\bfrom\s+PyQt5\b|\bimport\s+PyQt5\b")),
    ("PySide6", re.compile(r"\bfrom\s+PySide6\b|\bimport\s+PySide6\b")),
    ("PySide2", re.compile(r"\bfrom\s+PySide2\b|\bimport\s+PySide2\b")),
    ("dearpygui", re.compile(r"\bimport\s+dearpygui\b")),
    ("customtkinter", re.compile(r"\bimport\s+customtkinter\b")),
]

SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]"),
    re.compile(r"(?i)\bsecret\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]"),
    re.compile(r"(?i)\btoken\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]"),
]

def scan_code_for_entrypoints_and_gui(py_file: Path) -> Dict[str, object]:
    info = {"has_main_guard": False, "uses_argparse": False, "uses_click": False, "gui_hits": []}
    src = safe_read_text(py_file)
    if not src:
        return info
    if MAIN_GUARDS.search(src):
        info["has_main_guard"] = True
    if ARGPARSE_IMPORT.search(src):
        info["uses_argparse"] = True
    if CLICK_IMPORT.search(src):
        info["uses_click"] = True
    for name, pattern in GUI_HINTS:
        if pattern.search(src):
            info["gui_hits"].append(name)
    return info

def find_files(root: Path, patterns: List[str]) -> List[Path]:
    matches = []
    for dirpath, _, filenames in os.walk(root):
        for p in patterns:
            for fname in fnmatch.filter(filenames, p):
                matches.append(Path(dirpath) / fname)
    return matches

def load_requirements(req_path: Path) -> List[str]:
    lines = []
    txt = safe_read_text(req_path, max_bytes=500_000)
    if txt:
        for line in txt.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                lines.append(s)
    return lines

def parse_pyproject(pyproj: Path) -> Dict:
    data = {}
    try:
        # Python 3.11+: tomllib is stdlib
        try:
            import tomllib  # type: ignore
            with pyproj.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            # Minimal fallback: store raw text so we at least capture content
            txt = safe_read_text(pyproj, max_bytes=500_000) or ""
            data = {"_raw": txt}
    except Exception:
        data = {}
    return data

def extract_sqlite_schema(db_path: Path) -> Dict[str, List[str]]:
    schema = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view','index','trigger') ORDER BY type, name;")
        rows = cur.fetchall()
        for name, typ, sql in rows:
            schema.setdefault(typ, []).append(sql or f"-- {name} (no SQL)")
        conn.close()
    except Exception as e:
        schema = {"error": [repr(e)]}
    return schema

def scan_for_secrets(text: str) -> int:
    count = 0
    for pat in SECRET_PATTERNS:
        for _ in pat.finditer(text):
            count += 1
    return count

def list_special_dirs(root: Path) -> Dict[str, List[str]]:
    names = ["outputs", "logs", "cache", "data", "artifacts"]
    found = {n: [] for n in names}
    for dirpath, dirnames, _ in os.walk(root):
        for n in names:
            if Path(dirpath).name.lower() == n:
                found[n].append(str(Path(dirpath)))
    for n in names:
        p = root / n
        if p.exists() and p.is_dir():
            if str(p) not in found[n]:
                found[n].append(str(p))
    return found


# =========================
# Main collection
# =========================

def collect_snapshot(root: Path, max_depth: int) -> Dict:
    t0 = time.time()
    root = root.resolve()

    snapshot = {
        "meta": {
            "root": str(root),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool": "ailys_snapshot.py",
            "version": "1.1.0",
        },
        "environment": detect_python_env(),
        "pip_freeze": run_pip_freeze(),
        "tree": iter_tree(root, max_depth=max_depth),
        "dependencies": {
            "requirements_txt": [],
            "pyproject_toml": {},
        },
        "entry_points": [],
        "gui_indicators": {},
        "config_files": [],
        "sqlite_schemas": {},
        "special_dirs": {},
        "potential_parsers": [],
        "secrets_summary": {
            "files_scanned": 0,
            "matches_found": 0
        },
        "errors": [],
        "duration_sec": None,
    }

    # Dependencies
    req_files = find_files(root, ["requirements.txt", "requirements-*.txt"])
    if req_files:
        req_files.sort(key=lambda p: len(p.relative_to(root).parts))
        snapshot["dependencies"]["requirements_txt"] = load_requirements(req_files[0])

    pyproj_files = find_files(root, ["pyproject.toml"])
    if pyproj_files:
        pyproj_files.sort(key=lambda p: len(p.relative_to(root).parts))
        snapshot["dependencies"]["pyproject_toml"] = parse_pyproject(pyproj_files[0])

    # Entry points + GUI hints + secrets count
    py_files = find_files(root, ["*.py"])
    gui_agg: Dict[str, List[str]] = {}
    secrets_count = 0
    files_scanned = 0

    for pf in py_files:
        info = scan_code_for_entrypoints_and_gui(pf)
        if info["has_main_guard"] or info["uses_argparse"] or info["uses_click"]:
            snapshot["entry_points"].append({
                "path": str(pf.relative_to(root)),
                **info
            })
        if info["gui_hits"]:
            gui_agg[str(pf.relative_to(root))] = info["gui_hits"]

        txt = safe_read_text(pf, max_bytes=300_000)
        if txt:
            files_scanned += 1
            secrets_count += scan_for_secrets(txt)

    snapshot["gui_indicators"] = gui_agg
    snapshot["secrets_summary"]["files_scanned"] = files_scanned
    snapshot["secrets_summary"]["matches_found"] = secrets_count

    # Config files
    cfg_patterns = ["*..env", "..env", "*.ini", "*.cfg", "*.conf", "*.yaml", "*.yml", "*.json"]
    cfgs = []
    for pat in cfg_patterns:
        cfgs.extend(find_files(root, [pat]))
    snapshot["config_files"] = [str(c.relative_to(root)) for c in sorted(set(cfgs), key=lambda p: str(p))]

    # SQLite schemas
    db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]
    dbs = []
    for pat in db_patterns:
        dbs.extend(find_files(root, [pat]))
    for db in dbs:
        snapshot["sqlite_schemas"][str(db.relative_to(root))] = extract_sqlite_schema(db)

    # Special dirs (outputs/logs/cache/…)
    snapshot["special_dirs"] = list_special_dirs(root)

    # Parsers (by simple naming heuristics)
    likely_parsers = []
    for pf in py_files:
        name = pf.name.lower()
        if any(key in name for key in ["parser", "parse", "citation", "apa", "lit_review", "batch", "viz", "storage"]):
            likely_parsers.append(str(pf.relative_to(root)))
    snapshot["potential_parsers"] = sorted(set(likely_parsers))

    snapshot["duration_sec"] = round(time.time() - t0, 2)
    return snapshot


# =========================
# Rendering
# =========================

def to_markdown(root: Path, data: Dict, tree_data: List[Dict], max_depth: int) -> str:
    md = []
    md.append(f"# Ailys Snapshot Report\n")
    md.append(f"- **Root:** `{root}`")
    md.append(f"- **Generated:** {data['meta']['timestamp']}")
    md.append(f"- **Tool:** {data['meta']['tool']} v{data['meta']['version']}")
    md.append(f"- **Duration:** {data['duration_sec']} sec")
    md.append("")

    # Environment
    env = data["environment"]
    md.append("## Environment")
    md.append(f"- Python: `{env['python_version']}`")
    md.append(f"- Executable: `{env['python_executable']}`")
    md.append(f"- Platform: `{env['platform']}`")
    if env.get("virtual_env_var"):
        md.append(f"- VIRTUAL_ENV: `{env['virtual_env_var']}`")
    if env.get("conda_prefix"):
        md.append(f"- CONDA_PREFIX: `{env['conda_prefix']}`")
    md.append("")

    # Dependencies
    md.append("## Dependencies")
    req = data["dependencies"].get("requirements_txt", [])
    if req:
        md.append("**requirements.txt (parsed):**")
        md.append("```")
        md.extend(req)
        md.append("```")
    else:
        md.append("_No requirements.txt found (or empty)._")
    md.append("")
    if data["dependencies"].get("pyproject_toml"):
        md.append("**pyproject.toml (parsed/partial):**")
        md.append("```json")
        md.append(json.dumps(data["dependencies"]["pyproject_toml"], indent=2)[:50_000])
        md.append("```")
    else:
        md.append("_No pyproject.toml found._")
    md.append("")

    # Pip freeze
    md.append("## pip freeze (environment snapshot)")
    if data["pip_freeze"]:
        md.append("<details><summary>Show packages</summary>\n\n```")
        md.extend(data["pip_freeze"][:1000])  # cap just in case
        md.append("```\n</details>")
    else:
        md.append("_pip freeze unavailable or empty._")
    md.append("")

    # Entry points
    md.append("## Likely Entry Points (main guards / CLI)")
    if data["entry_points"]:
        for ep in data["entry_points"]:
            md.append(f"- `{ep['path']}`  "
                      f"(main: {ep['has_main_guard']}, argparse: {ep['uses_argparse']}, click: {ep['uses_click']})")
    else:
        md.append("_None detected._")
    md.append("")

    # GUI indicators
    md.append("## GUI Indicators")
    if data["gui_indicators"]:
        for path, hits in data["gui_indicators"].items():
            md.append(f"- `{path}` → {', '.join(hits)}")
    else:
        md.append("_No GUI imports detected (tkinter/PyQt/PySide/etc.)._")
    md.append("")

    # Config files
    md.append("## Config Files Detected")
    if data["config_files"]:
        for c in data["config_files"]:
            md.append(f"- `{c}`")
    else:
        md.append("_None found._")
    md.append("")

    # SQLite schemas
    md.append("## SQLite Schemas")
    if data["sqlite_schemas"]:
        for db, schema in data["sqlite_schemas"].items():
            md.append(f"### `{db}`")
            for typ, stmts in schema.items():
                md.append(f"**{typ.upper()}**")
                md.append("```sql")
                joined = "\n\n".join(stmts)
                md.append(joined[:20_000])
                md.append("```")
    else:
        md.append("_No SQLite databases found._")
    md.append("")

    # Special dirs
    md.append("## Outputs / Logs / Cache Directories")
    if data["special_dirs"]:
        for k, v in data["special_dirs"].items():
            if v:
                md.append(f"- **{k}**:")
                for p in v:
                    md.append(f"  - `{p}`")
    md.append("")

    # Potential parser/formatter modules
    md.append("## Potential Parser / Formatter / Core Modules")
    if data["potential_parsers"]:
        for p in data["potential_parsers"]:
            md.append(f"- `{p}`")
    else:
        md.append("_None flagged by naming heuristics._")
    md.append("")

    # Secrets (counts only)
    sec = data["secrets_summary"]
    md.append("## Secrets Scan (counts only)")
    md.append(f"- Files scanned: **{sec['files_scanned']}**")
    md.append(f"- Potential secret patterns found: **{sec['matches_found']}**")
    md.append("> Note: This does not print secrets—only counts.")
    md.append("")

    # Tree (depth-limited)
    md.append("## Repo Tree (depth-limited)")
    md.append(render_tree_md(root, data["tree"], max_depth=max_depth))
    md.append("")

    return "\n".join(md)


# =========================
# CLI / Entry
# =========================

def pick_folder_dialog(title: str = "Select the Ailys project folder") -> Optional[str]:
    if TK_AVAILABLE:
        try:
            root = Tk()
            root.withdraw()
            root.update()
            path = filedialog.askdirectory(title=title)
            root.destroy()
            return path or None
        except Exception:
            return None
    return None

def main():
    ap = argparse.ArgumentParser(
        description="Generate a machine- and human-readable snapshot of an Ailys codebase."
    )
    ap.add_argument("root", nargs="?", help="Path to the Ailys project folder (optional; GUI picker will appear if omitted)")
    ap.add_argument("--out", default=None, help="Output directory for report files (default: same as root)")
    ap.add_argument("--max-depth", type=int, default=3, help="Max folder depth for the tree (default 3)")
    args = ap.parse_args()

    root_path = args.root

    # If no path provided, try GUI picker; fallback to console input
    if not root_path:
        root_path = pick_folder_dialog()
        if not root_path:
            try:
                root_path = input("Enter the path to your Ailys project folder (or leave blank to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                root_path = ""
        if not root_path:
            print("❌ No folder selected or provided. Exiting.")
            sys.exit(1)

    root = Path(root_path).expanduser()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: Root path not found or not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.out).expanduser() if args.out else root
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Could not create output directory {outdir}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        snapshot = collect_snapshot(root, max_depth=args.max_depth)
        md = to_markdown(root, snapshot, snapshot["tree"], max_depth=args.max_depth)

        md_path = outdir / "ailys_report.md"
        json_path = outdir / "ailys_report.json"

        md_path.write_text(md, encoding="utf-8")
        json_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

        print(f"✅ Wrote: {md_path}")
        print(f"✅ Wrote: {json_path}")
        print("Done.")
    except Exception:
        tb = traceback.format_exc()
        print("ERROR during snapshot:\n", tb, file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
