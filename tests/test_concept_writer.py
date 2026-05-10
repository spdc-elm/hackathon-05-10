"""Tests for concept writer (LLM extraction → vault MD files)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Sequence

import pytest

from app.parsers.base import ParsedChapter, ParsedDocument
from app.services.concept_writer import ConceptWriter
from app.services.llm import LLMClient, MessageInput
from app.services.vault import VaultService


class FakeLLMClient(LLMClient):
    """Returns a preset JSON response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    async def generate_text(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        messages: Sequence[MessageInput] | None = None,
        temperature: float | None = None,
    ) -> str:
        import json
        return json.dumps(self._response, ensure_ascii=False)


FAKE_LLM_RESPONSE = {
    "concepts": [
        {
            "name": "炎症",
            "aliases": ["inflammation"],
            "definition": "机体对损伤因子的防御性反应",
            "category": "核心概念",
            "relations": [
                {"type": "prerequisite", "target": "细胞损伤", "description": "需先理解细胞损伤"},
                {"type": "contains", "target": "急性炎症", "description": "炎症的一种类型"},
            ],
            "evidence": "炎症是具有血管系统的活体组织对损伤因子的反应",
        },
        {
            "name": "细胞损伤",
            "aliases": ["cell injury"],
            "definition": "各种因素导致细胞结构和功能异常",
            "category": "核心概念",
            "relations": [],
            "evidence": "细胞损伤是病理学的基本概念",
        },
    ]
}


@pytest.fixture
def vault():
    with TemporaryDirectory() as tmp:
        svc = VaultService(Path(tmp))
        svc.ensure_structure()
        yield svc


@pytest.fixture
def document() -> ParsedDocument:
    return ParsedDocument(
        textbook_id="book_01",
        filename="病理学.pdf",
        title="病理学",
        total_pages=100,
        total_chars=5000,
        chapters=[
            ParsedChapter(
                chapter_id="ch_001",
                title="第一章 炎症",
                content="炎症是具有血管系统的活体组织对损伤因子的反应。细胞损伤是病理学的基本概念。",
                char_count=40,
            ),
        ],
        format="pdf",
    )


class TestConceptWriter:
    @pytest.mark.asyncio
    async def test_extract_and_write_creates_concept_files(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        client = FakeLLMClient(FAKE_LLM_RESPONSE)
        writer = ConceptWriter(vault, client=client)
        paths = await writer.extract_and_write(document)
        assert len(paths) == 2
        assert "concepts/炎症.md" in paths
        assert "concepts/细胞损伤.md" in paths

    @pytest.mark.asyncio
    async def test_concept_file_has_frontmatter(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        client = FakeLLMClient(FAKE_LLM_RESPONSE)
        writer = ConceptWriter(vault, client=client)
        await writer.extract_and_write(document)
        page = vault.read_page("concepts/炎症.md")
        assert page.frontmatter["id"] == "book_01_node_001"
        assert page.frontmatter["category"] == "核心概念"
        assert page.frontmatter["textbook_id"] == "book_01"
        assert "confidence" not in page.frontmatter
        assert "inflammation" in page.frontmatter["aliases"]

    @pytest.mark.asyncio
    async def test_concept_file_has_wikilinks(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        client = FakeLLMClient(FAKE_LLM_RESPONSE)
        writer = ConceptWriter(vault, client=client)
        await writer.extract_and_write(document)
        page = vault.read_page("concepts/炎症.md")
        assert "[[细胞损伤]]" in page.body
        assert "[[急性炎症]]" in page.body
        assert page.wikilinks == ["细胞损伤", "急性炎症"]

    @pytest.mark.asyncio
    async def test_concept_file_has_evidence(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        client = FakeLLMClient(FAKE_LLM_RESPONSE)
        writer = ConceptWriter(vault, client=client)
        await writer.extract_and_write(document)
        page = vault.read_page("concepts/炎症.md")
        assert "原文证据" in page.body
        assert "炎症是具有血管系统" in page.body


class TestTextbookChapterWriter:
    def test_writes_meta_and_chapters(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        writer = ConceptWriter(vault)
        paths = writer.write_textbook_chapters(document)
        assert len(paths) == 2  # _meta.md + 1 chapter
        assert any("_meta.md" in p for p in paths)

        meta = vault.read_page("textbooks/病理学/_meta.md")
        assert meta.frontmatter["textbook_id"] == "book_01"
        assert meta.frontmatter["chapter_count"] == 1

    def test_chapter_content_preserved(
        self, vault: VaultService, document: ParsedDocument
    ) -> None:
        writer = ConceptWriter(vault)
        writer.write_textbook_chapters(document)
        pages = vault.list_pages("textbooks")
        ch_pages = [p for p in pages if "_meta" not in p.path]
        assert len(ch_pages) == 1
        ch = vault.read_page(ch_pages[0].path)
        assert "炎症是具有血管系统" in ch.body
