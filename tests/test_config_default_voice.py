import unittest
from crawler.config_manager import ConfigManager


class TestDefaultVoice(unittest.TestCase):
    def test_config_default_voice(self):
        cfg = ConfigManager('config.json')
        self.assertIsNotNone(cfg.get('tts_voice'))
        self.assertEqual(cfg.get('tts_voice'), 'vi-VN-NamMinhNeural')


if __name__ == '__main__':
    unittest.main()
