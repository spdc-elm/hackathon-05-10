"""Markdown document parser."""

from __future__ import annotations

import re
from pathlib import Path

from .base import AssetReference, DocumentParser, ParsedChapter, ParsedDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
FRONTMATTER_RE = re.compile(r"^---\s*$")
TITLE_FRONTMATTER_RE = re.compile(r'^title:\s*["\']?(.*?)["\']?\s*$')
CHAPTER_TITLE_RE = re.compile(
    r"^(?:第\s*[一二三四五六七八九十百千万\d]+\s*章\b|Chapter\s+\d+\b)",
    re.IGNORECASE,
)


class MarkdownParser(DocumentParser):
    """Parse Markdown into contest-style chapters.

    The parser treats the shallowest heading level in the file as the chapter
    level. Lower-level headings stay inside chapter content. Image references
    are recorded as assets and removed from textual content so they do not
    pollute downstream graph extraction or RAG chunks.
    """

    format = "markdown"

    def parse(self, path: str | Path, *, textbook_id: str | None = None) -> ParsedDocument:
        source = Path(path)
        raw_text = source.read_text(encoding="utf-8")
        lines = raw_text.splitlines()
        frontmatter, body_start_idx = self._extract_frontmatter(lines)
        title_from_frontmatter = self._extract_title_from_frontmatter(frontmatter)

        body_lines = lines[body_start_idx:]
        headings = self._find_headings(body_lines, body_start_idx)
        title = title_from_frontmatter or (headings[0]["title"] if headings else source.stem)
        document_id = textbook_id or self._default_textbook_id(source)

        if not headings:
            content, assets = self._clean_content(body_lines, body_start_idx + 1)
            chapter = ParsedChapter(
                chapter_id="ch_001",
                title=title,
                page_start=None,
                page_end=None,
                level=None,
                line_start=body_start_idx + 1,
                line_end=len(lines),
                content=content,
                char_count=len(content),
                assets=assets,
            )
            return ParsedDocument(
                textbook_id=document_id,
                filename=source.name,
                title=title,
                total_pages=None,
                total_chars=chapter.char_count,
                chapters=[chapter],
                format=self.format,
                source_path=str(source),
            )

        chapter_headings = self._select_chapter_headings(headings)
        chapters: list[ParsedChapter] = []

        for idx, heading in enumerate(chapter_headings):
            start_body_idx = heading["body_idx"] + 1
            end_body_idx = (
                chapter_headings[idx + 1]["body_idx"]
                if idx + 1 < len(chapter_headings)
                else len(body_lines)
            )
            chapter_lines = body_lines[start_body_idx:end_body_idx]
            content, assets = self._clean_content(chapter_lines, body_start_idx + start_body_idx + 1)
            line_start = body_start_idx + heading["body_idx"] + 1
            line_end = body_start_idx + end_body_idx
            chapters.append(
                ParsedChapter(
                    chapter_id=f"ch_{idx + 1:03d}",
                    title=heading["title"],
                    page_start=None,
                    page_end=None,
                    level=heading["level"],
                    line_start=line_start,
                    line_end=line_end,
                    content=content,
                    char_count=len(content),
                    assets=assets,
                )
            )

        return ParsedDocument(
            textbook_id=document_id,
            filename=source.name,
            title=title,
            total_pages=None,
            total_chars=sum(chapter.char_count for chapter in chapters),
            chapters=chapters,
            format=self.format,
            source_path=str(source),
        )

    def _extract_frontmatter(self, lines: list[str]) -> tuple[list[str], int]:
        if not lines or not FRONTMATTER_RE.match(lines[0]):
            return [], 0

        for idx in range(1, len(lines)):
            if FRONTMATTER_RE.match(lines[idx]):
                return lines[1:idx], idx + 1

        return [], 0

    def _extract_title_from_frontmatter(self, frontmatter: list[str]) -> str | None:
        for line in frontmatter:
            match = TITLE_FRONTMATTER_RE.match(line.strip())
            if match:
                title = match.group(1).strip()
                if title:
                    return title
        return None

    def _find_headings(self, lines: list[str], source_offset: int) -> list[dict[str, int | str]]:
        headings: list[dict[str, int | str]] = []
        in_fence = False

        for body_idx, line in enumerate(lines):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            match = HEADING_RE.match(line)
            if not match:
                continue

            headings.append(
                {
                    "body_idx": body_idx,
                    "line": source_offset + body_idx + 1,
                    "level": len(match.group(1)),
                    "title": match.group(2).strip(),
                }
            )

        return headings

    def _select_chapter_headings(
        self,
        headings: list[dict[str, int | str]],
    ) -> list[dict[str, int | str]]:
        chapter_candidates = [
            heading
            for heading in headings
            if CHAPTER_TITLE_RE.match(str(heading["title"]))
        ]
        if chapter_candidates:
            chapter_level = min(int(item["level"]) for item in chapter_candidates)
            return [
                item
                for item in chapter_candidates
                if int(item["level"]) == chapter_level
            ]

        shallowest_level = min(int(item["level"]) for item in headings)
        shallowest = [item for item in headings if int(item["level"]) == shallowest_level]
        if (
            len(shallowest) == 1
            and int(shallowest[0]["body_idx"]) == 0
            and any(int(item["level"]) > shallowest_level for item in headings)
        ):
            next_level = min(
                int(item["level"])
                for item in headings
                if int(item["level"]) > shallowest_level
            )
            return [item for item in headings if int(item["level"]) == next_level]

        return shallowest

    def _clean_content(self, lines: list[str], first_line_number: int) -> tuple[str, list[AssetReference]]:
        cleaned_lines: list[str] = []
        assets: list[AssetReference] = []

        for idx, line in enumerate(lines):
            source_line = first_line_number + idx

            def replace_image(match: re.Match[str]) -> str:
                label = match.group(1).strip()
                asset_path = match.group(2).strip()
                assets.append(
                    AssetReference(
                        kind="image",
                        label=label,
                        path=asset_path,
                        line=source_line,
                    )
                )
                return ""

            line_without_images = IMAGE_RE.sub(replace_image, line).rstrip()
            cleaned_lines.append(line_without_images)

        content = "\n".join(cleaned_lines).strip()
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content, assets

    def _default_textbook_id(self, source: Path) -> str:
        safe_stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", source.stem).strip("_")
        return safe_stem or "document"
