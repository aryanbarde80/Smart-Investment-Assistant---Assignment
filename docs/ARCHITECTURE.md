# Approach, Tools & Architecture

This document is the brief explanation of approach, tools, and architecture
requested as a deliverable for the Smart Investment Assistant assignment.

## 1. Problem

Build a system that takes a PDF financial report, extracts its content
(narrative text, tables, and charts/images) accurately, exposes that content
through a FastAPI backend, and lets a user ask natural-language questions
that are answered using only the extracted report content.

## 2. Approach

The system is split into four stages that mirror the assignment's
requirements:

1. **Extraction** — pull structured data out of an uploaded PDF.
2. **Storage** — persist the extracted result so it can be queried later
   without re-parsing the PDF.
3. **Question answering** — retrieve the most relevant extracted content for
   a user's question and return it as a grounded answer.
4. **API + UI** — expose the above through a documented REST API and two
   user interfaces (an end-user dashboard and a developer API console).

Each stage is implemented as an isolated module so it can be tested,
replaced, or upgraded independently — for example, swapping the JSON file
store for a real database, or swapping the keyword-based QA for an LLM call,
without touching extraction or the API layer.

## 3. Tools

| Concern | Tool | Why |
|---|---|---|
| Web framework | FastAPI | Async-ready, automatic OpenAPI/Swagger docs, strong typing via Pydantic — matches the "mandatory FastAPI backend" requirement directly. |
| PDF text extraction | PyMuPDF (`fitz`) | Fast, accurate page-level text extraction and gives direct access to embedded images for chart OCR. |
| Table extraction | pdfplumber | Purpose-built for extracting ruled/structured tables from PDFs as row/column data, which is what's needed for numeric accuracy. |
| Chart/image-to-text | Pillow + pytesseract (Tesseract OCR) | Converts embedded chart/figure images into OCR text, which is then structured into bullet-point + detected-numbers form. |
| Validation/schemas | Pydantic | Defines request/response contracts (`schemas.py`) so the API is self-documenting and type-safe. |
| Storage | Local JSON file store (`storage.py`) | Simple, dependency-free persistence appropriate for an assignment/demo; designed to be swapped for Postgres/SQLite/object storage in production (see README). |
| Testing | pytest + FastAPI `TestClient` | End-to-end test exercises the full upload → list → detail → query → error-handling flow against an in-memory server. |

## 4. Architecture

```
                         ┌─────────────────────────────┐
                         │        FastAPI app          │
                         │         (main.py)           │
                         └──────────────┬───────────────┘
                                        │
       ┌────────────────────────────────┼────────────────────────────────┐
       │                                │                                │
┌──────▼───────┐               ┌────────▼────────┐               ┌───────▼──────┐
│ GET /         │               │ POST /api/reports│               │ POST /api/query│
│ HTML dashboard│               │ GET  /api/reports │              │  (Q&A)        │
│ GET /ui-testing│              │ GET  /api/reports/id│            │               │
│ HTML console  │               └────────┬─────────┘               └───────┬──────┘
└───────────────┘                        │                                │
                                ┌─────────▼─────────┐             ┌────────▼────────┐
                                │ services/security  │             │ services/qa      │
                                │  - content-type     │             │  - chunk text,   │
                                │  - PDF signature    │             │    tables, OCR    │
                                │  - size limit       │             │  - score by      │
                                │  - filename safety  │             │    keyword match  │
                                └─────────┬─────────┘             │  - metric aliases  │
                                          │                        │    (revenue, EBITDA,│
                                ┌─────────▼─────────┐             │    EPS, etc.)       │
                                │ services/extractor  │             └────────┬────────┘
                                │  - PyMuPDF: text +  │                      │
                                │    embedded images  │                      │
                                │  - pdfplumber: tables│                      │
                                │  - pytesseract: OCR  │                      │
                                │    on chart images   │                      │
                                │  - regex: detect      │                      │
                                │    numbers, flag      │                      │
                                │    suspicious values  │                      │
                                └─────────┬─────────┘                      │
                                          │                                │
                                ┌─────────▼────────────────────────────────▼────┐
                                │              storage.JsonReportStore           │
                                │   data/<report_id>.json  (text, tables, images,│
                                │   metrics, numeric_warnings persisted per      │
                                │   report; uploaded PDFs and extracted chart    │
                                │   images kept alongside on disk)               │
                                └─────────────────────────────────────────────────┘
```

### Request flow: uploading a report

1. Browser/Postman sends a PDF to `POST /api/reports`.
2. `services/security.validate_pdf_upload` checks content-type, file size,
   and the `%PDF` magic-byte signature before anything else touches the
   file.
3. `services/extractor.extract_financial_report` opens the PDF twice — once
   with PyMuPDF (text + embedded images) and once with pdfplumber (ruled
   tables) — and merges the results into one report dict, including OCR'd
   chart text and a numeric-warning pass over every detected number.
4. The result is saved via `storage.JsonReportStore` and a summary is
   returned to the caller.

### Request flow: asking a question

1. `POST /api/query` looks up the stored report by `report_id`.
2. `services/qa.answer_question` first checks if the question matches a
   known financial metric (revenue, profit, EBITDA, EPS, assets,
   liabilities, cash) and if so returns the chunks of text/table/chart data
   that mention it.
3. If no metric matches, it falls back to scoring every extracted chunk
   (paragraphs, tables, chart OCR) against the question's keywords and
   returns the highest-scoring chunks as the answer, with their source
   (page/table/image) attached so the answer is traceable back to the
   document.

### Why two web UIs

- **`/`** is the end-user-facing dashboard: upload a report, browse what was
  extracted (text, tables, chart OCR, flagged numbers), and ask questions —
  this is what a non-technical reviewer would use to evaluate the project.
- **`/ui-testing`** is a separate developer console for exercising each raw
  API endpoint directly (request/response inspection), useful for debugging
  and for recording a focused API walkthrough.
- **`/docs`** is FastAPI's auto-generated Swagger UI, used for the
  Swagger-based demo evidence in `docs/SWAGGER_DEMO.md`.

## 5. Known limitations (intentionally out of scope for this assignment)

- Question answering is deterministic keyword/term retrieval, not an LLM —
  it's explainable and fully local (no external API calls, important for
  sensitive financial data), but won't handle questions requiring
  multi-step reasoning across the document. Swapping in an LLM call inside
  `services/qa.py` is the natural next step.
- No authentication/authorization or per-user multi-tenancy — every
  uploaded report is visible to every API caller. Fine for a local demo,
  not for production.
- Storage is local JSON files, not a database — chosen for zero external
  dependencies in a take-home assignment; `storage.py` is the single place
  to swap in Postgres/SQLite/S3 for production use.

## 6. Sample report used for demos

`docs/sample-report/aurora-capital-fy2025.pdf` is a synthetic two-page
financial report (narrative summary + a ruled income statement table + a
ruled balance sheet table) used to exercise text extraction, table
extraction, and metric-grounded Q&A end-to-end. It's referenced in the
Swagger demo evidence in `docs/SWAGGER_DEMO.md`.
