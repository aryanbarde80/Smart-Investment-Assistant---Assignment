import io
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pdfplumber
from PIL import Image

from app.services.security import safe_filename

NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\(?\$?\d[\d,]*(?:\.\d+)?%?\)?")


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _extract_numbers(text: str) -> list[str]:
    return [match.group(0) for match in NUMBER_RE.finditer(text)]


def _numeric_warnings(tables: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for table_index, table in enumerate(tables, start=1):
        for row_index, row in enumerate(table["rows"], start=1):
            joined = " | ".join(row)
            for value in _extract_numbers(joined):
                digits = re.sub(r"[^0-9]", "", value)
                if len(digits) >= 4 and "," not in value and "." not in value:
                    warnings.append(
                        f"Table {table_index}, row {row_index}: verify large ungrouped number '{value}'."
                    )
    return warnings[:50]


def _ocr_image(image: Image.Image) -> str | None:
    try:
        import pytesseract  # type: ignore
    except Exception:
        return None

    try:
        return pytesseract.image_to_string(image).strip() or None
    except Exception:
        return None


def _structure_chart_text(ocr_text: str | None) -> str | None:
    if not ocr_text:
        return None
    lines = [re.sub(r"\s+", " ", line).strip() for line in ocr_text.splitlines() if line.strip()]
    numbers = _extract_numbers(" ".join(lines))
    if not lines:
        return None
    parts = ["Chart/Image OCR:"]
    parts.extend(f"- {line}" for line in lines[:12])
    if numbers:
        parts.append(f"Detected numeric values: {', '.join(numbers[:25])}")
    return "\n".join(parts)


def extract_financial_report(
    pdf_bytes: bytes,
    original_filename: str | None,
    upload_dir: Path,
    assets_dir: Path,
) -> dict[str, Any]:
    report_id = uuid.uuid4().hex
    filename = safe_filename(original_filename)
    upload_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = upload_dir / f"{report_id}_{filename}"
    pdf_path.write_bytes(pdf_bytes)

    text_blocks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            text_blocks.append({"page": page_index, "text": text})

        for image_index, image_info in enumerate(page.get_images(full=True), start=1):
            xref = image_info[0]
            extracted = doc.extract_image(xref)
            image_bytes = extracted.get("image")
            ext = extracted.get("ext", "png")
            if not image_bytes:
                continue
            image_name = f"{report_id}_page{page_index}_image{image_index}.{ext}"
            image_path = assets_dir / image_name
            image_path.write_bytes(image_bytes)
            pil_image = Image.open(io.BytesIO(image_bytes))
            ocr_text = _ocr_image(pil_image)
            images.append(
                {
                    "page": page_index,
                    "image_index": image_index,
                    "filename": image_name,
                    "width": pil_image.width,
                    "height": pil_image.height,
                    "ocr_text": ocr_text,
                    "structured_text": _structure_chart_text(ocr_text),
                }
            )

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            for raw_table in page.extract_tables() or []:
                rows = [[_clean_cell(cell) for cell in row] for row in raw_table if row]
                rows = [row for row in rows if any(cell for cell in row)]
                if rows:
                    tables.append({"page": page_index, "rows": rows})

    all_text = "\n\n".join(block["text"] for block in text_blocks)
    all_text += "\n\n" + "\n\n".join(image.get("structured_text") or "" for image in images)
    metrics = {
        "detected_numbers": _extract_numbers(all_text)[:200],
        "table_count": len(tables),
        "image_count": len(images),
        "has_chart_ocr": any(image.get("ocr_text") for image in images),
    }

    return {
        "report_id": report_id,
        "filename": filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "pages": doc.page_count,
        "text_blocks": text_blocks,
        "tables": tables,
        "images": images,
        "metrics": metrics,
        "numeric_warnings": _numeric_warnings(tables),
    }

