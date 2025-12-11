import unittest
from gen_youtube_descriptions import make_description


class TestGenYoutubeDescriptions(unittest.TestCase):
    def test_template_substitution(self):
        story_title = 'Trận Vấn Trường Sinh'
        chapters = [
            {'index': 1, 'title': 'Chương 1: Mặc Họa', 'url': 'http://example'},
            {'index': 2, 'title': 'Chương 2: Đạo Bia', 'url': 'http://example'},
        ]
        metadata = {
            'author': 'Trạch Trư',
            'lead': 'Cùng theo chân Tần Mục khám phá bí ẩn Đại Khư!',
            'synopsis': 'Tóm tắt ngắn gọn của truyện',
            'work_title': 'Mục Thần Ký (Tales of Herding Gods)',
            'tags': '#MucThanKy #TrachTru',
            'narrator': 'Giọng đọc Nam Minh (tts)'
        }

        out = make_description(story_title, 1, chapters, playlist_link='http://playlist', metadata=metadata)
        self.assertIn('Tác giả: Trạch Trư', out)
        self.assertIn('Cùng theo chân Tần Mục khám phá bí ẩn Đại Khư!', out)
        self.assertIn('Tóm tắt ngắn gọn của truyện', out)
        self.assertIn('Mục Thần Ký (Tales of Herding Gods)', out)
        self.assertIn('#MucThanKy #TrachTru', out)
        # test starting episode offset
        out2 = make_description(story_title, 1, chapters, playlist_link='http://playlist', metadata=metadata, start_episode=5)
        self.assertIn('Tập 5', out2)


if __name__ == '__main__':
    unittest.main()
import os
import tempfile
import unittest
from unittest.mock import patch, Mock

from crawler.config_manager import ConfigManager

from gen_youtube_descriptions import write_descriptions


class TestGenDescriptions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # create a minimal config file pointing at a fake story
        import json
        cfg_path = os.path.join(self.tmp.name, 'cfg.json')
        with open(cfg_path, 'w', encoding='utf-8') as fh:
            json.dump({
                'story_id': 'FAKE',
                'base_url': 'https://example.com',
                'chapters_api': 'https://example.com/chapters?story_id={}',
                'last_downloaded_chapter': 0,
                'batch_size': 15,
            }, fh)
        self.cfg_path = cfg_path

    def tearDown(self):
        self.tmp.cleanup()

    @patch('gen_youtube_descriptions.ChapterFetcher')
    def test_write_descriptions_creates_files(self, mock_fetcher_cls):
        # make a fake chapter list 1..7
        fake_chapters = [{'index': i, 'title': f'Chương {i}: Một tiêu đề {i}', 'url': f'https://ex/ch{i}'} for i in range(1, 8)]

        # fake instance
        fetcher = Mock()
        fetcher.fetch_chapter_list.return_value = fake_chapters
        fetcher.fetch_chapter.return_value = '<html><h1 class="truyen-title">Test Story</h1><div class="box-chap">Nội dung</div></html>'
        mock_fetcher_cls.return_value = fetcher

        cfg = ConfigManager(self.cfg_path)
        count = write_descriptions(cfg, group_size=5, out_playist='PL')

        out_dir = os.path.join('.', f"{cfg.get('story_id')} - Youtube description")
        self.assertTrue(os.path.exists(out_dir))
        # should make two description files (5 and 2)
        files = sorted(os.listdir(out_dir))
        self.assertEqual(len(files), 2)

        # cleanup created folder
        for f in files:
            os.remove(os.path.join(out_dir, f))
        os.rmdir(out_dir)


if __name__ == '__main__':
    unittest.main()
