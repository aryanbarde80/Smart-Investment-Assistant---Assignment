from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import Settings


PDF_SIGNATURE = b"%PDF"


async def validate_pdf_upload(file: UploadFile, settings: Settings) -> bytes:
    content_type = (file.content_type or "").lower()
    if content_type not in settings.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported.",
        )

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"PDF exceeds {settings.max_upload_mb} MB limit.")
    if not content.startswith(PDF_SIGNATURE):
        raise HTTPException(status_code=400, detail="File does not look like a valid PDF.")
    return content


def safe_filename(filename: str | None) -> str:
    raw_name = filename or "report.pdf"
    name = Path(raw_name).name.replace("\x00", "")
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"

