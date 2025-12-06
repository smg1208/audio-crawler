import unittest
from crawler.parser import HTMLParser

SAMPLE_HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
</head>
<body>
<!-- trimmed for test -->
<div class="chapter-c max900">
  <div class="chapter-c-content">
    <div class="box-chap box-chap-3512668"> Trời tối, đừng đi ra ngoài.

Câu nói này tại Tàn Lão thôn lưu truyền rất nhiều năm...</div>
  </div>
</div>
</body>
</html>
"""


class TestParserRealWorld(unittest.TestCase):
    def test_parse_tangthuvien_chapter(self):
        parser = HTMLParser()
        text = parser.parse_main_text(SAMPLE_HTML)

        # important snippets expected from the real HTML
        self.assertIn('Trời tối, đừng đi ra ngoài', text)
        self.assertIn('Tàn Lão thôn', text)
        self.assertNotIn('<div', text)  # should be plain text, not raw HTML


if __name__ == '__main__':
    unittest.main()
