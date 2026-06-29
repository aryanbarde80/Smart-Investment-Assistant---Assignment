from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExtractedTable(BaseModel):
    page: int
    rows: list[list[str]]


class ExtractedImage(BaseModel):
    page: int
    image_index: int
    filename: str
    width: int | None = None
    height: int | None = None
    ocr_text: str | None = None
    structured_text: str | None = None


class ReportSummary(BaseModel):
    report_id: str
    filename: str
    uploaded_at: datetime
    pages: int
    text_blocks: int
    tables: int
    images: int
    numeric_warnings: list[str] = Field(default_factory=list)


class ReportDetail(ReportSummary):
    text_preview: str
    tables_preview: list[ExtractedTable]
    images_preview: list[ExtractedImage]
    metrics: dict[str, Any]


class QueryRequest(BaseModel):
    report_id: str = Field(..., description="Report id returned by the upload endpoint.")
    question: str = Field(..., min_length=3, max_length=500)


class QueryResponse(BaseModel):
    report_id: str
    question: str
    answer: str
    confidence: str
    sources: list[str]

