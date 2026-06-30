import fitz
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def _sample_pdf_bytes() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "Smart Investment Assistant Demo Report",
                "Fiscal Year 2025",
                "Revenue: $1,250,000",
                "Net Profit: $310,000",
                "Cash and equivalents: $90,000",
                "Total assets: $2,400,000",
            ]
        ),
    )
    return pdf.tobytes()


def test_full_api_flow(tmp_path):
    settings = get_settings()
    settings.storage_dir = tmp_path / "data"
    settings.upload_dir = tmp_path / "uploads"
    settings.extracted_assets_dir = tmp_path / "assets"

    client = TestClient(app)

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "text/html" in root_response.headers["content-type"]
    assert "Smart Investment Assistant" in root_response.text

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ok"

    ui_testing_response = client.get("/ui-testing")
    assert ui_testing_response.status_code == 200
    assert "text/html" in ui_testing_response.headers["content-type"]

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "healthy"

    upload_response = client.post(
        "/api/reports",
        files={"file": ("demo-report.pdf", _sample_pdf_bytes(), "application/pdf")},
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    assert uploaded["pages"] == 1
    assert uploaded["text_blocks"] == 1
    assert uploaded["report_id"]

    list_response = client.get("/api/reports")
    assert list_response.status_code == 200
    assert any(report["report_id"] == uploaded["report_id"] for report in list_response.json())

    detail_response = client.get(f"/api/reports/{uploaded['report_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert "Revenue" in detail["text_preview"]
    assert "detected_numbers" in detail["metrics"]

    query_response = client.post(
        "/api/query",
        json={"report_id": uploaded["report_id"], "question": "What was the revenue?"},
    )
    assert query_response.status_code == 200
    answer = query_response.json()
    assert "$1,250,000" in answer["answer"]
    assert answer["sources"]

    missing_response = client.get("/api/reports/not-found")
    assert missing_response.status_code == 404

    invalid_upload_response = client.post(
        "/api/reports",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert invalid_upload_response.status_code == 415

