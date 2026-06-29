import json
from pathlib import Path
from typing import Any


class JsonReportStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, report_id: str) -> Path:
        safe_id = "".join(ch for ch in report_id if ch.isalnum() or ch in {"-", "_"})
        return self.storage_dir / f"{safe_id}.json"

    def save(self, report: dict[str, Any]) -> None:
        path = self._path(report["report_id"])
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    def get(self, report_id: str) -> dict[str, Any] | None:
        path = self._path(report_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for path in sorted(self.storage_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        return reports

