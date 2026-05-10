"""Tests for merge decision audit and execution."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.services.graph_builder import GraphBuilder
from app.services.merge_service import MergeConflictError, MergeService, MergeValidationError
from app.services.vault import VaultService


@pytest.fixture
def vault():
    with TemporaryDirectory() as tmp:
        svc = VaultService(Path(tmp))
        svc.ensure_structure()
        yield svc


@pytest.fixture
def merge_service(vault: VaultService) -> MergeService:
    return MergeService(vault)


def write_duplicate_concepts(vault: VaultService) -> None:
    vault.write_page(
        "concepts/A.md",
        {
            "id": "concept_A",
            "canonical_name": "A",
            "status": "active",
            "category": "核心概念",
            "sources": [{"textbook_id": "doc1", "chapter_id": "ch1"}],
        },
        "# A\n\nDefinition from doc1\n\n## 关系\n\n- 并列: [[B]]\n",
    )
    vault.write_page(
        "concepts/A__doc2__ch2__1.md",
        {
            "id": "concept_A__doc2__ch2__1",
            "canonical_name": "A",
            "status": "active",
            "category": "核心概念",
            "sources": [{"textbook_id": "doc2", "chapter_id": "ch2"}],
        },
        "# A\n\nDefinition from doc2\n",
    )


class TestMergeScan:
    def test_scan_same_name_creates_candidate(
        self, vault: VaultService, merge_service: MergeService
    ) -> None:
        write_duplicate_concepts(vault)

        decisions = merge_service.scan_same_name_candidates()

        assert len(decisions) == 1
        decision = decisions[0]
        assert decision.decision_id == "merge_same_name_A"
        assert decision.status == "candidate"
        assert decision.affected_nodes == ["concepts/A.md", "concepts/A__doc2__ch2__1.md"]

        original = vault.read_page("concepts/A.md")
        assert "merge_same_name_A" in original.frontmatter["merge_decisions"]


class TestMergeExecute:
    def test_execute_writes_merged_node_archives_old_and_rewrites_links(
        self, vault: VaultService, merge_service: MergeService
    ) -> None:
        write_duplicate_concepts(vault)
        vault.write_page(
            "textbooks/book/chapter.md",
            {},
            "See [[A__doc2__ch2__1|second version]] and [[A]].",
        )
        merge_service.scan_same_name_candidates()

        result = merge_service.execute_merge(
            decision_id="merge_same_name_A",
            affected_nodes=["concepts/A.md", "concepts/A__doc2__ch2__1.md"],
            result_name="A",
            frontmatter={"category": "核心概念", "aliases": ["alpha"]},
            body="# A\n\nMerged definition\n",
        )

        assert result.status == "applied"
        merged = vault.read_page("concepts/A.md")
        assert merged.frontmatter["status"] == "active"
        assert merged.frontmatter["merge_decision"] == "merge_same_name_A"
        assert merged.frontmatter["merged_from"] == [
            "concepts/A.md",
            "concepts/A__doc2__ch2__1.md",
        ]
        assert len(merged.frontmatter["sources"]) == 2

        archived = vault.read_page("archive/concepts/merge_same_name_A/A__doc2__ch2__1.md")
        assert archived.frontmatter["status"] == "archived"
        assert archived.frontmatter["merged_into"] == "concepts/A.md"

        chapter = vault.read_page("textbooks/book/chapter.md")
        assert "[[A|second version]]" in chapter.body

        decision = vault.read_page("decisions/merge/merge_same_name_A.md")
        assert decision.frontmatter["status"] == "applied"
        assert "[[A__doc2__ch2__1]]" in decision.body

    def test_execute_invalid_payload_does_not_move_files(
        self, vault: VaultService, merge_service: MergeService
    ) -> None:
        write_duplicate_concepts(vault)
        merge_service.scan_same_name_candidates()

        with pytest.raises(MergeValidationError):
            merge_service.execute_merge(
                decision_id="merge_same_name_A",
                affected_nodes=["concepts/A.md", "concepts/A__doc2__ch2__1.md"],
                result_name="A",
                frontmatter={},
                body="",
            )

        assert vault.read_page("concepts/A__doc2__ch2__1.md").frontmatter["status"] == "active"
        decision = vault.read_page("decisions/merge/merge_same_name_A.md")
        assert decision.frontmatter["status"] == "candidate"

    def test_execute_result_path_conflict_requires_conflict_node(
        self, vault: VaultService, merge_service: MergeService
    ) -> None:
        vault.write_page(
            "concepts/A.md",
            {"canonical_name": "A", "status": "active"},
            "# A",
        )
        vault.write_page(
            "concepts/B.md",
            {"canonical_name": "B", "status": "active"},
            "# B",
        )
        vault.write_page(
            "concepts/C.md",
            {"canonical_name": "C", "status": "active"},
            "# C",
        )
        merge_service.create_or_update_candidate(
            affected_nodes=["concepts/A.md", "concepts/B.md"],
            result_name="C",
            reason_summary="manual candidate",
        )

        with pytest.raises(MergeConflictError):
            merge_service.execute_merge(
                decision_id="merge_manual_C",
                affected_nodes=["concepts/A.md", "concepts/B.md"],
                result_name="C",
                frontmatter={},
                body="# C\n\nMerged",
            )


class TestMergeGraphInteraction:
    def test_graph_and_search_ignore_archived_concepts(
        self, vault: VaultService, merge_service: MergeService
    ) -> None:
        write_duplicate_concepts(vault)
        merge_service.scan_same_name_candidates()
        merge_service.execute_merge(
            decision_id="merge_same_name_A",
            affected_nodes=["concepts/A.md", "concepts/A__doc2__ch2__1.md"],
            result_name="A",
            frontmatter={},
            body="# A\n\nMerged definition",
        )

        builder = GraphBuilder(vault)
        view = builder.build_graph_view()
        node_names = {node["name"] for node in view["nodes"]}
        assert node_names == {"A"}

        results = builder.search_nodes("doc2")
        assert results == []
