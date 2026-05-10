"""Tests for the PDF parser.

Uses a synthetic PDF fixture built with PyMuPDF to avoid depending on
large textbook files in CI.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
import pytest

from app.parsers.pdf import PdfParser


# ---------------------------------------------------------------------------
# Fixture: synthetic PDF with bookmarks
# ---------------------------------------------------------------------------


CJK = "china-s"


def _create_bookmarked_pdf(path: Path) -> None:
    """Create a small PDF with 2 chapters via bookmarks."""
    doc = pymupdf.open()

    # Front matter page
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "封面页", fontsize=12, fontname=CJK)
    page.insert_text((72, 130), "本书简介", fontsize=12, fontname=CJK)

    # Chapter 1 - two pages
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第一章  绪论", fontsize=14, fontname=CJK)
    page.insert_text((72, 100), "生理学是研究生命活动规律的科学。", fontsize=11, fontname=CJK)
    page.insert_text((72, 120), "本章介绍基本概念。", fontsize=11, fontname=CJK)

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第一章  绪论", fontsize=11, fontname=CJK)
    page.insert_text((72, 100), "生命活动的基本特征包括新陈代谢。", fontsize=11, fontname=CJK)

    # Chapter 2 - two pages
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第二章  细胞", fontsize=14, fontname=CJK)
    page.insert_text((72, 100), "细胞是生命的基本单位。", fontsize=11, fontname=CJK)
    page.insert_text((72, 120), "细胞膜具有选择透过性。", fontsize=11, fontname=CJK)

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第二章  细胞", fontsize=11, fontname=CJK)
    page.insert_text((72, 100), "细胞内有多种细胞器参与物质代谢。", fontsize=11, fontname=CJK)

    # Add bookmarks (TOC)
    toc = [
        [1, "封面页", 1],
        [1, "第一章　绪论", 2],
        [1, "第二章　细胞", 4],
    ]
    doc.set_toc(toc)
    doc.save(str(path))
    doc.close()


def _create_no_bookmark_pdf(path: Path) -> None:
    """Create a PDF without bookmarks, relying on page-scan fallback."""
    doc = pymupdf.open()

    # TOC page (not a real structured TOC, just content)
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "目录", fontsize=14, fontname=CJK)
    page.insert_text((72, 100), "绪论 .......................... 1", fontsize=11, fontname=CJK)

    # Chapter pages with headers
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第一章  基础知识", fontsize=14, fontname=CJK)
    page.insert_text((72, 100), "本章讲解基础知识的核心内容。", fontsize=11, fontname=CJK)

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第一章  基础知识", fontsize=11, fontname=CJK)
    page.insert_text((72, 100), "基础知识的第二页内容继续。", fontsize=11, fontname=CJK)

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 60), "第二章  进阶方法", fontsize=14, fontname=CJK)
    page.insert_text((72, 100), "进阶方法是在基础之上的拓展。", fontsize=11, fontname=CJK)

    # No bookmarks set
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# Tests: Bookmark-based chapter detection
# ---------------------------------------------------------------------------


class TestPdfParserBookmarks:
    def test_parses_chapters_from_bookmarks(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert result.format == "pdf"
        assert result.total_pages == 5
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "第一章　绪论"
        assert result.chapters[1].title == "第二章　细胞"

    def test_chapter_page_ranges(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        ch1 = result.chapters[0]
        ch2 = result.chapters[1]
        assert ch1.page_start == 2
        assert ch1.page_end == 3
        assert ch2.page_start == 4
        assert ch2.page_end == 5

    def test_skips_front_matter_bookmarks(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        titles = [ch.title for ch in result.chapters]
        assert "封面页" not in titles

    def test_chapter_content_extracted(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert "生理学" in result.chapters[0].content or "生命活动" in result.chapters[0].content
        assert "细胞" in result.chapters[1].content

    def test_filters_repeated_chapter_headers(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        # The chapter title appears as a page header on page 3 — should be filtered
        content = result.chapters[0].content
        # Should not have duplicate "第一章  绪论" lines in the content body
        occurrences = content.count("第一章")
        assert occurrences <= 1

    def test_textbook_id_from_argument(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path, textbook_id="book_03")

        assert result.textbook_id == "book_03"

    def test_textbook_id_from_filename(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "03_生理学.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert "生理学" in result.textbook_id or "03" in result.textbook_id

    def test_to_dict_serializable(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        data = result.to_dict()
        assert data["format"] == "pdf"
        assert data["total_pages"] == 5
        assert len(data["chapters"]) == 2
        assert isinstance(data["chapters"][0]["page_start"], int)


# ---------------------------------------------------------------------------
# Tests: Page-scan fallback
# ---------------------------------------------------------------------------


class TestPdfParserPageScan:
    def test_detects_chapters_without_bookmarks(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "no_bookmarks.pdf"
            _create_no_bookmark_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert len(result.chapters) >= 2
        titles = [ch.title for ch in result.chapters]
        assert any("第一章" in t for t in titles)
        assert any("第二章" in t for t in titles)

    def test_page_scan_content_correct(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "no_bookmarks.pdf"
            _create_no_bookmark_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        ch1 = next(ch for ch in result.chapters if "第一章" in ch.title)
        assert "基础知识" in ch1.content or "核心内容" in ch1.content


# ---------------------------------------------------------------------------
# Tests: Text extraction and cleaning
# ---------------------------------------------------------------------------


class TestPdfTextExtraction:
    def test_total_chars_equals_sum_of_chapters(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert result.total_chars == sum(ch.char_count for ch in result.chapters)

    def test_no_excessive_blank_lines(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "bookmarked.pdf"
            _create_bookmarked_pdf(pdf_path)

            parser = PdfParser()
            result = parser.parse(pdf_path)

        for ch in result.chapters:
            assert "\n\n\n" not in ch.content

    def test_single_page_pdf_produces_one_chapter(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "single.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 100), "这是一个单页文档的内容。", fontsize=12, fontname=CJK)
            doc.save(str(pdf_path))
            doc.close()

            parser = PdfParser()
            result = parser.parse(pdf_path)

        assert len(result.chapters) == 1
        assert result.total_pages == 1
        assert "单页文档" in result.chapters[0].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
