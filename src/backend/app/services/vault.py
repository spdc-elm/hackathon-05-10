"""Obsidian-compatible vault service for MD file management."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_DELIMITER = re.compile(r"^---\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class VaultPage:
    """A single MD page in the vault."""

    path: str
    frontmatter: dict[str, Any]
    body: str
    wikilinks: list[str]


@dataclass(frozen=True)
class VaultPageSummary:
    """Lightweight listing entry."""

    path: str
    title: str
    category: str


class VaultService:
    """Reads/writes Obsidian-flavored MD files in a vault directory."""

    def __init__(self, vault_root: str | Path) -> None:
        self.root = Path(vault_root)

    def ensure_structure(self) -> None:
        (self.root / "textbooks").mkdir(parents=True, exist_ok=True)
        (self.root / "concepts").mkdir(parents=True, exist_ok=True)
        (self.root / "decisions" / "merge").mkdir(parents=True, exist_ok=True)
        (self.root / "archive" / "concepts").mkdir(parents=True, exist_ok=True)

    def list_pages(self, subdir: str | None = None) -> list[VaultPageSummary]:
        base = self.root / subdir if subdir else self.root
        if not base.exists():
            return []

        pages: list[VaultPageSummary] = []
        for md_file in sorted(base.rglob("*.md")):
            relative = str(md_file.relative_to(self.root))
            fm, _ = self._parse_frontmatter(md_file.read_text(encoding="utf-8"))
            title = fm.get("title") or fm.get("canonical_name") or md_file.stem
            category = fm.get("category", "")
            pages.append(VaultPageSummary(path=relative, title=title, category=category))
        return pages

    def read_page(self, relative_path: str) -> VaultPage:
        full_path = self.root / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"Vault page not found: {relative_path}")
        content = full_path.read_text(encoding="utf-8")
        fm, body = self._parse_frontmatter(content)
        wikilinks = self._extract_wikilinks(body)
        return VaultPage(path=relative_path, frontmatter=fm, body=body, wikilinks=wikilinks)

    def write_page(self, relative_path: str, frontmatter: dict[str, Any], body: str) -> None:
        full_path = self.root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._render_page(frontmatter, body)
        full_path.write_text(content, encoding="utf-8")

    def delete_page(self, relative_path: str) -> bool:
        full_path = self.root / relative_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def scan_all_wikilinks(self) -> dict[str, list[str]]:
        """Return {page_stem: [linked_page_stems]} for all concept pages."""
        adjacency: dict[str, list[str]] = {}
        concepts_dir = self.root / "concepts"
        if not concepts_dir.exists():
            return adjacency

        for md_file in concepts_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            _, body = self._parse_frontmatter(content)
            links = self._extract_wikilinks(body)
            adjacency[md_file.stem] = links
        return adjacency

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        lines = content.split("\n")
        if not lines or not FRONTMATTER_DELIMITER.match(lines[0]):
            return {}, content

        end_idx = None
        for i in range(1, len(lines)):
            if FRONTMATTER_DELIMITER.match(lines[i]):
                end_idx = i
                break

        if end_idx is None:
            return {}, content

        yaml_text = "\n".join(lines[1:end_idx])
        try:
            fm = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError:
            fm = {}

        body = "\n".join(lines[end_idx + 1:]).strip()
        return fm if isinstance(fm, dict) else {}, body

    def _extract_wikilinks(self, text: str) -> list[str]:
        links: list[str] = []
        for raw_link in WIKILINK_RE.findall(text):
            target = raw_link.split("|", 1)[0].strip()
            if target:
                links.append(target)
        return list(dict.fromkeys(links))

    def _render_page(self, frontmatter: dict[str, Any], body: str) -> str:
        yaml_text = yaml.dump(
            frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
        ).strip()
        return f"---\n{yaml_text}\n---\n\n{body}\n"
