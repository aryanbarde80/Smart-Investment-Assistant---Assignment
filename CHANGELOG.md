# Changelog

All notable changes to Smart Investment Assistant are documented here.

---

## [Unreleased]

- Production-grade storage (Postgres + S3) to replace ephemeral local JSON files
- Per-user authentication and report scoping
- Batch PDF ingestion endpoint
- Streaming LLM responses via Server-Sent Events

---

## [1.3.0] — 2026-07-01

### Added
- **DeepSeek LLM synthesis layer** (`services/llm.py`) — when `SIA_DEEPSEEK_API_KEY` is set, retrieved chunks are passed to `deepseek-chat` for a clean, cited natural-language answer
- `SIA_DEEPSEEK_API_KEY` setting in `config.py` with graceful fallback: if the key is absent or the API call fails, the system returns the keyword-retrieval answer unchanged
- `httpx` pinned in `requirements.txt` for the DeepSeek HTTP client

### Changed
- `services/qa.py` refactored into a two-stage pipeline: retrieval → optional LLM synthesis
- `_metric_answer()` now returns matched chunks alongside the formatted answer so they can be passed directly to the LLM as numbered context

---

## [1.2.0] — 2026-06-30

### Added
- **`/ui-testing` API console** (`templates/ui_testing.html`) — interactive browser-based endpoint tester with prefilled examples, drag-and-drop PDF upload, syntax-highlighted JSON responses, flow stepper, and cURL snippet tab
- `/api/status` endpoint returning JSON service name and status
- `GET /api/status` added to API console sidebar
- Quick Actions panel in console fires `/health` and `/api/status` and renders results inline (replaced browser `alert()`)
- Content-type-aware response parsing — HTML responses no longer crash with `Unexpected token '<'`

### Fixed
- API console `runRequest()` now checks `Content-Type` before calling `.json()`, falling back to a truncated HTML preview for non-JSON routes

---

## [1.1.0] — 2026-06-30

### Added
- **Dashboard UI** (`/`, `templates/index.html`) — upload, browse extracted text/tables/chart OCR, ask questions, all from the browser
- Cross-page navigation bar linking Dashboard, API Console, and Swagger docs
- Custom Swagger UI (`/docs`) wrapped with the nav bar
- `GET /api/status` JSON health check (separate from `GET /health`)
- `UnreadablePdfError` in `extractor.py` — corrupted PDFs now return HTTP 422 instead of a 500
- Synthetic sample report `docs/sample-report/aurora-capital-fy2025.pdf` for end-to-end demos
- `docs/ARCHITECTURE.md` — full design write-up, tool rationale, system diagram, request flow

### Changed
- `GET /` changed from a JSON health response to the HTML dashboard
- Test suite updated: covers `/ui-testing`, `/docs`, `/api/status`, corrupted PDF upload (422), and missing-report query (404)

---

## [1.0.0] — 2026-06-29

### Added
- FastAPI backend with four REST endpoints: `POST /api/reports`, `GET /api/reports`, `GET /api/reports/{id}`, `POST /api/query`
- `services/extractor.py` — PDF text extraction (PyMuPDF), table extraction (pdfplumber), chart OCR (pytesseract + Pillow), numeric warning detection
- `services/qa.py` — two-path keyword Q&A: metric-alias fast path + scored full-text fallback
- `services/security.py` — content-type, magic-byte, size, and filename validation
- `storage.py` — JSON file store persisting one file per report under `data/`
- `config.py` — environment-driven settings with `SIA_` prefix via pydantic-settings
- `vercel.json` + `api/index.py` for Vercel Python serverless deployment
- End-to-end pytest suite
- `docs/SWAGGER_DEMO.md` + screenshots as submission evidence
