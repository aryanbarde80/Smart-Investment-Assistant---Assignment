from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.config import Settings, get_settings
from app.schemas import QueryRequest, QueryResponse, ReportDetail, ReportSummary
from app.services.extractor import extract_financial_report
from app.services.qa import answer_question
from app.services.security import validate_pdf_upload
from app.storage import JsonReportStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_NAV_HTML = """
<nav style="background:#16201B;border-bottom:1px solid #2e3347;padding:10px 32px;
  display:flex;gap:24px;font-size:12.5px;font-family:'IBM Plex Sans',Arial,sans-serif;">
  <a href="/" style="color:#9aa39c;text-decoration:none;">Dashboard</a>
  <a href="/ui-testing" style="color:#9aa39c;text-decoration:none;">API Console</a>
  <a href="/docs" style="color:#fff;font-weight:600;text-decoration:none;border-bottom:2px solid #1F6F54;padding-bottom:2px;">Swagger Docs</a>
</nav>
"""

app = FastAPI(
    title="Smart Investment Assistant",
    description="Extracts financial report data from PDFs and answers report-grounded questions.",
    version="1.0.0",
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui() -> HTMLResponse:
    """Swagger UI wrapped with a nav bar linking back to the dashboard and API console."""
    response = get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} - Swagger UI")
    body = response.body.decode("utf-8")
    body = body.replace("<body>", f"<body>{_NAV_HTML}", 1)
    return HTMLResponse(content=body)


def get_store(settings: Settings = Depends(get_settings)) -> JsonReportStore:
    return JsonReportStore(settings.storage_dir)


def _summary(report: dict) -> ReportSummary:
    return ReportSummary(
        report_id=report["report_id"],
        filename=report["filename"],
        uploaded_at=report["uploaded_at"],
        pages=report["pages"],
        text_blocks=len(report.get("text_blocks", [])),
        tables=len(report.get("tables", [])),
        images=len(report.get("images", [])),
        numeric_warnings=report.get("numeric_warnings", []),
    )


@app.get("/", tags=["UI"], response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Primary dashboard: upload reports, browse extracted data, ask questions."""
    html = (_TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/api/status", tags=["Health"])
def api_status() -> dict[str, str]:
    return {"status": "ok", "service": "Smart Investment Assistant"}


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ui-testing", tags=["Testing"], response_class=HTMLResponse)
def ui_testing() -> HTMLResponse:
    """Interactive browser-based API testing console."""
    html = (_TEMPLATES_DIR / "ui_testing.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/api/reports", response_model=ReportSummary, tags=["Reports"])
async def upload_report(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: JsonReportStore = Depends(get_store),
) -> ReportSummary:
    pdf_bytes = await validate_pdf_upload(file, settings)
    report = extract_financial_report(
        pdf_bytes=pdf_bytes,
        original_filename=file.filename,
        upload_dir=settings.upload_dir,
        assets_dir=settings.extracted_assets_dir,
    )
    store.save(report)
    return _summary(report)


@app.get("/api/reports", response_model=list[ReportSummary], tags=["Reports"])
def list_reports(store: JsonReportStore = Depends(get_store)) -> list[ReportSummary]:
    return [_summary(report) for report in store.list()]


@app.get("/api/reports/{report_id}", response_model=ReportDetail, tags=["Reports"])
def get_report(report_id: str, store: JsonReportStore = Depends(get_store)) -> ReportDetail:
    report = store.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    text_preview = "\n\n".join(block.get("text", "") for block in report.get("text_blocks", []))[:3000]
    return ReportDetail(
        **_summary(report).model_dump(),
        text_preview=text_preview,
        tables_preview=report.get("tables", [])[:5],
        images_preview=report.get("images", [])[:5],
        metrics=report.get("metrics", {}),
    )


@app.post("/api/query", response_model=QueryResponse, tags=["Question Answering"])
def query_report(payload: QueryRequest, store: JsonReportStore = Depends(get_store)) -> QueryResponse:
    report = store.get(payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    result = answer_question(report, payload.question)
    return QueryResponse(report_id=payload.report_id, question=payload.question, **result)

