# Swagger Demo and API Test Evidence

This document records the tested API flow for the Smart Investment Assistant backend.

## Test Date

June 29, 2026

## Environment

- Local API server: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Test report: generated one-page financial PDF with revenue, profit, EBITDA, cash, assets, and liabilities values.

## Swagger UI

The screenshot below shows the FastAPI-generated Swagger documentation with all exposed endpoints.

![Swagger endpoints](screenshots/01-swagger-endpoints.png)

## Tested API Flow

The following endpoints were tested one by one:

- `GET /`
- `GET /health`
- `POST /api/reports`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `POST /api/query`
- `POST /api/reports` with an invalid text file to verify upload validation

The screenshot below shows the captured test results from the same local server used by Swagger UI.

![Swagger tested results](screenshots/02-swagger-tested-results.png)

The machine-readable results are also available in [`swagger-test-results.json`](swagger-test-results.json).

## Result Summary

- Health endpoints returned `200`.
- PDF upload returned `200` with a generated `report_id`.
- Report listing returned the uploaded report.
- Report detail returned extracted text and detected numeric values.
- Query endpoint returned a grounded answer containing `$1,250,000` revenue and `$310,000` net profit.
- Invalid upload returned `415`, confirming file type validation.

## Reproduce

Start the API:

```bash
uvicorn app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Run automated API tests:

```bash
pytest
```

Generate fresh live API evidence while the server is running:

```bash
python scripts/run_live_api_demo.py
```

