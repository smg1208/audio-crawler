import unittest
import tempfile
import os

import crawler.converter as conv_module
from crawler.converter import TextToAudioConverter


class FakeCommunicate:
    def __init__(self, text, voice=None):
        self.text = text
        self.voice = voice

    async def save(self, out_path):
        # emulate writing an audio file (write bytes)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as fh:
            fh.write(self.text.encode('utf-8'))


class TestConvertBatch(unittest.TestCase):
    def test_convert_batch_creates_files(self):
        # Patch Communicate in the converter module
        orig = getattr(conv_module, 'Communicate', None)
        conv_module.Communicate = FakeCommunicate

        try:
            with tempfile.TemporaryDirectory() as td:
                # create a few text files
                tasks = []
                for i in range(3):
                    in_path = os.path.join(td, f'chapter_{i}.txt')
                    out_path = os.path.join(td, f'chapter_{i}.mp3')
                    with open(in_path, 'w', encoding='utf-8') as fh:
                        fh.write(f'Chapter {i} text')
                    tasks.append((in_path, out_path, None))

                conv = TextToAudioConverter(backend='edge-tts', dry_run=False)
                # should not raise
                conv.convert_batch(tasks, concurrency=2)

                # verify files created and contents match
                for i in range(3):
                    out_path = os.path.join(td, f'chapter_{i}.mp3')
                    self.assertTrue(os.path.exists(out_path))
                    with open(out_path, 'rb') as fh:
                        data = fh.read()
                    self.assertIn(b'Chapter', data)
        finally:
            # restore original
            if orig is None:
                try:
                    delattr(conv_module, 'Communicate')
                except Exception:
                    pass
            else:
                conv_module.Communicate = orig


if __name__ == '__main__':
    unittest.main()
