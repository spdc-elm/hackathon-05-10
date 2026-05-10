"""Converts LLM extraction output into concept MD files with [[wikilinks]]."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.parsers.base import ParsedChapter, ParsedDocument
from app.services.llm import LLMClient, generate_json
from app.services.vault import VaultService


EXTRACTION_SYSTEM_PROMPT = """你是教材知识图谱抽取器。
只从给定章节正文抽取知识，不使用外部知识。
输出必须是 JSON object，包含 concepts 数组。
每个 concept:
  - name: 概念名（简洁）
  - aliases: 别名列表
  - definition: 定义(1-2句话)
  - category: 核心概念|方法|结构|过程|物质
  - relations: [{type, target, description}]
    - type 只能是 prerequisite, contains, parallel, applies_to
    - target 是另一个概念的 name
    - description 简要说明关系
  - evidence: 章节原文中的连续短句（直接引用）
  - confidence: 0.0-1.0
每章最多抽取 8-15 个可教学的核心知识点。不要抽取过于宽泛或过于琐碎的概念。"""

RELATION_LABELS = {
    "prerequisite": "前置依赖",
    "contains": "包含",
    "parallel": "并列",
    "applies_to": "应用于",
}


@dataclass
class ExtractedConcept:
    name: str
    aliases: list[str]
    definition: str
    category: str
    relations: list[dict[str, str]]
    evidence: str
    confidence: float
    textbook_id: str
    chapter_id: str


class ConceptWriter:
    """Extract concepts via LLM and write them as vault MD pages."""

    def __init__(
        self,
        vault: VaultService,
        *,
        client: LLMClient | None = None,
    ) -> None:
        self.vault = vault
        self.client = client

    async def extract_and_write(self, document: ParsedDocument) -> list[str]:
        """Extract concepts from all chapters and write to vault.

        Returns list of vault paths written.
        """
        written_paths: list[str] = []
        concept_index = 0

        for chapter in document.chapters:
            if not chapter.content.strip():
                continue

            payload = await generate_json(
                self._build_prompt(document, chapter),
                system=EXTRACTION_SYSTEM_PROMPT,
                client=self.client,
            )

            concepts = self._normalize_payload(document, chapter, payload)
            for concept in concepts:
                concept_index += 1
                path = self._write_concept(concept, document, concept_index)
                written_paths.append(path)

        return written_paths

    def write_textbook_chapters(self, document: ParsedDocument) -> list[str]:
        """Write parsed chapters as MD files under vault/textbooks/{title}/."""
        safe_title = document.title.replace("/", "_").replace("\\", "_")
        written: list[str] = []

        meta_frontmatter = {
            "textbook_id": document.textbook_id,
            "title": document.title,
            "filename": document.filename,
            "total_pages": document.total_pages,
            "total_chars": document.total_chars,
            "chapter_count": len(document.chapters),
        }
        meta_path = f"textbooks/{safe_title}/_meta.md"
        self.vault.write_page(meta_path, meta_frontmatter, f"# {document.title}\n")
        written.append(meta_path)

        for chapter in document.chapters:
            ch_frontmatter = {
                "chapter_id": chapter.chapter_id,
                "textbook_id": document.textbook_id,
                "title": chapter.title,
                "page_start": chapter.page_start,
                "page_end": chapter.page_end,
                "char_count": chapter.char_count,
            }
            safe_ch = chapter.title.replace("/", "_").replace("\\", "_").replace(" ", "-")
            ch_path = f"textbooks/{safe_title}/{safe_ch}.md"
            self.vault.write_page(ch_path, ch_frontmatter, f"# {chapter.title}\n\n{chapter.content}")
            written.append(ch_path)

        return written

    def _build_prompt(self, document: ParsedDocument, chapter: ParsedChapter) -> str:
        return (
            f"教材: {document.title}\n"
            f"章节: {chapter.title}\n"
            f"章节ID: {chapter.chapter_id}\n\n"
            f"正文:\n{chapter.content[:8000]}"
        )

    def _normalize_payload(
        self, document: ParsedDocument, chapter: ParsedChapter, payload: Any
    ) -> list[ExtractedConcept]:
        if not isinstance(payload, dict):
            return []
        raw_concepts = payload.get("concepts", [])
        if not isinstance(raw_concepts, list):
            return []

        results: list[ExtractedConcept] = []
        for item in raw_concepts:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue

            relations = []
            for rel in item.get("relations") or []:
                if not isinstance(rel, dict):
                    continue
                rel_type = str(rel.get("type") or "").strip()
                target = str(rel.get("target") or "").strip()
                if rel_type in RELATION_LABELS and target:
                    relations.append({
                        "type": rel_type,
                        "target": target,
                        "description": str(rel.get("description") or ""),
                    })

            results.append(ExtractedConcept(
                name=name,
                aliases=[str(a) for a in (item.get("aliases") or []) if a],
                definition=str(item.get("definition") or ""),
                category=str(item.get("category") or "核心概念"),
                relations=relations,
                evidence=str(item.get("evidence") or ""),
                confidence=min(1.0, max(0.0, float(item.get("confidence") or 0.8))),
                textbook_id=document.textbook_id,
                chapter_id=chapter.chapter_id,
            ))

        return results

    def _write_concept(self, concept: ExtractedConcept, document: ParsedDocument, index: int) -> str:
        stable_id = f"{document.textbook_id}_node_{index:03d}"

        frontmatter: dict[str, Any] = {
            "id": stable_id,
            "category": concept.category,
            "aliases": concept.aliases,
            "textbook_id": concept.textbook_id,
            "chapter_id": concept.chapter_id,
            "confidence": concept.confidence,
        }

        body = f"# {concept.name}\n\n{concept.definition}\n"

        if concept.relations:
            body += "\n## 关系\n\n"
            for rel in concept.relations:
                label = RELATION_LABELS.get(rel["type"], rel["type"])
                body += f"- {label}: [[{rel['target']}]]\n"

        if concept.evidence:
            body += f"\n## 原文证据\n\n> {concept.evidence}\n"

        body += f"\n来源: {document.title} {concept.chapter_id}\n"

        safe_name = concept.name.replace("/", "_").replace("\\", "_")
        relative_path = f"concepts/{safe_name}.md"
        self.vault.write_page(relative_path, frontmatter, body)
        return relative_path
