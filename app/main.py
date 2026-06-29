from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.schemas import QueryRequest, QueryResponse, ReportDetail, ReportSummary
from app.services.extractor import extract_financial_report
from app.services.qa import answer_question
from app.services.security import validate_pdf_upload
from app.storage import JsonReportStore

app = FastAPI(
    title="Smart Investment Assistant",
    description="Extracts financial report data from PDFs and answers report-grounded questions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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


@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    return {"status": "ok", "service": "Smart Investment Assistant"}


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "healthy"}


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

