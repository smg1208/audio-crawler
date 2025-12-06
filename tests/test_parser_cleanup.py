import unittest
from crawler.parser import HTMLParser


SAMPLE_TEXT = '''
Chương

trước

Chương

tiếp

Tuỳ chỉnh

Theme

Font chữ

Palatino

Times

Arial

Georgia

Cỡ chữ

A-

26

A+

Màn hình

900

Chương 1 : Trời tối đừng đi ra ngoài

Trời tối, đừng đi ra ngoài.

Hãy nhấn like ở mỗi chương để ủng hộ tinh thần các dịch giả bạn nhé!

886

Tặng phiếu

Link thảo luận bên forum
'''


class TestParserCleanup(unittest.TestCase):
    def test_cleanup_removes_chrome(self):
        parser = HTMLParser()

        # embed the text into a chapter container to mimic page
        html = f'<div class="chapter-c"><div class="chapter-c-content">{SAMPLE_TEXT}</div></div>'
        out = parser.parse_main_text(html)

        # Should contain the real opening sentence
        self.assertIn('Trời tối, đừng đi ra ngoài.', out)

        # Should not contain UI chrome pieces
        for junk in ['Theme', 'Font chữ', 'Palatino', 'A+', 'Hãy nhấn like', 'Tặng phiếu', 'Link thảo luận']:
            self.assertNotIn(junk, out)


if __name__ == '__main__':
    unittest.main()
