# scripts/context_pack.py
import os
import sys
import fnmatch
import json
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime

# Folders/files to skip (in addition to .gitignore)
DEFAULT_EXCLUDES = [
    ".git", ".idea", ".vscode", "__pycache__", "venv", ".venv",
    "outputs", "data", ".cache", ".prompt_cache", "secrets",
    "*.log", "*.pyc", "*.pyo", "*.egg-info", "*.qt.*"
]

# Extensions to include (source + text docs)
INCLUDE_EXT = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".ini", ".cfg",
    ".ui", ".qss", ".csv"
}

ROOT = Path(__file__).resolve().parents[1]  # repo root
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

def is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    # folder/file exclusions
    for part in parts:
        for pat in DEFAULT_EXCLUDES:
            if pat.startswith("*."):
                if fnmatch.fnmatch(part, pat):
                    return True
            else:
                if part == pat:
                    return True
    # dotfiles at root we never want
    if rel in {".env", ".env.*"}:
        return True
    return False

def should_include_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in INCLUDE_EXT

def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def walk_sources():
    for p in ROOT.rglob("*"):
        if p == DIST:
            continue
        if any(is_excluded(parent) for parent in [p] + list(p.parents)):
            continue
        if should_include_file(p):
            yield p

def build_codemap(files):
    """Create a quick map of modules and sizes."""
    tree = {}
    total_bytes = 0
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        size = f.stat().st_size
        total_bytes += size
        parts = rel.split("/")
        cur = tree
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = {"size": size}
    return tree, total_bytes

def main():
    files = sorted(set(walk_sources()))
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    codemap_tree, total_bytes = build_codemap(files)

    # Write CODEMAP (human-friendly)
    codemap_path = DIST / f"CODEMAP-{ts}.md"
    with codemap_path.open("w", encoding="utf-8") as out:
        out.write(f"# CODEMAP ({ts} UTC)\n\n")
        out.write(f"Root: {ROOT}\n")
        out.write(f"Total files: {len(files)} | Total bytes: {total_bytes}\n\n")
        def dump(d, indent=0, prefix=""):
            for k, v in sorted(d.items()):
                if isinstance(v, dict) and "size" not in v:
                    out.write("  " * indent + f"- {k}/\n")
                    dump(v, indent+1, prefix + k + "/")
                else:
                    out.write("  " * indent + f"- {k} ({v['size']} bytes)\n")
        dump(codemap_tree)

    # Zip bundle (code + README snapshot)
    zip_path = DIST / f"ailys-context-{ts}.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
        # Include all sources
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            z.write(f, arcname=rel)
        # Include CODEMAP
        z.write(codemap_path, arcname=codemap_path.name)

        # Add a lightweight MANIFEST.json with hashes
        manifest = []
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            manifest.append({
                "path": rel,
                "bytes": f.stat().st_size,
                "sha": sha256sum(f)
            })
        manifest_bytes = json.dumps({
            "generated_utc": ts,
            "files": manifest
        }, indent=2).encode("utf-8")
        z.writestr("MANIFEST.json", manifest_bytes)

    print(f"✅ Packed {len(files)} files")
    print(f"   • {codemap_path}")
    print(f"   • {zip_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
