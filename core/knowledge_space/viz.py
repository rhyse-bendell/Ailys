# core/knowledge_space/viz.py
# Zoomable, hoverable visualizations using Plotly + safe Matplotlib backend.
# Now run-scoped: if core/knowledge_space/paths.ensure_run_dirs is available,
# outputs go to outputs/ks_runs/{label}/{run_id}/viz[/units]; otherwise fall back
# to legacy outputs/ks_viz paths.

import os
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

# Use a non-interactive backend to avoid GUI-in-thread warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.express as px
import pandas as pd

from .storage import DB_PATH

# Optional run-scoped output support
try:
    from .paths import ensure_run_dirs  # introduced by paths.py helper
except Exception:
    ensure_run_dirs = None  # type: ignore

# Legacy fallback dirs (used only if ensure_run_dirs is missing)
LEGACY_OUT_DIR = "outputs/ks_viz"


def _resolve_viz_dirs(root_path: str | None, run_id: str | None, label: str):
    """
    Resolve output directories and filenames for this visualization run.
    If paths.ensure_run_dirs is available and root_path is provided, we use:
        outputs/ks_runs/{label_safe}/{run_id}/viz
        outputs/ks_runs/{label_safe}/{run_id}/viz/units
    Otherwise, we fall back to legacy outputs/ks_viz[/units/{label}]
    Returns: dict with keys: out_dir, units_dir, global_html, global_png
    """
    if root_path and ensure_run_dirs:
        run_base, sub = ensure_run_dirs(root_path, run_id=run_id)
        out_dir = sub["viz"]
        units_dir = sub["units"]
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(units_dir, exist_ok=True)
        return {
            "out_dir": out_dir,
            "units_dir": units_dir,
            "global_html": os.path.join(out_dir, f"global_timeline_{label}.html"),
            "global_png": os.path.join(out_dir, f"global_timeline_{label}.png"),
            "meta_path": os.path.join(run_base, "meta.json")
        }

    # Legacy fallback
    out_dir = LEGACY_OUT_DIR
    units_dir = os.path.join(out_dir, "units", label)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(units_dir, exist_ok=True)
    return {
        "out_dir": out_dir,
        "units_dir": units_dir,
        "global_html": os.path.join(out_dir, f"global_timeline_{label}.html"),
        "global_png": os.path.join(out_dir, f"global_timeline_{label}.png"),
        "meta_path": None
    }


def _fetch_events_with_units():
    """
    Returns a list of dicts:
    {
      'ts': datetime,
      'actor': str,
      'actor_tag': str,
      'artifact_id': str,
      'unit': str,           # mentioned_unit if present, else rel_path/path, else artifact_id[:8]
      'parsed_ok': bool,     # True if mentioned_unit existed in payload_json
      'source': str,         # filesystem/changelog/etc
      'summary': str,        # short delta summary if present
    }
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT e.id, e.ts, e.actor, e.artifact_id, e.source, d.summary, d.payload_json
        FROM events e
        LEFT JOIN deltas d ON d.version_id = e.version_id
        ORDER BY e.ts ASC
    """).fetchall()
    conn.close()

    out = []
    for (eid, ts, actor, aid, source, summary, payload_json) in rows:
        try:
            ts_dt = datetime.fromisoformat(ts)
        except Exception:
            continue

        unit = None
        parsed_ok = False
        if payload_json:
            try:
                p = json.loads(payload_json)
                # Prefer the *mentioned* target (actual item changed)
                unit = p.get("mentioned_unit")
                if unit:
                    parsed_ok = True
                else:
                    unit = p.get("rel_path") or p.get("path")
                if unit and isinstance(unit, str):
                    unit = unit.replace("\\", "/")
                    # If absolute, shorten to filename for readability
                    if unit.startswith("/") or ":" in unit:
                        unit = os.path.basename(unit)
            except Exception:
                pass
        if not unit:
            unit = aid[:8]

        actor = actor or ""
        out.append({
            "ts": ts_dt,
            "actor": actor,
            "actor_tag": _actor_tag(actor),
            "artifact_id": aid,
            "unit": unit,
            "parsed_ok": parsed_ok,
            "source": source or "",
            "summary": summary or "",
        })
    return out


def _actor_tag(actor: str) -> str:
    if not actor:
        return "?"
    # Short 2–3 letter tag
    parts = [p for p in actor.replace(".", " ").replace("_", " ").split() if p]
    if len(parts) == 1:
        return parts[0][:3]
    return "".join(p[0] for p in parts)[:3]


def _safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name[:180]


def generate_visualizations(sources=None, label: str = "all", root_path: str | None = None, run_id: str | None = None):
    """
    Creates a global interactive HTML timeline and per-unit HTML timelines.
    Also writes a simple static PNG for the global timeline (no labels) as fallback.
    Returns the path to the GLOBAL HTML (which the GUI will auto-open).

    Zero-config:
    - If caller passes nothing, we still work (legacy outputs/ks_viz).
    - If caller passes root_path (and paths.ensure_run_dirs exists), we write to the run folder.
    """
    # Resolve where outputs go
    loc = _resolve_viz_dirs(root_path=root_path, run_id=run_id, label=label)

    events = _fetch_events_with_units()
    if sources:
        events = [e for e in events if e.get("source") in set(sources)]

    # Special handling for LOGS mode: split parsed vs unparsed
    logs_mode = (sources is not None and set(sources) == {"changelog"})
    if logs_mode:
        parsed = [e for e in events if e.get("parsed_ok")]
        unparsed = [e for e in events if not e.get("parsed_ok")]

        # ---------- GLOBAL (parsed only) ----------
        global_html = _write_global(parsed, loc, out_label=f"{label}", title_suffix="(logs)")
        _save_static_global_png(pd.DataFrame(parsed) if parsed else pd.DataFrame(columns=["ts","unit"]),
                                _unit_order(parsed), label, loc)

        # also write an audit view that includes unparsed (colored by parsed vs unparsed)
        _write_global(parsed + unparsed, loc, out_label=f"{label}_all",
                      title_suffix="(logs · parsed vs unparsed)",
                      color_by="parsed_ok", color_title="Parsed")

        # ---------- PER-UNIT (parsed only) ----------
        _write_per_unit(parsed, label, loc)

        _maybe_update_meta(loc, label, global_html)
        return global_html

    # Normal path (local or all sources)
    if not events:
        with open(loc["global_html"], "w", encoding="utf-8") as f:
            f.write("<html><body><h3>No events to visualize yet.</h3></body></html>")
        _maybe_update_meta(loc, label, loc["global_html"])
        return loc["global_html"]

    global_html = _write_global(events, loc, out_label=f"{label}", title_suffix=f"({label})")
    _save_static_global_png(pd.DataFrame(events), _unit_order(events), label, loc)
    _write_per_unit(events, label, loc)
    _maybe_update_meta(loc, label, global_html)
    return global_html


# ---------- Helpers to build charts ----------

def _unit_order(events: list) -> list:
    if not events:
        return []
    df = pd.DataFrame(events)
    return df["unit"].value_counts().index.tolist()

def _write_global(events: list, loc: dict, out_label: str, title_suffix: str = "",
                  color_by: str = "actor_tag", color_title: str = "Actor"):
    global_html = os.path.join(os.path.dirname(loc["global_html"]), f"global_timeline_{out_label}.html")
    if not events:
        with open(global_html, "w", encoding="utf-8") as f:
            f.write("<html><body><h3>No events to visualize yet.</h3></body></html>")
        return global_html

    df = pd.DataFrame(events)
    unit_order = df["unit"].value_counts().index.tolist()
    df["unit"] = pd.Categorical(df["unit"], categories=unit_order, ordered=True)

    height = max(600, min(2400, 20 * max(1, len(unit_order))))
    hover_map = {
        "unit": True,
        "actor": True,
        "source": True,
        "summary": True,
        "ts": "|%Y-%m-%d %H:%M:%S",
        "actor_tag": False,
        "parsed_ok": False,
    }

    fig = px.scatter(
        df,
        x="ts",
        y="unit",
        color=color_by,
        hover_data=hover_map,
        title=f"Knowledge Space: Global Timeline of Edits {title_suffix}",
        height=height
    )
    fig.update_traces(marker=dict(size=7))
    fig.update_yaxes(automargin=True)
    fig.update_layout(legend_title_text=color_title, hovermode="closest")
    fig.write_html(global_html, include_plotlyjs="cdn")
    return global_html

def _write_per_unit(events: list, label: str, loc: dict):
    by_unit = defaultdict(list)
    for rec in events:
        by_unit[rec["unit"]].append(rec)

    units_out = loc["units_dir"]  # already run-/label-scoped by _resolve_viz_dirs

    for unit, evs in by_unit.items():
        dfu = pd.DataFrame(sorted(evs, key=lambda r: r["ts"]))
        h = max(320, 40 * max(1, len(dfu)))
        f2 = px.scatter(
            dfu,
            x="ts",
            y=[unit] * len(dfu),  # single line
            color="actor_tag",
            hover_data={
                "unit": True,
                "actor": True,
                "source": True,
                "summary": True,
                "ts": "|%Y-%m-%d %H:%M:%S",
                "actor_tag": False,
                "parsed_ok": False,
            },
            title=f"Timeline: {unit} ({label})",
            height=h
        )
        f2.update_traces(marker=dict(size=9))
        f2.update_yaxes(visible=False)
        f2.update_layout(showlegend=True, hovermode="closest")

        out_unit_html = os.path.join(units_out, _safe_filename(unit) + ".html")
        f2.write_html(out_unit_html, include_plotlyjs="cdn")

        # Optional static PNG
        _save_static_unit_png(unit, dfu, label, loc)


# ---------- Static (PNG) helpers ----------

def _save_static_global_png(df: pd.DataFrame, unit_order: list, label: str, loc: dict):
    xs = df["ts"].tolist() if not df.empty else []
    y_map = {u: i for i, u in enumerate(unit_order)}
    ys = [y_map.get(u, 0) for u in (df["unit"].tolist() if not df.empty else [])]

    plt.figure(figsize=(18, max(6, min(20, len(unit_order) * 0.25)) if unit_order else 6))
    if xs:
        plt.scatter(xs, ys, s=8)
        plt.yticks(range(len(unit_order)), unit_order, fontsize=7)
    else:
        plt.yticks([])
    plt.xlabel("Time")
    plt.ylabel("Unit (file/folder)")
    plt.title(f"Knowledge Space: Global Timeline of Edits (static preview · {label})")
    plt.tight_layout()
    path = os.path.join(os.path.dirname(loc["global_png"]), f"global_timeline_{label}.png")
    plt.savefig(path, dpi=200)
    plt.close()


def _save_static_unit_png(unit: str, dfu: pd.DataFrame, label: str, loc: dict):
    xs = dfu["ts"].tolist() if not dfu.empty else []
    ys = [1] * len(xs)
    plt.figure(figsize=(12, 2.4))
    if xs:
        plt.plot(xs, ys, marker="o", linestyle="-", linewidth=1)
    plt.yticks([])
    plt.xlabel("Time")
    plt.title(f"Timeline: {unit} ({label})")
    plt.tight_layout()
    out_unit = os.path.join(loc["units_dir"], _safe_filename(unit) + ".png")
    plt.savefig(out_unit, dpi=160)
    plt.close()


def _maybe_update_meta(loc: dict, label: str, global_html: str):
    """
    If we're in a run-scoped directory (meta_path present), append viz info to meta.json.
    """
    meta_path = loc.get("meta_path")
    if not meta_path:
        return
    try:
        meta = json.load(open(meta_path, "r", encoding="utf-8"))
    except Exception:
        meta = {}
    meta["visualizations"] = {
        "label": label,
        "html": global_html
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
