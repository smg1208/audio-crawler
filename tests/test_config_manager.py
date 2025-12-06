import os
import json
import tempfile
import unittest

from crawler.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def test_load_and_save(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, 'cfg.json')
            data = {'story_id': 'x', 'last_downloaded_chapter': 0}
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh)

            cm = ConfigManager(path)
            self.assertEqual(cm.get('story_id'), 'x')

            cm.set('last_downloaded_chapter', 5)
            cm.save()

            with open(path, 'r', encoding='utf-8') as fh:
                d2 = json.load(fh)
            self.assertEqual(d2['last_downloaded_chapter'], 5)


if __name__ == '__main__':
    unittest.main()
