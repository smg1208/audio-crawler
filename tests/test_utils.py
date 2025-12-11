import unittest
from crawler.utils import extract_chapter_number_from_text


class TestUtilsExtractChapter(unittest.TestCase):
    def test_extract_from_text(self):
        txt = """Chương 42: Cuộc đột kích

        Nội dung chương..."""
        self.assertEqual(extract_chapter_number_from_text(txt), '42')

    def test_extract_decimal(self):
        txt = "Chương 12.5: Ngoại truyện"
        self.assertEqual(extract_chapter_number_from_text(txt), '12.5')

    def test_extract_from_title(self):
        title = "Chương 7: Tiêu đề"
        self.assertEqual(extract_chapter_number_from_text('', title), '7')

    def test_no_number(self):
        txt = "Một chương không ghi số"
        self.assertIsNone(extract_chapter_number_from_text(txt))


if __name__ == '__main__':
    unittest.main()
