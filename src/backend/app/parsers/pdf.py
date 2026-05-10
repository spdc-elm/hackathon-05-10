"""PDF document parser with cascading chapter detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .base import DocumentParser, ParsedChapter, ParsedDocument

SKIP_TITLES = frozenset([
    "封面", "封面页", "书名", "书名页", "版权", "版权页",
    "编委", "编委名单", "新形态", "序言", "修订说明",
    "简介", "主审简介", "主编简介", "副主编简介",
    "前言", "目录", "封底", "教材修订说明",
    "新形态教材使用说明", "主审", "主编", "副主编",
])

CHAPTER_RE = re.compile(
    r"^第[一二三四五六七八九十百千万\d]+章",
)

PIAN_RE = re.compile(
    r"^(上篇|下篇|中篇|第[一二三四五六七八九十百\d]+篇)",
)

CN_CHAPTER_FULL_RE = re.compile(
    r"第([一二三四五六七八九十百千万\d]+)章",
)

PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")

BOILERPLATE_RE = re.compile(
    r"^(本章数字资源|本章思维导图|数字资源|学习目标)",
)


@dataclass(slots=True)
class ChapterSpan:
    title: str
    page_start: int  # 1-indexed
    page_end: int    # 1-indexed, inclusive


class PdfParser(DocumentParser):
    """Parse PDF textbooks into chapter-level structured data.

    Uses a cascading strategy for chapter detection:
    A) PDF bookmarks (most reliable)
    B) Text-based TOC page parsing
    C) Regex scan of page headers
    """

    format = "pdf"

    def parse(self, path: str | Path, *, textbook_id: str | None = None) -> ParsedDocument:
        source = Path(path)
        doc = pymupdf.open(str(source))
        try:
            total_pages = len(doc)
            chapters = self._detect_chapters(doc)

            if not chapters:
                content = self._extract_pages_text(doc, 1, total_pages, chapter_title=None)
                parsed_chapters = [
                    ParsedChapter(
                        chapter_id="ch_001",
                        title=source.stem,
                        page_start=1,
                        page_end=total_pages,
                        content=content,
                        char_count=len(content),
                    )
                ]
            else:
                parsed_chapters = []
                for idx, span in enumerate(chapters):
                    content = self._extract_pages_text(
                        doc, span.page_start, span.page_end,
                        chapter_title=span.title,
                    )
                    parsed_chapters.append(
                        ParsedChapter(
                            chapter_id=f"ch_{idx + 1:03d}",
                            title=span.title,
                            page_start=span.page_start,
                            page_end=span.page_end,
                            content=content,
                            char_count=len(content),
                        )
                    )

            document_id = textbook_id or self._default_textbook_id(source)
            return ParsedDocument(
                textbook_id=document_id,
                filename=source.name,
                title=self._infer_title(chapters, source),
                total_pages=total_pages,
                total_chars=sum(ch.char_count for ch in parsed_chapters),
                chapters=parsed_chapters,
                format=self.format,
                source_path=str(source),
            )
        finally:
            doc.close()

    # ------------------------------------------------------------------
    # Chapter detection cascade
    # ------------------------------------------------------------------

    def _detect_chapters(self, doc: pymupdf.Document) -> list[ChapterSpan]:
        total_pages = len(doc)

        # Stage A: bookmarks
        chapters = self._chapters_from_bookmarks(doc)
        if chapters:
            return chapters

        # Stage B: text TOC
        chapters = self._chapters_from_text_toc(doc)
        if chapters:
            return chapters

        # Stage C: regex page scan
        chapters = self._chapters_from_page_scan(doc)
        if chapters:
            return chapters

        return []

    # ------------------------------------------------------------------
    # Stage A: Bookmarks
    # ------------------------------------------------------------------

    def _chapters_from_bookmarks(self, doc: pymupdf.Document) -> list[ChapterSpan]:
        toc = doc.get_toc()
        if not toc:
            return []

        total_pages = len(doc)

        # Collect level-1 content entries
        level1 = []
        for level, title, page in toc:
            if level == 1 and page > 0:
                title = _clean_title(title)
                if _is_skip_title(title):
                    continue
                level1.append((title, page))

        if not level1:
            return []

        # Check if level-1 is too coarse ("篇" divisions)
        pian_count = sum(1 for title, _ in level1 if PIAN_RE.match(title))
        use_level2 = pian_count >= len(level1) * 0.3

        if use_level2:
            chapters = self._promote_level2_chapters(toc)
            if chapters:
                return self._spans_from_entries(chapters, total_pages)

        return self._spans_from_entries(level1, total_pages)

    def _promote_level2_chapters(
        self, toc: list[list],
    ) -> list[tuple[str, int]]:
        """When L1 entries are 'pian' divisions, use L2 chapter entries."""
        chapters: list[tuple[str, int]] = []

        # Include L1 绪论 if present
        for level, title, page in toc:
            if level == 1 and page > 0:
                title = _clean_title(title)
                if "绪论" in title and not _is_skip_title(title):
                    chapters.append((title, page))

        # Include L2 chapter entries
        for level, title, page in toc:
            if level == 2 and page > 0:
                title = _clean_title(title)
                if _is_skip_title(title):
                    continue
                if CHAPTER_RE.match(title) or "绪论" in title:
                    chapters.append((title, page))

        chapters.sort(key=lambda x: x[1])
        # Deduplicate 绪论 if it appears in both L1 and L2
        seen_pages: set[int] = set()
        deduped: list[tuple[str, int]] = []
        for title, page in chapters:
            if page not in seen_pages:
                seen_pages.add(page)
                deduped.append((title, page))
        return deduped

    def _spans_from_entries(
        self,
        entries: list[tuple[str, int]],
        total_pages: int,
    ) -> list[ChapterSpan]:
        spans: list[ChapterSpan] = []
        for i, (title, start) in enumerate(entries):
            end = entries[i + 1][1] - 1 if i + 1 < len(entries) else total_pages
            end = max(start, end)
            spans.append(ChapterSpan(title=title, page_start=start, page_end=end))
        return spans

    # ------------------------------------------------------------------
    # Stage B: Text-TOC Parsing
    # ------------------------------------------------------------------

    def _chapters_from_text_toc(self, doc: pymupdf.Document) -> list[ChapterSpan]:
        total_pages = len(doc)

        toc_text = self._find_toc_text(doc)
        if not toc_text:
            return []

        entries = self._parse_toc_entries(toc_text)
        if not entries:
            return []

        offset = self._calculate_page_offset(doc, entries)

        # Apply offset and build spans
        spans: list[ChapterSpan] = []
        for i, (title, printed_page) in enumerate(entries):
            actual_page = printed_page + offset
            actual_page = max(1, min(actual_page, total_pages))

            if i + 1 < len(entries):
                next_actual = entries[i + 1][1] + offset
                end_page = max(actual_page, min(next_actual - 1, total_pages))
            else:
                end_page = total_pages

            spans.append(ChapterSpan(title=title, page_start=actual_page, page_end=end_page))

        # Validate: check that at least one chapter title appears on its target page
        if not self._validate_spans(doc, spans):
            return []

        return spans

    def _find_toc_text(self, doc: pymupdf.Document) -> str:
        """Find and collect text from TOC pages."""
        total_pages = len(doc)
        toc_text = ""

        for p in range(min(25, total_pages)):
            text = doc[p].get_text()
            if "目录" in text[:80]:
                for tp in range(p, min(p + 15, total_pages)):
                    page_text = doc[tp].get_text()
                    lines = page_text.strip().split("\n")
                    # Stop when we hit dense content pages (not TOC)
                    if tp > p + 1:
                        # A TOC page has many lines with dot-leaders or short entries;
                        # a content page has long prose lines without dots
                        content_lines = [
                            l for l in lines
                            if len(l) > 80
                            and "\t" not in l
                            and l.count("·") < 3
                            and l.count("…") < 3
                            and l.count(". ") < 10
                            and l.count("�") < 3
                        ]
                        if len(content_lines) > 5:
                            break
                    toc_text += page_text + "\n"
                break

        return toc_text

    def _parse_toc_entries(self, toc_text: str) -> list[tuple[str, int]]:
        """Extract chapter titles and page numbers from TOC text."""
        # Clean control chars and dot leaders
        clean = re.sub(r"[\x00-\x09\x0b\x0c\x0e-\x1f]", "", toc_text)
        clean = re.sub(r"[·…��]+", "", clean)

        entries: list[tuple[str, int]] = []

        # Look for 绪论
        intro_match = re.search(r"绪论\s*\n\s*(\d+)", clean)
        if intro_match:
            entries.append(("绪论", int(intro_match.group(1))))

        # Pattern: 第X章\n章名\n页码  OR  第X章 章名\n...页码
        # Handle multi-line chapter entries
        pattern = re.compile(
            r"(第[一二三四五六七八九十百]+章)\s*\n([^\n]+?)\n\s*(\d+)",
            re.MULTILINE,
        )
        for match in pattern.finditer(clean):
            chapter_num = match.group(1)
            chapter_name = match.group(2).strip()
            page_num = int(match.group(3))
            if chapter_name and not chapter_name.startswith("第"):
                title = f"{chapter_num}　{chapter_name}"
                entries.append((title, page_num))

        # Also try single-line pattern: 第X章 章名 ... 页码
        pattern2 = re.compile(
            r"(第[一二三四五六七八九十百]+章)\s+([^\n\d]+?)\s+(\d+)\s*$",
            re.MULTILINE,
        )
        seen_chapters = {e[0].split("　")[0].split(" ")[0] for e in entries}
        for match in pattern2.finditer(clean):
            chapter_num = match.group(1)
            if chapter_num in seen_chapters:
                continue
            chapter_name = match.group(2).strip()
            page_num = int(match.group(3))
            if chapter_name and len(chapter_name) < 30:
                title = f"{chapter_num}　{chapter_name}"
                entries.append((title, page_num))
                seen_chapters.add(chapter_num)

        entries.sort(key=lambda x: x[1])
        return entries

    def _calculate_page_offset(
        self,
        doc: pymupdf.Document,
        entries: list[tuple[str, int]],
    ) -> int:
        """Determine the offset between printed page numbers and PDF page indices."""
        total_pages = len(doc)

        # Find a good search entry (prefer a named chapter, not just 绪论)
        search_entry = None
        for title, page in entries:
            if CN_CHAPTER_FULL_RE.search(title):
                search_entry = (title, page)
                break
        if not search_entry and entries:
            search_entry = entries[0]
        if not search_entry:
            return 0

        search_title, printed_page = search_entry
        # Extract chapter number text for searching
        search_text = re.sub(r"[\s　　]+", "", search_title)[:8]

        # Search in content pages (skip front matter), but also skip TOC pages
        # A content page has prose text after the header; a TOC page has dot-leaders
        for p in range(10, min(60, total_pages)):
            text = doc[p].get_text()
            text_normalized = re.sub(r"[\s　　]+", "", text[:400])
            if search_text not in text_normalized:
                continue
            # Verify this is a content page, not a TOC page
            if self._is_toc_page(text):
                continue
            return p + 1 - printed_page

        # Broader search from the beginning
        for p in range(5, min(40, total_pages)):
            text = doc[p].get_text()
            text_normalized = re.sub(r"[\s　　]+", "", text[:400])
            if search_text not in text_normalized:
                continue
            if self._is_toc_page(text):
                continue
            return p + 1 - printed_page

        return 0

    def _is_toc_page(self, text: str) -> bool:
        """Check if a page looks like a table-of-contents page."""
        lines = text.strip().split("\n")
        dot_lines = sum(
            1 for l in lines
            if (l.count(".") > 10
                or l.count("·") > 5
                or l.count("…") > 3
                or l.count("�") > 10
                or l.count(". ") > 8)
        )
        return dot_lines > 3

    def _validate_spans(self, doc: pymupdf.Document, spans: list[ChapterSpan]) -> bool:
        """Check that at least one chapter title appears on its target page."""
        validated = 0
        for span in spans[:5]:
            page_idx = span.page_start - 1
            if page_idx < 0 or page_idx >= len(doc):
                continue
            text = doc[page_idx].get_text()[:500]
            # Normalize for comparison
            title_key = re.sub(r"[\s　　]+", "", span.title)[:6]
            text_normalized = re.sub(r"[\s　　]+", "", text)
            if title_key in text_normalized:
                validated += 1

        return validated > 0

    # ------------------------------------------------------------------
    # Stage C: Regex Page Scan
    # ------------------------------------------------------------------

    def _chapters_from_page_scan(self, doc: pymupdf.Document) -> list[ChapterSpan]:
        """Scan page headers for chapter title patterns."""
        total_pages = len(doc)
        chapter_pages: list[tuple[str, int]] = []
        last_title: str | None = None

        for page_idx in range(total_pages):
            text = doc[page_idx].get_text()[:300]
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Look at first few non-empty lines for chapter pattern
            for line in lines[:3]:
                # Skip page numbers
                if PAGE_NUMBER_RE.match(line):
                    continue
                match = CHAPTER_RE.match(line)
                if match:
                    title = _clean_title(line.split("\n")[0])
                    if title != last_title:
                        chapter_pages.append((title, page_idx + 1))
                        last_title = title
                    break
                # Also detect 绪论 as a standalone chapter header
                if line == "绪论" and last_title != "绪论":
                    chapter_pages.append(("绪论", page_idx + 1))
                    last_title = "绪论"
                break

        if not chapter_pages:
            return []

        return self._spans_from_entries(chapter_pages, total_pages)

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_pages_text(
        self,
        doc: pymupdf.Document,
        start_page: int,
        end_page: int,
        *,
        chapter_title: str | None,
    ) -> str:
        """Extract and clean text from a range of pages."""
        parts: list[str] = []
        header_pattern = self._make_header_pattern(chapter_title)

        for page_idx in range(start_page - 1, end_page):
            if page_idx < 0 or page_idx >= len(doc):
                continue
            page_text = doc[page_idx].get_text()
            cleaned = self._clean_page_text(page_text, header_pattern)
            if cleaned:
                parts.append(cleaned)

        content = "\n\n".join(parts)
        content = _normalize_whitespace(content)
        return content

    def _make_header_pattern(self, chapter_title: str | None) -> re.Pattern[str] | None:
        if not chapter_title:
            return None
        title_chars = re.sub(r"[\s　　]+", "", chapter_title)
        if not title_chars:
            return None
        ch_match = CN_CHAPTER_FULL_RE.search(title_chars)
        if ch_match:
            pattern_text = re.escape(ch_match.group(0))
        else:
            pattern_text = re.escape(title_chars[:6])
        # Also consume an optional short continuation line (≤3 chars) that is
        # a fragment of the title split across lines by PDF text extraction.
        return re.compile(
            r"^[ \t]*" + pattern_text + r"[^\n]*(?:\n[^\n]{1,3}$)?",
            re.MULTILINE,
        )

    def _clean_page_text(
        self,
        text: str,
        header_pattern: re.Pattern[str] | None,
    ) -> str:
        lines = text.split("\n")
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned.append("")
                continue
            # Skip standalone page numbers
            if PAGE_NUMBER_RE.match(stripped):
                continue
            # Skip boilerplate
            if BOILERPLATE_RE.match(stripped):
                continue
            # Join short orphan fragments (≤2 chars) back to the previous line.
            # PDF extraction often splits CJK headings like "概述" into "概\n述".
            if len(stripped) <= 2 and cleaned and cleaned[-1]:
                cleaned[-1] += stripped
                continue
            cleaned.append(stripped)

        result = "\n".join(cleaned)

        # Remove header lines (chapter title repeated at top of page)
        if header_pattern:
            result = header_pattern.sub("", result, count=1)

        return result.strip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _infer_title(self, chapters: list[ChapterSpan], source: Path) -> str:
        if not chapters:
            return source.stem
        # Use the source filename stem as title (it's typically "03_生理学")
        stem = source.stem
        # Strip leading number prefix like "03_"
        cleaned = re.sub(r"^\d+_", "", stem)
        return cleaned or stem

    def _default_textbook_id(self, source: Path) -> str:
        safe_stem = re.sub(r"[^0-9A-Za-z一-鿿]+", "_", source.stem).strip("_")
        return safe_stem or "document"


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _clean_title(title: str) -> str:
    """Remove null bytes, control chars, surrogates, and normalize whitespace."""
    title = title.replace("\x00", "").replace("\r", "").replace("\n", "")
    title = re.sub(r"[\ud800-\udfff]", "", title)
    title = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", title)
    return title.strip()


def _is_skip_title(title: str) -> bool:
    """Check if a bookmark title is front/back matter that should be skipped."""
    for skip in SKIP_TITLES:
        if skip in title:
            return True
    return False


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and strip trailing whitespace."""
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
