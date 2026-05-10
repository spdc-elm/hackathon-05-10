"""Build graph topology by scanning [[wikilinks]] across the vault."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.vault import VaultService, VaultPage


RELATION_LABELS = {
    "prerequisite": "前置依赖",
    "contains": "包含",
    "parallel": "并列",
    "applies_to": "应用于",
}

RELATION_LABELS_REVERSE = {v: k for k, v in RELATION_LABELS.items()}

CATEGORY_COLORS = {
    "核心概念": "#7ecb9a",
    "方法": "#6ab0d4",
    "结构": "#d4a06a",
    "过程": "#c47ed4",
    "物质": "#d47e7e",
}

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
        safe_name = concept_name.replace("/", "_").replace("\\", "_")
        path = f"concepts/{safe_name}.md"
        try:
            page = self.vault.read_page(path)
        except FileNotFoundError:
            return None

        return {
            "node": {
                "id": page.frontmatter.get("id", safe_name),
                "name": concept_name,
                "aliases": page.frontmatter.get("aliases", []),
                "definition": self._extract_definition(page.body),
                "category": page.frontmatter.get("category", ""),
                "textbook_id": page.frontmatter.get("textbook_id", ""),
                "chapter_id": page.frontmatter.get("chapter_id", ""),
                "confidence": page.frontmatter.get("confidence", 0.0),
                "evidence": self._extract_evidence(page.body),
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
            if query_lower in name.lower():
                matches.append({"name": name, "match_field": "name", "score": 1.0})
                continue

            content = md_file.read_text(encoding="utf-8")
            fm, _ = self.vault._parse_frontmatter(content)
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
            wikilinks = self.vault._extract_wikilinks(body)
            pages.append(VaultPage(path=relative, frontmatter=fm, body=body, wikilinks=wikilinks))
        return pages

    def _build_nodes(self, pages: list[VaultPage]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for page in pages:
            fm = page.frontmatter
            name = Path(page.path).stem
            textbook_id = fm.get("textbook_id", "unknown")
            nodes.append({
                "id": fm.get("id", name),
                "label": name,
                "category": fm.get("category", "核心概念"),
                "document_id": textbook_id,
                "chapter_id": fm.get("chapter_id", ""),
                "source_count": 1,
                "source_documents": [textbook_id],
                "size": 20,
                "color_key": fm.get("category", "核心概念"),
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
                results.append((link_match.group(1), relation_type))
        return results

    def _build_legend(self, pages: list[VaultPage]) -> dict[str, Any]:
        documents: list[dict[str, str]] = []
        seen_docs: set[str] = set()
        for page in pages:
            doc_id = page.frontmatter.get("textbook_id", "unknown")
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                documents.append({
                    "document_id": doc_id,
                    "title": doc_id,
                    "color_key": doc_id,
                })

        relations = [
            {"relation_type": rt, "label": label, "color_key": rt}
            for rt, label in RELATION_LABELS.items()
        ]

        return {"documents": documents, "relations": relations}

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
