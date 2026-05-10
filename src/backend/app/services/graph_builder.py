"""Build graph topology by scanning [[wikilinks]] across the vault."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.merge_service import safe_name
from app.services.vault import VaultService, VaultPage


RELATION_LABELS = {
    "prerequisite": "前置依赖",
    "contains": "包含",
    "parallel": "并列",
    "applies_to": "应用于",
}

RELATION_LABELS_REVERSE = {v: k for k, v in RELATION_LABELS.items()}

RELATION_COLORS = {
    "prerequisite": "#e8a838",
    "contains": "#38b2e8",
    "parallel": "#8ce838",
    "applies_to": "#e838b2",
}

RELATION_LINE_RE = re.compile(
    r"^-\s*(前置依赖|包含|并列|应用于):\s*(.+)$", re.MULTILINE
)


class GraphBuilder:
    """Derive graph view from vault wikilink topology."""

    def __init__(self, vault: VaultService) -> None:
        self.vault = vault

    def build_graph_view(self) -> dict[str, Any]:
        concept_pages = self._load_concept_pages()
        nodes = self._build_nodes(concept_pages)
        edges = self._build_edges(concept_pages)
        legend = self._build_legend(concept_pages)

        return {
            "view_id": "vault_graph",
            "mode": "per_document",
            "nodes": nodes,
            "edges": edges,
            "legend": legend,
        }

    def get_node_detail(self, concept_name: str) -> dict[str, Any] | None:
        path = f"concepts/{safe_name(concept_name)}.md"
        try:
            page = self.vault.read_page(path)
        except FileNotFoundError:
            return None
        if page.frontmatter.get("status") == "archived":
            return None

        return {
            "node": {
                "id": page.frontmatter.get("id", Path(page.path).stem),
                "name": Path(page.path).stem,
                "canonical_name": page.frontmatter.get("canonical_name", concept_name),
                "aliases": page.frontmatter.get("aliases", []),
                "definition": self._extract_definition(page.body),
                "category": page.frontmatter.get("category", ""),
                "textbook_id": page.frontmatter.get("textbook_id", ""),
                "chapter_id": page.frontmatter.get("chapter_id", ""),
                "evidence": self._extract_evidence(page.body),
                "merge_decision": page.frontmatter.get("merge_decision"),
                "merged_from": page.frontmatter.get("merged_from", []),
            },
            "content_md": page.body,
        }

    def search_nodes(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches: list[dict[str, Any]] = []
        concepts_dir = self.vault.root / "concepts"
        if not concepts_dir.exists():
            return matches

        for md_file in concepts_dir.rglob("*.md"):
            name = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            fm, _ = self.vault._parse_frontmatter(content)
            if fm.get("status") == "archived":
                continue

            canonical_name = str(fm.get("canonical_name") or name)
            if query_lower in name.lower() or query_lower in canonical_name.lower():
                matches.append({"name": name, "match_field": "name", "score": 1.0})
                continue

            aliases = fm.get("aliases", [])
            if any(query_lower in str(a).lower() for a in aliases):
                matches.append({"name": name, "match_field": "aliases", "score": 0.8})

        return sorted(matches, key=lambda x: -x["score"])

    def _load_concept_pages(self) -> list[VaultPage]:
        concepts_dir = self.vault.root / "concepts"
        if not concepts_dir.exists():
            return []

        pages: list[VaultPage] = []
        for md_file in sorted(concepts_dir.rglob("*.md")):
            relative = str(md_file.relative_to(self.vault.root))
            content = md_file.read_text(encoding="utf-8")
            fm, body = self.vault._parse_frontmatter(content)
            if fm.get("status") == "archived":
                continue
            wikilinks = self.vault._extract_wikilinks(body)
            pages.append(VaultPage(path=relative, frontmatter=fm, body=body, wikilinks=wikilinks))
        return pages

    def _build_nodes(self, pages: list[VaultPage]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        canonical_counts: dict[str, int] = {}
        for page in pages:
            canonical_name = self._canonical_name(page)
            canonical_counts[canonical_name] = canonical_counts.get(canonical_name, 0) + 1

        for page in pages:
            fm = page.frontmatter
            name = Path(page.path).stem
            canonical_name = self._canonical_name(page)
            source_records = self._source_records(fm)
            source_documents = self._source_documents(source_records)
            color_key = self._node_color_key(fm, source_documents)
            document_id = "merged" if color_key == "merged" else source_documents[0]
            label = canonical_name
            if canonical_counts.get(canonical_name, 0) > 1:
                label = f"{canonical_name} · {self._source_hint(source_records)}"
            nodes.append({
                "id": fm.get("id", name),
                "name": name,
                "label": label,
                "canonical_name": canonical_name,
                "category": fm.get("category", "核心概念"),
                "document_id": document_id,
                "chapter_id": fm.get("chapter_id", ""),
                "source_count": len(source_records),
                "source_documents": source_documents,
                "size": 20,
                "color_key": color_key,
                "merge_decision": fm.get("merge_decision"),
            })
        return nodes

    def _build_edges(self, pages: list[VaultPage]) -> list[dict[str, Any]]:
        name_to_id: dict[str, str] = {}
        for page in pages:
            name = Path(page.path).stem
            name_to_id[name] = page.frontmatter.get("id", name)

        edges: list[dict[str, Any]] = []
        edge_idx = 0

        for page in pages:
            source_name = Path(page.path).stem
            source_id = name_to_id.get(source_name, source_name)

            for target_name, relation_type in self._parse_relations(page.body):
                target_id = name_to_id.get(target_name)
                if target_id is None:
                    continue
                edge_idx += 1
                edges.append({
                    "id": f"edge_{edge_idx:03d}",
                    "source": source_id,
                    "target": target_id,
                    "relation_type": relation_type,
                    "label": RELATION_LABELS.get(relation_type, relation_type),
                    "color_key": relation_type,
                })

        return edges

    def _parse_relations(self, body: str) -> list[tuple[str, str]]:
        """Parse typed links from the ## 关系 section."""
        results: list[tuple[str, str]] = []
        for match in RELATION_LINE_RE.finditer(body):
            label = match.group(1)
            targets_text = match.group(2)
            relation_type = RELATION_LABELS_REVERSE.get(label)
            if not relation_type:
                continue
            for link_match in re.finditer(r"\[\[([^\]]+)\]\]", targets_text):
                target = link_match.group(1).split("|", 1)[0].strip()
                results.append((target, relation_type))
        return results

    def _build_legend(self, pages: list[VaultPage]) -> dict[str, Any]:
        documents: list[dict[str, str]] = []
        seen_docs: set[str] = set()
        has_merged = False
        for page in pages:
            source_documents = self._source_documents(self._source_records(page.frontmatter))
            if self._node_color_key(page.frontmatter, source_documents) == "merged":
                has_merged = True
            for doc_id in source_documents:
                if doc_id in seen_docs:
                    continue
                seen_docs.add(doc_id)
                documents.append({
                    "document_id": doc_id,
                    "title": doc_id,
                    "color_key": doc_id,
                })

        if has_merged:
            documents.append({
                "document_id": "merged",
                "title": "Merged",
                "color_key": "merged",
            })

        relations = [
            {"relation_type": rt, "label": label, "color_key": rt}
            for rt, label in RELATION_LABELS.items()
        ]

        return {"documents": documents, "relations": relations}

    def _source_records(self, frontmatter: dict[str, Any]) -> list[dict[str, Any]]:
        raw_sources = frontmatter.get("sources")
        records: list[dict[str, Any]] = []
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if not isinstance(item, dict):
                    continue
                textbook_id = str(item.get("textbook_id") or "").strip()
                if textbook_id:
                    records.append({**item, "textbook_id": textbook_id})

        if records:
            return records

        textbook_id = str(frontmatter.get("textbook_id") or "unknown").strip() or "unknown"
        return [{
            "textbook_id": textbook_id,
            "chapter_id": frontmatter.get("chapter_id", ""),
        }]

    def _source_documents(self, source_records: list[dict[str, Any]]) -> list[str]:
        documents: list[str] = []
        seen: set[str] = set()
        for source in source_records:
            textbook_id = str(source.get("textbook_id") or "unknown").strip() or "unknown"
            if textbook_id in seen:
                continue
            seen.add(textbook_id)
            documents.append(textbook_id)
        return documents or ["unknown"]

    def _source_color_key(self, source_documents: list[str]) -> str:
        return "merged" if len(source_documents) > 1 else source_documents[0]

    def _node_color_key(self, frontmatter: dict[str, Any], source_documents: list[str]) -> str:
        if self._is_merged_result(frontmatter):
            return "merged"
        return self._source_color_key(source_documents)

    def _is_merged_result(self, frontmatter: dict[str, Any]) -> bool:
        merged_from = frontmatter.get("merged_from")
        if isinstance(merged_from, list) and any(str(item).strip() for item in merged_from):
            return True
        return bool(str(frontmatter.get("merge_decision") or "").strip())

    def _canonical_name(self, page: VaultPage) -> str:
        return str(page.frontmatter.get("canonical_name") or Path(page.path).stem).strip()

    def _source_hint(self, source_records: list[dict[str, Any]]) -> str:
        if not source_records:
            return "unknown"
        first = source_records[0]
        textbook_id = str(first.get("textbook_id") or "unknown")
        chapter_id = str(first.get("chapter_id") or "").strip()
        return f"{textbook_id}/{chapter_id}" if chapter_id else textbook_id

    def _extract_definition(self, body: str) -> str:
        lines = body.split("\n")
        in_definition = False
        definition_lines: list[str] = []
        for line in lines:
            if line.startswith("# "):
                in_definition = True
                continue
            if in_definition:
                if line.startswith("## ") or not line.strip():
                    if definition_lines:
                        break
                    continue
                definition_lines.append(line)
        return " ".join(definition_lines).strip()

    def _extract_evidence(self, body: str) -> str:
        in_evidence = False
        for line in body.split("\n"):
            if "## 原文证据" in line:
                in_evidence = True
                continue
            if in_evidence and line.startswith("> "):
                return line[2:].strip()
        return ""
