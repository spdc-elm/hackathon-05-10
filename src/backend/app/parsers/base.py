"""Shared parser data structures."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AssetReference:
    """Non-text asset found while parsing a document."""

    kind: str
    label: str
    path: str
    line: int | None = None


@dataclass(slots=True)
class ParsedChapter:
    """Contest-compatible chapter record with extra source metadata."""

    chapter_id: str
    title: str
    content: str
    char_count: int
    page_start: int | None = None
    page_end: int | None = None
    level: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    assets: list[AssetReference] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    """Unified parser output used by downstream graph and RAG stages."""

    textbook_id: str
    filename: str
    title: str
    total_pages: int | None
    total_chars: int
    chapters: list[ParsedChapter]
    format: str
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


def asset_reference_from_dict(data: dict[str, Any]) -> AssetReference:
    return AssetReference(
        kind=str(data.get("kind") or ""),
        label=str(data.get("label") or ""),
        path=str(data.get("path") or ""),
        line=_optional_int(data.get("line")),
    )


def parsed_chapter_from_dict(data: dict[str, Any]) -> ParsedChapter:
    return ParsedChapter(
        chapter_id=str(data.get("chapter_id") or ""),
        title=str(data.get("title") or ""),
        content=str(data.get("content") or ""),
        char_count=_required_int(data.get("char_count"), len(str(data.get("content") or ""))),
        page_start=_optional_int(data.get("page_start")),
        page_end=_optional_int(data.get("page_end")),
        level=_optional_int(data.get("level")),
        line_start=_optional_int(data.get("line_start")),
        line_end=_optional_int(data.get("line_end")),
        assets=[
            asset_reference_from_dict(item)
            for item in data.get("assets", [])
            if isinstance(item, dict)
        ],
    )


def parsed_document_from_dict(data: dict[str, Any]) -> ParsedDocument:
    return ParsedDocument(
        textbook_id=str(data.get("textbook_id") or ""),
        filename=str(data.get("filename") or ""),
        title=str(data.get("title") or ""),
        total_pages=_optional_int(data.get("total_pages")),
        total_chars=_required_int(data.get("total_chars"), 0),
        chapters=[
            parsed_chapter_from_dict(item)
            for item in data.get("chapters", [])
            if isinstance(item, dict)
        ],
        format=str(data.get("format") or ""),
        source_path=data.get("source_path"),
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _required_int(value: Any, default: int) -> int:
    parsed = _optional_int(value)
    return default if parsed is None else parsed


class DocumentParser:
    """Base interface for document parsers."""

    format: str

    def parse(self, path: str | Path, *, textbook_id: str | None = None) -> ParsedDocument:
        raise NotImplementedError
