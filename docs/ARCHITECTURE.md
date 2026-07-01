# Architecture & Design Decisions

> Smart Investment Assistant — technical write-up for the assignment submission.

---

## 1. Problem statement

Build a system that accepts a PDF financial report, extracts its content accurately (narrative text, tables, embedded charts/images), exposes that content via a FastAPI REST API, and answers natural-language questions that are grounded strictly in the uploaded document.

---

## 2. Approach

The system is split into four clearly separated stages:

| Stage | Module | Concern |
|---|---|---|
| **Extraction** | `services/extractor.py` | Parse PDF → structured data |
| **Storage** | `storage.py` | Persist extracted data per report |
| **Q&A** | `services/qa.py` + `services/llm.py` | Retrieve relevant chunks → synthesise answer |
| **API + UI** | `main.py` + `templates/` | Expose everything over HTTP |

Each stage is isolated so it can be tested, replaced, or upgraded independently — e.g., swapping the JSON file store for Postgres, or upgrading the keyword retriever, without touching extraction or routing.

---

## 3. Tool choices

| Concern | Tool | Reason |
|---|---|---|
| Web framework | **FastAPI** | Async-ready, automatic OpenAPI/Swagger, Pydantic type safety — directly matches the assignment requirement |
| PDF text extraction | **PyMuPDF (`fitz`)** | Fast, accurate page-level text; direct access to embedded images for chart OCR |
| Table extraction | **pdfplumber** | Purpose-built for ruled table extraction as row/column data — critical for numeric accuracy |
| Chart OCR | **Pillow + pytesseract** | Converts embedded chart/figure images to text; structured into bullet-point + detected-numbers form |
| Validation/schemas | **Pydantic v2** | Self-documenting, type-safe request/response contracts |
| Storage | **JSON file store** | Zero external dependencies for an assignment/demo; single module to swap for a real DB in production |
| LLM synthesis | **DeepSeek (`deepseek-chat`)** | OpenAI-compatible endpoint — no extra SDK; called via plain `httpx`. Optional: the system works without it |
| HTTP client | **httpx** | Synchronous client for DeepSeek API calls; already a transitive FastAPI dependency |
| Testing | **pytest + FastAPI TestClient** | Full end-to-end test: upload → list → detail → Q&A → 4xx/5xx error paths |

---

## 4. System architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI app                          │
│                         main.py                             │
└────┬──────────────────────┬───────────────────┬─────────────┘
     │                      │                   │
     ▼                      ▼                   ▼
┌─────────┐       ┌──────────────────┐   ┌─────────────────┐
│  UI     │       │  Report routes   │   │  Q&A route      │
│  /      │       │  POST /api/reports│   │  POST /api/query│
│  /ui-   │       │  GET  /api/reports│   └────────┬────────┘
│ testing │       │  GET  /api/reports│            │
│  /docs  │       │        /{id}      │            │
└─────────┘       └────────┬─────────┘            │
                           │                       │
                  ┌────────▼──────────┐   ┌────────▼────────────┐
                  │ security.py       │   │ qa.py               │
                  │ · content-type    │   │ · metric alias match │
                  │ · %PDF signature  │   │ · keyword scoring    │
                  │ · size limit      │   │ · top-k chunk select │
                  │ · filename safety │   └────────┬────────────┘
                  └────────┬──────────┘            │
                           │                       ▼
                  ┌────────▼──────────┐   ┌────────────────────┐
                  │ extractor.py      │   │ llm.py             │
                  │ · PyMuPDF: text + │   │ · DeepSeek API     │
                  │   embedded images │   │ · context = chunks │
                  │ · pdfplumber:     │   │ · graceful fallback │
                  │   ruled tables    │   │   if key absent    │
                  │ · pytesseract:    │   └────────────────────┘
                  │   chart OCR       │
                  │ · numeric warnings│
                  └────────┬──────────┘
                           │
                  ┌────────▼──────────────────────────────────┐
                  │            storage.JsonReportStore         │
                  │  data/<report_id>.json                     │
                  │  (text_blocks, tables, images, metrics,    │
                  │   numeric_warnings, uploaded_at …)         │
                  └────────────────────────────────────────────┘
```

---

## 5. Q&A pipeline in detail

The question-answering pipeline is intentionally two-stage so the retrieval result is always available as a fallback, and the LLM layer adds value without creating a hard dependency:

```
User question
      │
      ├─── metric alias check ──► known metric? (revenue, EBITDA, EPS…)
      │         yes → collect matching text/table/OCR chunks
      │          no → keyword tokenise + score every chunk → top-k
      │
      ▼
 Retrieved chunks  { source, text }[]
      │
      ├── SIA_DEEPSEEK_API_KEY set?
      │         no  → return retrieval answer directly
      │         yes ↓
      ▼
 DeepSeek deepseek-chat
      · system prompt: "answer using ONLY the numbered context excerpts"
      · user prompt:   numbered chunks + question
      · temperature:   0.2  (low, for factual consistency)
      · max_tokens:    512
      │
      ├── API call succeeds → return LLM answer  { confidence: "high" }
      └── API call fails    → silent fallback to retrieval answer
```

This design means:
- The API never breaks because the LLM is unavailable
- Retrieval-only answers are still useful and source-attributed
- LLM answers are strictly grounded — the model only sees extracted chunks, not its own training knowledge

---

## 6. Security model

| Control | Implementation |
|---|---|
| File type | `Content-Type: application/pdf` **and** `%PDF` magic-byte check |
| File size | Configurable via `SIA_MAX_UPLOAD_MB` (default 25 MB) |
| Filename | `safe_filename()` strips path separators, null bytes, non-pdf extensions |
| LLM data boundary | DeepSeek receives only extracted text chunks — never the raw PDF bytes |
| No auth (by design) | Single-user demo/assignment scope; noted as a production gap below |

---

## 7. Request flows

### Upload flow

```
POST /api/reports  (multipart/form-data, file=<PDF>)
  │
  ├─ validate_pdf_upload()   content-type + size + %PDF signature
  ├─ extract_financial_report()
  │     ├─ PyMuPDF  → text_blocks[], images[]
  │     ├─ pdfplumber → tables[]
  │     ├─ pytesseract (if available) → OCR text per image
  │     └─ numeric_warnings[] → flag suspicious table numbers
  ├─ JsonReportStore.save()  → data/<report_id>.json
  └─ return ReportSummary
```

### Query flow

```
POST /api/query  { report_id, question }
  │
  ├─ JsonReportStore.get(report_id)
  ├─ qa.answer_question()
  │     ├─ _metric_answer()  → exact metric match? → chunks
  │     └─ keyword scoring   → top-k chunks
  ├─ llm.ask_llm()           → DeepSeek synthesis (if key set)
  └─ return QueryResponse { answer, confidence, sources }
```

---

## 8. Known limitations

| Limitation | Notes |
|---|---|
| No authentication | All reports are visible to all callers. For production: add JWT/API-key auth and per-user report scoping. |
| Ephemeral storage on Vercel | Serverless functions have no persistent disk. For production: swap `storage.py` for Postgres + S3. |
| Scanned PDFs | Text extraction requires OCR (pytesseract + Tesseract binary). Works locally if installed; skipped on Vercel. |
| Single-file upload | One PDF per request. Batch ingestion is a natural extension. |
| LLM context window | Very long reports may exceed DeepSeek's context limit; chunk truncation at 700 chars mitigates this. |

---

## 9. Sample report

`docs/sample-report/aurora-capital-fy2025.pdf` is a synthetic two-page financial report with:
- One page of narrative summary text
- A ruled income statement table (Revenue, Gross Profit, EBITDA, Net Income, EPS)
- A ruled balance sheet table (Assets, Liabilities, Equity)

It is designed to exercise text extraction, table extraction, metric-alias Q&A, and DeepSeek synthesis end-to-end.
