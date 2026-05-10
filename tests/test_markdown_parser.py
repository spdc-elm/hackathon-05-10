from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.parsers.markdown import MarkdownParser


class MarkdownParserTest(unittest.TestCase):
    def test_parse_markdown_fixture_into_chapters(self) -> None:
        parser = MarkdownParser()
        parsed = parser.parse(Path("samples/fixtures/markdown/structured_course.md"))

        self.assertEqual(parsed.title, "示例教材")
        self.assertEqual(parsed.filename, "structured_course.md")
        self.assertEqual(parsed.format, "markdown")
        self.assertIsNone(parsed.total_pages)
        self.assertEqual(
            [chapter.title for chapter in parsed.chapters],
            ["第一章 绪论", "第二章 方法"],
        )

        first = parsed.chapters[0]
        self.assertEqual(first.chapter_id, "ch_001")
        self.assertEqual(first.level, 1)
        self.assertIsNone(first.page_start)
        self.assertIsNone(first.page_end)
        self.assertIn("第一节 背景", first.content)
        self.assertIn("# 这不是 Markdown 标题", first.content)
        self.assertNotIn("![系统结构图]", first.content)
        self.assertEqual(len(first.assets), 1)
        self.assertEqual(first.assets[0].kind, "image")
        self.assertEqual(first.assets[0].label, "系统结构图")
        self.assertEqual(first.assets[0].path, "assets/system.svg")

    def test_to_dict_is_json_serializable_shape(self) -> None:
        parser = MarkdownParser()
        parsed = parser.parse(Path("samples/fixtures/markdown/structured_course.md"))
        data = parsed.to_dict()

        self.assertEqual(data["textbook_id"], "structured_course")
        self.assertEqual(data["chapters"][0]["chapter_id"], "ch_001")
        self.assertEqual(data["chapters"][0]["assets"][0]["path"], "assets/system.svg")

    def test_prefers_chapter_headings_under_document_title(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "book.md"
            path.write_text(
                "# 示例书名\n\n"
                "总序不会被当作章节。\n\n"
                "## 第一章 基础\n\n"
                "基础正文。\n\n"
                "## 第二章 进阶\n\n"
                "进阶正文。\n",
                encoding="utf-8",
            )

            parsed = MarkdownParser().parse(path)

        self.assertEqual(parsed.title, "示例书名")
        self.assertEqual([chapter.title for chapter in parsed.chapters], ["第一章 基础", "第二章 进阶"])
        self.assertNotIn("总序不会被当作章节", parsed.chapters[0].content)


if __name__ == "__main__":
    unittest.main()
