import unittest
from unittest.mock import Mock, patch
from crawler.fetcher import ChapterFetcher


class TestFetcherRetries(unittest.TestCase):
    def setUp(self):
        self.fetcher = ChapterFetcher('https://tangthuvien.net/story/chapters?story_id={}', 'https://tangthuvien.net')
        self.fetcher.configure_retries(max_attempts=3, backoff_seconds=0.001)

    @patch('crawler.fetcher.requests.get')
    def test_retries_on_server_error_then_success(self, mock_get):
        # first two attempts return 500, third attempt returns 200
        m1 = Mock()
        m1.status_code = 500
        m1.raise_for_status.side_effect = None

        m2 = Mock()
        m2.status_code = 500
        m2.raise_for_status.side_effect = None

        m3 = Mock()
        m3.status_code = 200
        m3.text = 'OK'
        m3.raise_for_status = Mock()

        # sequence of calls should use the same candidate until it succeeds
        mock_get.side_effect = [m1, m2, m3]

        text = self.fetcher.fetch_chapter('https://tangthuvien.net/doc-truyen/test')
        self.assertEqual(text, 'OK')

    @patch('crawler.fetcher.requests.get')
    def test_404_skips_candidate_and_succeeds_with_next(self, mock_get):
        # If first candidate returns 404 we should skip to the next candidate
        r404 = Mock()
        r404.status_code = 404
        r404.raise_for_status.side_effect = None

        r200 = Mock()
        r200.status_code = 200
        r200.text = 'PAGE'
        r200.raise_for_status = Mock()

        # Patch candidate generator to return two specific candidates
        with patch.object(ChapterFetcher, '_candidate_variants', return_value=['https://tangthuvien.net/doc-truyen/test404', 'https://tangthuvien.net/doc-truyen/test404b']):
            mock_get.side_effect = [r404, r200]
            text = self.fetcher.fetch_chapter(' https:/tangthuvien.net/doc-truyen/test404 ')
            self.assertEqual(text, 'PAGE')


if __name__ == '__main__':
    unittest.main()
