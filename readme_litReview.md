# Ailys: Literature Processing Component

## Overview
The literature processing component of Ailys automates the extraction of structured information from academic manuscripts (PDFs) into formats ready for analysis and integration into research workflows. This system was designed for researchers conducting systematic reviews, meta-analyses, and literature syntheses, with an emphasis on structured output and reproducibility.

---

## Key Functions
1. **Single-PDF Review**
   - Select a PDF in the GUI.
   - Provide optional guidance text (instructions for extraction focus).
   - Ailys parses the PDF, extracts text, and applies structured analysis powered by GPT models.
   - Output is written to a spreadsheet (Excel `.xlsx` format).

2. **Batch Review**
   - Select a folder of PDFs.
   - Ailys processes each file sequentially.
   - Shared or file-specific guidance can be applied.
   - Outputs are aggregated into a single spreadsheet file for easier integration.

3. **Memory Integration**
   - Each review result is saved into Ailys’ crystallized memory system.
   - This ensures reviews contribute to the assistant’s long-term knowledge and can be recalled in future tasks.

4. **Structured Output**
   Each reviewed article is represented in a consistent, spreadsheet-ready row with the following fields:
   - **Source** – How the paper was located (keywords, search method).
   - **Citation** – Full APA-style reference.
   - **Abstract** – Verbatim abstract.
   - **Brief Summary** – Concise 4–6 sentence summary of findings, methods, and contributions.
   - **Expanded Notes** – 30–50 key quotes, formatted with bolded key terms and page numbers.
   - **Research Questions** – Explicit or inferred RQs.
   - **Hypotheses** – Directly stated hypotheses.
   - **Referenced Works to Review** – Citations of other works relevant to the review topic.
   - **Keywords** – List of article keywords.
   - **Type of Publication** – Empirical, theoretical, review, etc.

---

## Workflow Details

### Step 1: PDF Selection
The user selects a PDF from the GUI. Ailys uses its `pdf_reader.py` module to safely extract text while preserving readability for GPT-powered extraction.

### Step 2: Guidance Input
Optional user-provided instructions can emphasize aspects such as:
- Extracting only team cognition results.
- Highlighting AI-related findings.
- Prioritizing certain theories or methods.

### Step 3: Review Execution
The review task (`tasks/literature_review.py`) runs the following steps:
- Text extraction from the PDF.
- Chunking text into manageable sections if needed.
- Prompt construction with structured extraction fields.
- API call to GPT with approval queue handling if enabled.

### Step 4: Spreadsheet Output
Results are written into an `.xlsx` file with one row per paper. Columns are structured exactly as required for integration into systematic review spreadsheets.

### Step 5: Memory Storage
Each review is also stored as a crystallized memory entry. Metadata such as file path, extracted text, and AI insights are preserved.

### Step 6: Batch Mode
In batch review, the process repeats across all PDFs in a selected folder. Results are aggregated into a single Excel file, and all reviews are stored in memory.

---

## Outputs
1. **Excel Spreadsheets** – Primary structured review outputs.
2. **Memory Entries (SQLite + Snapshots)** – Long-term persistence for recall and cross-task use.
3. **Chat Integration** – Users can query Ailys about previously reviewed papers using the memory system.

---

## Example Use Cases
- Building a systematic literature review database for a dissertation or grant proposal.
- Extracting hypotheses and RQs from a set of domain-specific papers.
- Creating a citation-linked spreadsheet of all papers reviewed for meta-analysis.
- Maintaining a growing memory of reviewed literature across multiple projects.

---

## Integration with Knowledge Space
While literature review outputs are primarily research-focused, they also feed into the broader Knowledge Space Management (KSM) pipeline:
- Memory events ensure literature reviews contribute to the same cumulative knowledge system.
- Structured exports allow comparison between “knowledge produced by teams” (KSM) and “knowledge referenced by researchers” (literature).

---

## Future Extensions
- Automated duplicate detection across reviewed PDFs.
- Enhanced PDF parsing for scanned/poor-quality documents (OCR integration).
- NLP/ML analysis of extracted abstracts and summaries (topic modeling, clustering).
- Integration with bibliographic tools (Zotero, Mendeley).

---

## Conclusion
The literature processing component transforms raw PDFs into highly structured, analyzable entries. It reduces manual effort in systematic reviews, ensures consistency in outputs, and integrates into Ailys’ memory and knowledge space pipelines, making it a cornerstone of the system’s research-support capabilities.
