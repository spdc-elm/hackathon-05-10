"""Tests for graph builder deriving topology from vault wikilinks."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.services.graph_builder import GraphBuilder
from app.services.vault import VaultService


@pytest.fixture
def vault():
    with TemporaryDirectory() as tmp:
        svc = VaultService(Path(tmp))
        svc.ensure_structure()
        yield svc


@pytest.fixture
def builder(vault: VaultService) -> GraphBuilder:
    return GraphBuilder(vault)


class TestGraphBuilder:
    def test_empty_vault_returns_empty_graph(self, builder: GraphBuilder) -> None:
        view = builder.build_graph_view()
        assert view["nodes"] == []
        assert view["edges"] == []
        assert view["view_id"] == "vault_graph"

    def test_single_concept_no_edges(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/A.md",
            {"id": "n1", "category": "核心概念", "textbook_id": "book1", "chapter_id": "ch1"},
            "# A\n\nDefinition of A",
        )
        view = builder.build_graph_view()
        assert len(view["nodes"]) == 1
        assert view["nodes"][0]["id"] == "n1"
        assert view["nodes"][0]["label"] == "A"
        assert view["nodes"][0]["color_key"] == "book1"
        assert view["nodes"][0]["source_documents"] == ["book1"]
        assert view["edges"] == []

    def test_multisource_concept_uses_merged_color_key(
        self, vault: VaultService, builder: GraphBuilder
    ) -> None:
        vault.write_page(
            "concepts/A.md",
            {
                "id": "concept_A",
                "category": "核心概念",
                "sources": [
                    {"textbook_id": "book1", "chapter_id": "ch1"},
                    {"textbook_id": "book2", "chapter_id": "ch3"},
                ],
            },
            "# A\n\nDefinition of A",
        )

        view = builder.build_graph_view()

        node = view["nodes"][0]
        assert node["document_id"] == "merged"
        assert node["source_count"] == 2
        assert node["source_documents"] == ["book1", "book2"]
        assert node["color_key"] == "merged"
        assert view["legend"]["documents"] == [
            {"document_id": "book1", "title": "book1", "color_key": "book1"},
            {"document_id": "book2", "title": "book2", "color_key": "book2"},
            {"document_id": "merged", "title": "Merged", "color_key": "merged"},
        ]

    def test_multiple_chapters_from_same_document_keep_document_color(
        self, vault: VaultService, builder: GraphBuilder
    ) -> None:
        vault.write_page(
            "concepts/A.md",
            {
                "id": "concept_A",
                "category": "核心概念",
                "sources": [
                    {"textbook_id": "book1", "chapter_id": "ch1"},
                    {"textbook_id": "book1", "chapter_id": "ch2"},
                ],
            },
            "# A\n\nDefinition of A",
        )

        view = builder.build_graph_view()

        node = view["nodes"][0]
        assert node["document_id"] == "book1"
        assert node["source_count"] == 2
        assert node["source_documents"] == ["book1"]
        assert node["color_key"] == "book1"

    def test_applied_merge_from_same_document_uses_merged_color_key(
        self, vault: VaultService, builder: GraphBuilder
    ) -> None:
        vault.write_page(
            "concepts/A.md",
            {
                "id": "concept_A",
                "category": "核心概念",
                "sources": [
                    {"textbook_id": "book1", "chapter_id": "ch1"},
                    {"textbook_id": "book1", "chapter_id": "ch2"},
                ],
                "merged_from": ["concepts/A.md", "concepts/A__book1__ch2__1.md"],
                "merge_decision": "merge_same_name_A",
            },
            "# A\n\nMerged definition of A",
        )

        view = builder.build_graph_view()

        node = view["nodes"][0]
        assert node["document_id"] == "merged"
        assert node["source_count"] == 2
        assert node["source_documents"] == ["book1"]
        assert node["color_key"] == "merged"
        assert view["legend"]["documents"] == [
            {"document_id": "book1", "title": "book1", "color_key": "book1"},
            {"document_id": "merged", "title": "Merged", "color_key": "merged"},
        ]

    def test_linked_concepts_produce_edges(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/A.md",
            {"id": "n1", "category": "核心概念", "textbook_id": "book1"},
            "# A\n\nDef A\n\n## 关系\n\n- 前置依赖: [[B]]\n",
        )
        vault.write_page(
            "concepts/B.md",
            {"id": "n2", "category": "方法", "textbook_id": "book1"},
            "# B\n\nDef B",
        )
        view = builder.build_graph_view()
        assert len(view["nodes"]) == 2
        assert len(view["edges"]) == 1
        edge = view["edges"][0]
        assert edge["source"] == "n1"
        assert edge["target"] == "n2"
        assert edge["relation_type"] == "prerequisite"

    def test_multiple_relation_types(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/X.md",
            {"id": "x1", "textbook_id": "b1"},
            "# X\n\nDef\n\n## 关系\n\n- 包含: [[Y]]\n- 并列: [[Z]]\n",
        )
        vault.write_page("concepts/Y.md", {"id": "y1", "textbook_id": "b1"}, "# Y\n\nDef")
        vault.write_page("concepts/Z.md", {"id": "z1", "textbook_id": "b1"}, "# Z\n\nDef")
        view = builder.build_graph_view()
        edge_types = {e["relation_type"] for e in view["edges"]}
        assert edge_types == {"contains", "parallel"}

    def test_dangling_links_excluded(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/A.md",
            {"id": "n1", "textbook_id": "b1"},
            "# A\n\n## 关系\n\n- 前置依赖: [[NoExist]]\n",
        )
        view = builder.build_graph_view()
        assert len(view["nodes"]) == 1
        assert view["edges"] == []

    def test_multiple_targets_on_one_line(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/A.md",
            {"id": "n1", "textbook_id": "b1"},
            "# A\n\n## 关系\n\n- 包含: [[B]], [[C]]\n",
        )
        vault.write_page("concepts/B.md", {"id": "n2", "textbook_id": "b1"}, "# B")
        vault.write_page("concepts/C.md", {"id": "n3", "textbook_id": "b1"}, "# C")
        view = builder.build_graph_view()
        assert len(view["edges"]) == 2


class TestNodeDetail:
    def test_returns_content_md(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page(
            "concepts/炎症.md",
            {"id": "n1", "category": "核心概念", "aliases": ["inflammation"]},
            "# 炎症\n\n机体对损伤的防御反应\n\n## 原文证据\n\n> 原文引用\n",
        )
        detail = builder.get_node_detail("炎症")
        assert detail is not None
        assert detail["node"]["name"] == "炎症"
        assert detail["node"]["definition"] == "机体对损伤的防御反应"
        assert detail["node"]["evidence"] == "原文引用"
        assert "# 炎症" in detail["content_md"]

    def test_missing_concept_returns_none(self, builder: GraphBuilder) -> None:
        assert builder.get_node_detail("不存在") is None


class TestSearch:
    def test_search_by_name(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page("concepts/炎症.md", {"aliases": []}, "# 炎症")
        vault.write_page("concepts/免疫.md", {"aliases": []}, "# 免疫")
        results = builder.search_nodes("炎")
        assert len(results) == 1
        assert results[0]["name"] == "炎症"

    def test_search_by_alias(self, vault: VaultService, builder: GraphBuilder) -> None:
        vault.write_page("concepts/炎症.md", {"aliases": ["inflammation"]}, "# 炎症")
        results = builder.search_nodes("inflam")
        assert len(results) == 1
        assert results[0]["match_field"] == "aliases"

    def test_search_empty_query(self, builder: GraphBuilder) -> None:
        assert builder.search_nodes("") == []
