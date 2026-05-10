"""Integration tests for the LLM Wiki API endpoints."""

from __future__ import annotations

import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_dirs(monkeypatch):
    """Use temp directories for runtime and vault so tests don't interfere."""
    with TemporaryDirectory() as runtime, TemporaryDirectory() as vault:
        monkeypatch.setenv("RUNTIME_DIR", runtime)
        monkeypatch.setenv("VAULT_DIR", vault)
        from app.core.config import get_settings
        get_settings.cache_clear()
        yield {"runtime": runtime, "vault": vault}
        get_settings.cache_clear()


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDocumentUpload:
    def test_upload_markdown(self, client: TestClient, isolated_dirs) -> None:
        content = "# 第一章 测试\n\n这是测试内容。\n\n# 第二章 示例\n\n更多内容。"
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.md", io.BytesIO(content.encode()), "text/markdown")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "parsed"
        assert data["chapter_count"] == 2

    def test_upload_writes_to_vault(self, client: TestClient, isolated_dirs) -> None:
        content = "# Chapter 1\n\nHello world"
        client.post(
            "/api/documents/upload",
            files={"file": ("demo.md", io.BytesIO(content.encode()), "text/markdown")},
        )
        vault_dir = Path(isolated_dirs["vault"])
        textbook_files = list((vault_dir / "textbooks").rglob("*.md"))
        assert len(textbook_files) >= 1

    def test_upload_unsupported_type(self, client: TestClient) -> None:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("data.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
        )
        assert resp.status_code == 422

    def test_list_documents_after_upload(self, client: TestClient) -> None:
        content = "# Test\n\nContent"
        client.post(
            "/api/documents/upload",
            files={"file": ("test.md", io.BytesIO(content.encode()), "text/markdown")},
        )
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["filename"] == "test.md"


class TestVaultBrowse:
    def test_list_empty_vault(self, client: TestClient) -> None:
        resp = client.get("/api/vault/pages", params={"subdir": "concepts"})
        assert resp.status_code == 200
        assert resp.json()["pages"] == []

    def test_list_after_upload(self, client: TestClient) -> None:
        content = "# Chapter\n\nContent here"
        client.post(
            "/api/documents/upload",
            files={"file": ("book.md", io.BytesIO(content.encode()), "text/markdown")},
        )
        resp = client.get("/api/vault/pages", params={"subdir": "textbooks"})
        assert resp.status_code == 200
        assert len(resp.json()["pages"]) >= 1

    def test_read_page_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/vault/pages/concepts/nope.md")
        assert resp.status_code == 404


class TestGraph:
    def test_empty_graph(self, client: TestClient) -> None:
        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["view_id"] == "vault_graph"
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_graph_with_concepts(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page(
            "concepts/A.md",
            {"id": "n1", "category": "核心概念", "textbook_id": "b1"},
            "# A\n\nDef A\n\n## 关系\n\n- 前置依赖: [[B]]\n",
        )
        vault.write_page(
            "concepts/B.md",
            {"id": "n2", "category": "方法", "textbook_id": "b1"},
            "# B\n\nDef B",
        )

        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["relation_type"] == "prerequisite"

    def test_node_detail(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page(
            "concepts/炎症.md",
            {"id": "n1", "category": "核心概念"},
            "# 炎症\n\n防御反应\n\n## 原文证据\n\n> 原文\n",
        )

        resp = client.get("/api/graph/nodes/炎症")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node"]["name"] == "炎症"
        assert "content_md" in data

    def test_node_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/graph/nodes/不存在")
        assert resp.status_code == 404

    def test_search(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page("concepts/炎症.md", {"aliases": []}, "# 炎症")
        vault.write_page("concepts/免疫.md", {"aliases": []}, "# 免疫")

        resp = client.get("/api/graph/search", params={"q": "炎"})
        assert resp.status_code == 200
        matches = resp.json()["matches"]
        assert len(matches) == 1
        assert matches[0]["name"] == "炎症"

    def test_search_empty_query(self, client: TestClient) -> None:
        resp = client.get("/api/graph/search", params={"q": ""})
        assert resp.status_code == 400


class TestMergeAPI:
    def test_scan_and_read_decision(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page(
            "concepts/A.md",
            {"canonical_name": "A", "status": "active"},
            "# A",
        )
        vault.write_page(
            "concepts/A__doc2__ch1__1.md",
            {"canonical_name": "A", "status": "active"},
            "# A",
        )

        resp = client.post("/api/merge/scan")
        assert resp.status_code == 200
        decisions = resp.json()["decisions"]
        assert len(decisions) == 1
        assert decisions[0]["decision_id"] == "merge_same_name_A"

        detail_resp = client.get("/api/merge/decisions/merge_same_name_A")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["frontmatter"]["status"] == "candidate"
        assert "A__doc2__ch1__1" in detail["wikilinks"]

    def test_execute_merge_endpoint(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page(
            "concepts/A.md",
            {"canonical_name": "A", "status": "active"},
            "# A",
        )
        vault.write_page(
            "concepts/A__doc2__ch1__1.md",
            {"canonical_name": "A", "status": "active"},
            "# A",
        )
        client.post("/api/merge/scan")

        resp = client.post(
            "/api/merge/execute",
            json={
                "decision_id": "merge_same_name_A",
                "affected_nodes": ["concepts/A.md", "concepts/A__doc2__ch1__1.md"],
                "result_name": "A",
                "frontmatter": {},
                "body": "# A\n\nMerged",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"
        assert vault.read_page("concepts/A.md").frontmatter["merge_decision"] == "merge_same_name_A"

    def test_execute_invalid_payload_returns_422(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page("concepts/A.md", {"canonical_name": "A", "status": "active"}, "# A")
        vault.write_page("concepts/B.md", {"canonical_name": "A", "status": "active"}, "# B")
        client.post("/api/merge/scan")

        resp = client.post(
            "/api/merge/execute",
            json={
                "decision_id": "merge_same_name_A",
                "affected_nodes": ["concepts/A.md", "concepts/B.md"],
                "result_name": "A",
                "frontmatter": {},
                "body": "",
            },
        )

        assert resp.status_code == 422
        assert vault.read_page("concepts/B.md").frontmatter["status"] == "active"

    def test_execute_conflict_returns_409(self, client: TestClient, isolated_dirs) -> None:
        from app.services.vault import VaultService
        vault = VaultService(isolated_dirs["vault"])
        vault.ensure_structure()
        vault.write_page("concepts/A.md", {"canonical_name": "A", "status": "active"}, "# A")
        vault.write_page("concepts/B.md", {"canonical_name": "B", "status": "active"}, "# B")
        vault.write_page("concepts/C.md", {"canonical_name": "C", "status": "active"}, "# C")
        client.post(
            "/api/merge/decisions",
            json={
                "decision_id": "merge_manual_C",
                "affected_nodes": ["concepts/A.md", "concepts/B.md"],
                "result_name": "C",
                "reason_summary": "manual",
            },
        )

        resp = client.post(
            "/api/merge/execute",
            json={
                "decision_id": "merge_manual_C",
                "affected_nodes": ["concepts/A.md", "concepts/B.md"],
                "result_name": "C",
                "frontmatter": {},
                "body": "# C\n\nMerged",
            },
        )

        assert resp.status_code == 409


class TestExtractionStatus:
    def test_upload_triggers_extraction(self, client: TestClient) -> None:
        content = "# Test\n\nContent"
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("test.md", io.BytesIO(content.encode()), "text/markdown")},
        )
        data = resp.json()
        assert data["extraction_status"] == "running"
        doc_id = data["document_id"]

        status_resp = client.get(f"/api/extraction/status/{doc_id}")
        assert status_resp.status_code == 200
        # Status may be running or error (no LLM configured in test)
        assert status_resp.json()["extraction_status"] in ("running", "error", "ready")

    def test_extraction_status_unknown_doc(self, client: TestClient) -> None:
        resp = client.get("/api/extraction/status/nonexistent")
        assert resp.status_code == 200
        assert resp.json()["extraction_status"] == "none"
