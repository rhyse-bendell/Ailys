# Knowledge Space Management Pipeline

## Documentation for Review by Non-Technical Audiences

### Overview

The Knowledge Space Management (KSM) pipeline is a software system
designed to capture, organize, and analyze the evolving activity within
collaborative workspaces (what we call "knowledge spaces"). When teams
work together on shared documents, diagrams, notes, or other files, they
generate two layers of information: 1. Surface activity -- when files
are created, saved, or edited. 2. Embedded records of change -- logs or
text records created by tools that track edits, authors, and specific
modifications.

The KSM pipeline collects both of these, integrates them, and
produces: - A structured timeline of who changed what, when, and how. -
Visualizations that show the sequence of edits across documents or for
each document individually. - Exports that make the timeline and edits
available as structured data (CSV and JSON formats). - Metrics that
summarize how much each participant contributed and how activity
unfolded over time. - Narrative-ready summaries of how the knowledge
space developed (suitable for natural language analysis and reflection).

### Step 1: Knowledge Space Review

The system scans all files in a folder (and its subfolders). It looks
for two kinds of evidence of change: file system changes and embedded
change logs. Each change becomes an event record that includes: time of
the change, file/unit affected, source (file system vs. log), summary,
and actor identity if known.

### Step 2: Timeline Creation

The pipeline organizes events into a timeline: - Global timeline: all
edits across all files in chronological order. - Unit timelines: history
of each file individually. - Sessions: bursts of activity grouped by
gaps in time.

### Step 3: Visualization

The system produces interactive and static visualizations: - Global
timeline visualization: shows edits across all units over time, colored
by actor. - Per-unit timelines: history of each document individually. -
Static images: fallback for inclusion in reports.

### Step 4: Exports

The system generates structured exports: - JSONL: one event per line. -
Compiled JSON: includes global events, units, and sessions. - Compact
JSON: short summaries for language model use. - Prompt chunks: divided
JSON files for narrative generation.

### Step 5: Metrics Calculation

The system computes metrics for each actor: - Total edits, words added,
first/last activity, activity span, edits per minute. Results are
written to a CSV file for analysis in Excel, R, or Python.

### Step 6: Timeline CSV Export

The system produces a row-per-edit CSV containing time, actor, unit,
action, source, summary, and excerpt. This enables further analyses such
as sentiment or linguistic style analysis.

### Step 7: Narrative Generation (Optional)

The structured exports can be used with AI tools to produce narrative
descriptions of collaboration.

### Key Benefits

-   Transparency: every change captured and visible.
-   Traceability: who contributed what and when.
-   Reflection support: teams can review their own process.
-   Metrics: quantitative measures of collaboration.
-   Compatibility: exports are standard formats (CSV, JSON).
-   Narrative potential: structured logs can be turned into readable
    stories.

### In Practice

1.  Select a folder in the interface.
2.  The pipeline scans and collects changes.
3.  Outputs are written to a run-specific folder under outputs/ks_runs.
4.  Visualizations, exports, and metrics are immediately available.

### Conclusion

The KSM pipeline transforms raw traces of collaboration into coherent,
analyzable records of team activity. It provides transparency,
traceability, and metrics, while also enabling narrative reflection on
how a team worked together to build knowledge.
