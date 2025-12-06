import unittest

from crawler.parser import HTMLParser


class TestHTMLParser(unittest.TestCase):
    SAMPLE_HTML = '''
    <html><body>
    <div id="chapter-content">
        <h1>Chapter Title</h1>
        <p>Paragraph 1.</p>
        <p>Paragraph 2.</p>
    </div>
    </body></html>
    '''

    def test_parse_main_text(self):
        p = HTMLParser()
        text = p.parse_main_text(self.SAMPLE_HTML)
        self.assertIn('Chapter Title', text)
        self.assertIn('Paragraph 1.', text)


if __name__ == '__main__':
    unittest.main()
