import unittest
from unittest.mock import patch, Mock
from crawler.fetcher import ChapterFetcher


SAMPLE_HTML = '''
<html><body>
<ul class="chapters">
    <li><a href=" https:/tangthuvien.net/doc-truyen/story/chuong-1 ">Chapter 1</a></li>
    <li><a href="%20https:/tangthuvien.net/doc-truyen/story/chuong-1b%20">Chapter 1b</a></li>
  <li><a href="/doc-truyen/story/chuong-2">Chapter 2</a></li>
  <li><a href="https://tangthuvien.net/doc-truyen/story/chuong-3">Chapter 3</a></li>
  <li><a href="//tangthuvien.net/doc-truyen/story/chuong-4">Chapter 4</a></li>
</ul>
</body></html>
'''


class TestFetcherMalformed(unittest.TestCase):
    def setUp(self):
        self.fetcher = ChapterFetcher('https://tangthuvien.net/story/chapters?story_id={}', 'https://tangthuvien.net')

    @patch('crawler.fetcher.requests.get')
    def test_fetch_chapter_list_normalizes_urls(self, mock_get):
        # prepare fake response
        resp = Mock()
        resp.headers = {'Content-Type': 'text/html'}
        resp.text = SAMPLE_HTML
        resp.raise_for_status = Mock()

        mock_get.return_value = resp

        res = self.fetcher.fetch_chapter_list('x')
        urls = [c['url'] for c in res]

        # all urls should be normalized and contain 'https://'
        for u in urls:
            self.assertTrue(u.startswith('https://'), f'url not normalized: {u}')
            self.assertNotIn('%20', u)
        # also check that urls list contains both the two variants
        self.assertTrue(any('chuong-1' in u for u in urls))
        self.assertTrue(any('chuong-1b' in u for u in urls))

    @patch('crawler.fetcher.requests.get')
    def test_fetch_chapter_calls_sanitized_url(self, mock_get):
        # when fetching a chapter, ensure requests.get receives sanitized URL
        called_urls = []

        def fake_get(url, *args, **kwargs):
            called_urls.append(url)
            m = Mock()
            m.status_code = 200
            m.raise_for_status = Mock()
            m.text = '<html></html>'
            m.headers = {'Content-Type': 'text/html'}
            return m

        mock_get.side_effect = fake_get

        # pass a malformed url to fetch_chapter
        self.fetcher.fetch_chapter(' https:/tangthuvien.net/doc-truyen/story/chuong-1 ')

        self.assertEqual(len(called_urls), 1)
        self.assertTrue(called_urls[0].startswith('https://'))
        self.assertNotIn('%20', called_urls[0])


if __name__ == '__main__':
    unittest.main()
