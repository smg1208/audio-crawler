import unittest
from crawler.parser import HTMLParser


class TestParserDedupTitle(unittest.TestCase):
    def test_remove_consecutive_duplicate_title(self):
        html = """
        <div class="box-chap">
            Chương 5 : Một ví dụ tiêu đề

            Chương 5 : Một ví dụ tiêu đề

            Nội dung chương bắt đầu ở đây.
        </div>
        """
        p = HTMLParser()
        out = p.parse_main_text(html)
        # the title should appear only once
        self.assertEqual(out.count('Chương 5'), 1)

    def test_remove_near_duplicate_title(self):
        html = """
        <div class="box-chap">
            Chương 5: Một ví dụ tiêu đề

            
            Chương 5 : Một ví dụ tiêu đề

            Nội dung chương bắt đầu ở đây.
        </div>
        """
        p = HTMLParser()
        out = p.parse_main_text(html)
        # the title should appear only once
        self.assertEqual(out.count('Chương 5'), 1)


if __name__ == '__main__':
    unittest.main()
