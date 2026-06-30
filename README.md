# Smart Investment Assistant

FastAPI backend for extracting structured financial data from PDF reports and answering report-grounded questions.

## Features

- Upload PDF financial reports through a REST API.
- Extract page text with PyMuPDF.
- Extract tabular data with `pdfplumber` while preserving row and cell structure.
- Extract embedded report images and optionally OCR chart images when `pytesseract` is available.
- Detect numeric values and flag suspicious table values for manual verification.
- Ask questions against the uploaded report content using deterministic retrieval over text, tables, and chart OCR.
- Store extracted report data locally as JSON for simple integration and demos.
- Includes `vercel.json` and `api/index.py` for Vercel Python deployment.

## Web Interface

- `GET /` — primary dashboard. Upload a PDF report, browse extracted text/tables/chart OCR, review flagged numeric values, and ask grounded questions, all from the browser.
- `GET /ui-testing` — a separate developer console for exercising each API endpoint directly (raw request/response, useful for debugging and demos).
- `GET /docs` — auto-generated Swagger UI.

## Project Structure

```text
app/
  main.py                 FastAPI app and routes
  config.py               Environment-driven settings
  schemas.py              Pydantic response/request models
  storage.py              JSON report store
  services/
    extractor.py          PDF text, table, image, OCR extraction
    qa.py                 Report-grounded question answering
    security.py           Upload validation and filename safety
api/index.py              Vercel entrypoint
vercel.json               Vercel deployment config
requirements.txt          Python dependencies
```

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

## Run Tests

```bash
pytest
```

## API Endpoints

### `GET /`

Dashboard UI (HTML). Upload reports, browse extracted data, ask questions.

### `GET /api/status`

JSON health/status check.

### `GET /ui-testing`

Developer API console (HTML) for manually exercising every endpoint.

### `POST /api/reports`

Uploads and processes a PDF report.

Form-data:

- `file`: PDF file

Returns:

- `report_id`
- filename
- page count
- counts of extracted text blocks, tables, and images
- numeric warnings

### `GET /api/reports`

Lists processed reports.

### `GET /api/reports/{report_id}`

Returns a detailed report preview including extracted text preview, tables, image OCR preview, and detected metrics.

### `POST /api/query`

Asks a question about an uploaded report.

Request:

```json
{
  "report_id": "generated-report-id",
  "question": "What was the revenue?"
}
```

Returns:

- answer
- confidence
- source references such as page/table/image

## Security and Data Handling

- Accepts only PDFs by content type and PDF signature.
- Enforces an upload size limit with `SIA_MAX_UPLOAD_MB`.
- Sanitizes uploaded filenames.
- Does not call external AI APIs by default, keeping financial data local.
- Stores extracted data in local JSON files under `data/`.
- For production, replace local JSON storage with a managed database and object storage.

## Environment Variables

All settings are optional and use the `SIA_` prefix.

```text
SIA_MAX_UPLOAD_MB=25
SIA_STORAGE_DIR=data
SIA_UPLOAD_DIR=uploads
SIA_EXTRACTED_ASSETS_DIR=extracted_assets
```

## Vercel Deployment

This repository includes:

- `vercel.json`
- `api/index.py`

Deploy with:

```bash
vercel --prod
```

Note: Vercel serverless storage is ephemeral. For production persistence, connect the app to a hosted database and cloud object storage.

## Demo Flow

1. Start the server with `uvicorn app.main:app --reload`.
2. Open Swagger UI at `/docs`.
3. Use `POST /api/reports` to upload the sample PDF.
4. Copy the returned `report_id`.
5. Use `POST /api/query` with questions like:
   - `What is the revenue mentioned in the report?`
   - `Summarize the profit figures.`
   - `Which tables contain cash or assets?`

Swagger screenshot evidence and live endpoint test results are documented in [`docs/SWAGGER_DEMO.md`](docs/SWAGGER_DEMO.md).

## Accuracy Notes

Financial extraction accuracy depends on PDF quality:

- Native PDFs generally extract cleanly.
- Scanned PDFs require OCR.
- Embedded chart OCR requires local `pytesseract` and a Tesseract binary installed on the host.
- Numeric warnings help identify values that should be manually checked before investment decisions.
