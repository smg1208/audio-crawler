import unittest
import tempfile
import os

from crawler.converter import TextToAudioConverter


class TestConverterDryRun(unittest.TestCase):
    def test_ttx_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, 'in.txt')
            out_path = os.path.join(td, 'out.mp3')
            with open(in_path, 'w', encoding='utf-8') as fh:
                fh.write('Hello world')

            conv = TextToAudioConverter(backend='ttx', dry_run=True)
            # should not raise
            conv.convert(in_path, out_path)

    def test_edge_tts_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, 'in.txt')
            out_path = os.path.join(td, 'out.mp3')
            with open(in_path, 'w', encoding='utf-8') as fh:
                fh.write('Xin chào')

            conv = TextToAudioConverter(backend='edge-tts', dry_run=True)
            # should not raise even if edge-tts isn't installed because dry_run short-circuits
            conv.convert(in_path, out_path, voice='vi-VN-HoaiMyNeural')


if __name__ == '__main__':
    unittest.main()
