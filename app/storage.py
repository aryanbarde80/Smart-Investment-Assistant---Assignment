import json
import os
import tempfile
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
        payload = json.dumps(report, indent=2, default=str)
        # Write to a temp file in the same directory, then atomically replace the
        # target so a crash or concurrent read mid-write can never see a half-written
        # or corrupted report file.
        fd, tmp_path = tempfile.mkstemp(dir=self.storage_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(payload)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

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

