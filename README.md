# Smart Investment Assistant

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://smart-investment-assistant-assignme.vercel.app/)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen?logo=pytest)](./tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A FastAPI backend that extracts structured financial data from PDF reports and answers natural-language questions grounded strictly in the uploaded document — with an optional DeepSeek LLM layer for richer answers.

**Live demo →** [smart-investment-assistant-assignme.vercel.app](https://smart-investment-assistant-assignme.vercel.app/)

---

## Features

- **PDF extraction** — page text (PyMuPDF), ruled tables (pdfplumber), embedded chart/figure OCR (pytesseract + Pillow)
- **Numeric validation** — flags suspicious large ungrouped numbers in tables for manual review
- **Two-stage Q&A** — deterministic keyword retrieval finds relevant chunks; optional DeepSeek LLM synthesises a clean, cited answer on top
- **Dashboard UI** (`/`) — upload, browse extracted text/tables/chart OCR, ask questions — all in the browser, no CLI needed
- **Developer API console** (`/ui-testing`) — fire every endpoint with prefilled examples, see live request/response with syntax-highlighted JSON
- **Swagger UI** (`/docs`) — auto-generated OpenAPI documentation
- **Vercel-ready** — `vercel.json` + `api/index.py` entrypoint included

---

## Live Interfaces

| Route | Purpose |
|---|---|
| [`/`](https://smart-investment-assistant-assignme.vercel.app/) | End-user dashboard — upload a report and ask questions |
| [`/ui-testing`](https://smart-investment-assistant-assignme.vercel.app/ui-testing) | Developer API console with prefilled examples |
| [`/docs`](https://smart-investment-assistant-assignme.vercel.app/docs) | Swagger / OpenAPI documentation |

---

## Project Structure

```text
app/
  main.py                 FastAPI app, routes, and nav
  config.py               Environment-driven settings (SIA_ prefix)
  schemas.py              Pydantic request/response models
  storage.py              JSON report store (swap for DB in production)
  services/
    extractor.py          PDF text, table, image, and OCR extraction
    qa.py                 Two-stage retrieval → LLM Q&A pipeline
    llm.py                DeepSeek API client (optional, graceful fallback)
    security.py           Upload validation and filename sanitisation
  templates/
    index.html            Dashboard UI
    ui_testing.html       API testing console
api/
  index.py                Vercel serverless entrypoint
docs/
  ARCHITECTURE.md         Design decisions, tool choices, system diagram
  SWAGGER_DEMO.md         Tested endpoint evidence with screenshots
  sample-report/
    aurora-capital-fy2025.pdf   Synthetic two-page report for demos
vercel.json               Vercel deployment config
requirements.txt          Python dependencies
tests/
  test_api_flow.py        End-to-end API test (upload → list → detail → query → errors)
```

---

## Local Setup

```bash
git clone https://github.com/aryanbarde80/Smart-Investment-Assistant---Assignment.git
cd Smart-Investment-Assistant---Assignment

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Run Tests

```bash
pytest
```

One test covers the full flow: upload → list → detail → Q&A → 404 → 415 (unsupported type) → 422 (corrupted PDF) → UI routes.

---

## Environment Variables

All variables are optional and use the `SIA_` prefix. Create a `.env` file in the project root:

```env
# Storage paths (defaults work for local dev)
SIA_MAX_UPLOAD_MB=25
SIA_STORAGE_DIR=data
SIA_UPLOAD_DIR=uploads
SIA_EXTRACTED_ASSETS_DIR=extracted_assets

# Optional: enable DeepSeek LLM for richer Q&A answers
# Without this key the system still works — it falls back to keyword retrieval
SIA_DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

On Vercel, add these under **Project → Settings → Environment Variables**.

---

## API Endpoints

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status` | JSON status and service name |
| `GET` | `/health` | JSON health check |

### Reports

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reports` | Upload and process a PDF report |
| `GET` | `/api/reports` | List all processed reports |
| `GET` | `/api/reports/{report_id}` | Full detail — text preview, tables, image OCR, metrics |

**Upload request** (`multipart/form-data`):
```
file: <PDF file>
```

**Upload response:**
```json
{
  "report_id": "abc123",
  "filename": "annual-report.pdf",
  "uploaded_at": "2025-06-30T12:00:00Z",
  "pages": 12,
  "text_blocks": 34,
  "tables": 5,
  "images": 3,
  "numeric_warnings": []
}
```

### Question Answering

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/query` | Ask a natural-language question about a report |

**Request:**
```json
{
  "report_id": "abc123",
  "question": "What was the EBITDA for FY2025?"
}
```

**Response:**
```json
{
  "report_id": "abc123",
  "question": "What was the EBITDA for FY2025?",
  "answer": "Based on the income statement (Table 1, page 2), EBITDA for FY2025 was $4,200,000 ...",
  "confidence": "high",
  "sources": ["table 1, page 2", "page 1"]
}
```

---

## Q&A Pipeline

```
User question
      │
      ▼
 Keyword retrieval        ← always runs; finds relevant text/table/OCR chunks
      │
      ▼
 DeepSeek LLM synthesis   ← runs only if SIA_DEEPSEEK_API_KEY is set
      │   (model: deepseek-chat, context = retrieved chunks only)
      │   if API call fails → silent fallback to retrieval answer
      ▼
 Structured response  { answer, confidence, sources }
```

---

## Security

- Accepts only PDFs — validated by `Content-Type` header **and** `%PDF` magic-byte signature
- Enforces configurable upload size limit (`SIA_MAX_UPLOAD_MB`, default 25 MB)
- Sanitises uploaded filenames before writing to disk
- No external API calls by default — financial data stays local unless `SIA_DEEPSEEK_API_KEY` is set

---

## Deployment (Vercel)

```bash
vercel --prod
```

> **Note:** Vercel serverless storage is ephemeral — uploaded reports are lost between cold starts. For production persistence, connect to a managed database and cloud object storage and swap out `storage.py`.

---

## Architecture & Design Decisions

A full write-up of the approach, tool choices, and system architecture is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Demo Flow

1. Start the server — `uvicorn app.main:app --reload`
2. Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
3. Upload `docs/sample-report/aurora-capital-fy2025.pdf`
4. Browse extracted text, tables, and chart OCR in the workspace tabs
5. Ask questions like:
   - *"What was the total revenue?"*
   - *"What was the EBITDA?"*
   - *"Summarise the key financial metrics."*

Or use the API console at `/ui-testing` to fire raw requests and inspect responses.

---

## Swagger Evidence

Tested endpoint screenshots and live API results are recorded in [`docs/SWAGGER_DEMO.md`](docs/SWAGGER_DEMO.md).

---

## Accuracy Notes

- **Native PDFs** — text and tables extract cleanly
- **Scanned PDFs** — require Tesseract OCR installed on the host
- **Chart OCR** — requires `pytesseract` + a local Tesseract binary; gracefully skipped if unavailable
- **Numeric warnings** — flag large ungrouped numbers that should be manually verified before any investment decision
