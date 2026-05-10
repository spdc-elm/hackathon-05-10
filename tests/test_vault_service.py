"""Tests for vault service CRUD and wikilink scanning."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.services.vault import VaultService


@pytest.fixture
def vault_dir():
    with TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def vault(vault_dir: Path) -> VaultService:
    svc = VaultService(vault_dir)
    svc.ensure_structure()
    return svc


class TestVaultCRUD:
    def test_write_and_read_page(self, vault: VaultService) -> None:
        vault.write_page("concepts/test.md", {"id": "n1", "category": "核心概念"}, "# Test\n\nHello")
        page = vault.read_page("concepts/test.md")
        assert page.frontmatter["id"] == "n1"
        assert page.frontmatter["category"] == "核心概念"
        assert "# Test" in page.body

    def test_read_missing_page_raises(self, vault: VaultService) -> None:
        with pytest.raises(FileNotFoundError):
            vault.read_page("concepts/nope.md")

    def test_list_pages_returns_all(self, vault: VaultService) -> None:
        vault.write_page("concepts/a.md", {"category": "方法"}, "# A")
        vault.write_page("concepts/b.md", {"category": "结构"}, "# B")
        vault.write_page("textbooks/x/_meta.md", {}, "# X")
        pages = vault.list_pages("concepts")
        assert len(pages) == 2
        names = {p.title for p in pages}
        assert names == {"a", "b"}

    def test_list_pages_category(self, vault: VaultService) -> None:
        vault.write_page("concepts/c.md", {"category": "过程"}, "# C")
        pages = vault.list_pages("concepts")
        assert pages[0].category == "过程"

    def test_delete_page(self, vault: VaultService) -> None:
        vault.write_page("concepts/del.md", {}, "# Del")
        assert vault.delete_page("concepts/del.md") is True
        assert vault.delete_page("concepts/del.md") is False

    def test_frontmatter_with_aliases(self, vault: VaultService) -> None:
        vault.write_page(
            "concepts/炎症.md",
            {"id": "n1", "aliases": ["inflammation", "炎性反应"]},
            "# 炎症\n\n定义",
        )
        page = vault.read_page("concepts/炎症.md")
        assert page.frontmatter["aliases"] == ["inflammation", "炎性反应"]


class TestVaultWikilinks:
    def test_extract_wikilinks_from_body(self, vault: VaultService) -> None:
        body = "## 关系\n\n- 前置依赖: [[细胞损伤]]\n- 包含: [[急性炎症]], [[慢性炎症]]"
        vault.write_page("concepts/炎症.md", {}, body)
        page = vault.read_page("concepts/炎症.md")
        assert page.wikilinks == ["细胞损伤", "急性炎症", "慢性炎症"]

    def test_no_duplicates_in_wikilinks(self, vault: VaultService) -> None:
        body = "See [[A]] and [[B]] and also [[A]] again"
        vault.write_page("concepts/test.md", {}, body)
        page = vault.read_page("concepts/test.md")
        assert page.wikilinks == ["A", "B"]

    def test_scan_all_wikilinks(self, vault: VaultService) -> None:
        vault.write_page("concepts/A.md", {}, "Links to [[B]] and [[C]]")
        vault.write_page("concepts/B.md", {}, "Links to [[A]]")
        vault.write_page("concepts/C.md", {}, "No links here")
        adj = vault.scan_all_wikilinks()
        assert adj["A"] == ["B", "C"]
        assert adj["B"] == ["A"]
        assert adj["C"] == []

    def test_scan_empty_vault(self, vault: VaultService) -> None:
        assert vault.scan_all_wikilinks() == {}

    def test_scan_ignores_textbook_pages(self, vault: VaultService) -> None:
        vault.write_page("textbooks/book/ch1.md", {}, "Has [[link]]")
        vault.write_page("concepts/real.md", {}, "Has [[other]]")
        adj = vault.scan_all_wikilinks()
        assert "ch1" not in adj
        assert adj["real"] == ["other"]
