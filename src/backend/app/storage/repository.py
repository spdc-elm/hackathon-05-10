"""Filesystem-backed runtime repository for document metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.parsers.base import ParsedDocument, parsed_document_from_dict


class RuntimeRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.documents_dir = self.root / "documents"
        self.jobs_dir = self.root / "jobs"

    def save_document(self, document: ParsedDocument, meta: dict[str, Any]) -> None:
        document_dir = self._document_dir(document.textbook_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(document_dir / "document.json", document.to_dict())
        self._write_json(document_dir / "meta.json", dict(meta))

    def load_document(self, document_id: str) -> ParsedDocument:
        path = self._document_dir(document_id) / "document.json"
        return parsed_document_from_dict(self._read_json(path))

    def get_document_meta(self, document_id: str) -> dict[str, Any]:
        return self._read_json(self._document_dir(document_id) / "meta.json")

    def list_documents(self) -> list[dict[str, Any]]:
        if not self.documents_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for meta_path in self.documents_dir.glob("*/meta.json"):
            try:
                records.append(self._read_json(meta_path))
            except FileNotFoundError:
                continue
        return sorted(
            records,
            key=lambda item: (str(item.get("created_at") or ""), str(item.get("document_id") or "")),
        )

    def update_document_meta(self, document_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        meta = self.get_document_meta(document_id)
        meta.update(updates)
        self._write_json(self._document_dir(document_id) / "meta.json", meta)
        return meta

    def save_job(self, job_id: str, job: dict[str, Any]) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._job_path(job_id), job)

    def load_job(self, job_id: str) -> dict[str, Any]:
        return self._read_json(self._job_path(job_id))

    def _document_dir(self, document_id: str) -> Path:
        return self.documents_dir / document_id

    def _job_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{path} did not contain a JSON object.")
        return data

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        tmp_path.replace(path)
