import json
import mimetypes
import uuid
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

import fitz


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
DOCS_DIR = ROOT / "docs"


def make_demo_pdf() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            [
                "Smart Investment Assistant Demo Financial Report",
                "Fiscal Year 2025",
                "Revenue: $1,250,000",
                "Net Profit: $310,000",
                "EBITDA: $470,000",
                "Cash and equivalents: $90,000",
                "Total assets: $2,400,000",
                "Total liabilities: $860,000",
            ]
        ),
    )
    return pdf.tobytes()


def call_json(method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    req = request.Request(BASE_URL + path, data=body, headers=headers or {}, method=method)
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return {"status": response.status, "response": json.loads(payload)}
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return {"status": exc.code, "response": json.loads(payload)}


def multipart_file(field_name: str, filename: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----sia-{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'}\r\n\r\n"
            ).encode(),
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def call_html(method: str, path: str) -> dict:
    req = request.Request(BASE_URL + path, method=method)
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return {"status": response.status, "content_type": response.headers.get("content-type"), "length": len(payload)}
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return {"status": exc.code, "content_type": exc.headers.get("content-type"), "length": len(payload)}


def write_html(results: dict) -> None:
    rows = []
    for endpoint, result in results.items():
        if "response" in result:
            body = f"<pre>{json.dumps(result['response'], indent=2)}</pre>"
        else:
            body = f"<p><strong>Content-Type:</strong> {result.get('content_type')} &middot; <strong>Bytes:</strong> {result.get('length')}</p>"
        rows.append(
            f"""
            <section>
              <h2>{endpoint}</h2>
              <p><strong>Status:</strong> {result["status"]}</p>
              {body}
            </section>
            """
        )
    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Swagger API Test Results</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
        h1 {{ margin-bottom: 8px; }}
        .note {{ margin-bottom: 24px; color: #4b5563; }}
        section {{ border: 1px solid #d1d5db; border-left: 6px solid #49cc90; border-radius: 6px; margin: 16px 0; padding: 16px; }}
        h2 {{ font-size: 18px; margin: 0 0 8px; }}
        pre {{ background: #f6f8fa; border-radius: 6px; padding: 12px; white-space: pre-wrap; word-break: break-word; }}
      </style>
    </head>
    <body>
      <h1>Swagger API Test Results</h1>
      <p class="note">These endpoint results were produced against the same local FastAPI server shown in Swagger UI.</p>
      {''.join(rows)}
    </body>
    </html>
    """
    (DOCS_DIR / "swagger-test-results.html").write_text(html, encoding="utf-8")


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_body, pdf_content_type = multipart_file(
        "file", "demo-financial-report.pdf", make_demo_pdf(), "application/pdf"
    )

    results: dict[str, dict] = {}
    results["GET / (dashboard UI)"] = call_html("GET", "/")
    results["GET /ui-testing (API console UI)"] = call_html("GET", "/ui-testing")
    results["GET /api/status"] = call_json("GET", "/api/status")
    results["GET /health"] = call_json("GET", "/health")
    results["POST /api/reports"] = call_json(
        "POST", "/api/reports", pdf_body, {"Content-Type": pdf_content_type}
    )
    report_id = results["POST /api/reports"]["response"]["report_id"]
    results["GET /api/reports"] = call_json("GET", "/api/reports")
    results["GET /api/reports/{report_id}"] = call_json("GET", f"/api/reports/{report_id}")
    results["POST /api/query"] = call_json(
        "POST",
        "/api/query",
        json.dumps(
            {
                "report_id": report_id,
                "question": "What was the revenue and net profit?",
            }
        ).encode("utf-8"),
        {"Content-Type": "application/json"},
    )
    invalid_body, invalid_content_type = multipart_file("file", "notes.txt", b"not a pdf", "text/plain")
    results["POST /api/reports invalid file"] = call_json(
        "POST", "/api/reports", invalid_body, {"Content-Type": invalid_content_type}
    )

    (DOCS_DIR / "swagger-test-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_html(results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

