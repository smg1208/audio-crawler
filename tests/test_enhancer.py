import unittest
import tempfile
import json
import os

from crawler.enhancer import improve_chapter_text
from crawler.llm_wrapper import LLMClient


class TestEnhancer(unittest.TestCase):
    SAMPLE = 'Tần Mục cùng Tư bà bà nói chuyện. Mã lão lắc đầu.'

    def test_improve_dry_run(self):
        out, cmap, warnings = improve_chapter_text(self.SAMPLE, story_id='test', storage_dir=tempfile.gettempdir(), llm_client=LLMClient(), dry_run=True)
        self.assertIsInstance(out, str)
        # canonical map contains discovered names
        self.assertTrue(any('Tần Mục' in v or 'Tư bà bà' in v or 'Mã lão' in v for v in cmap.values()))

    def test_storage_created(self):
        tmpdir = tempfile.gettempdir()
        storyfile = os.path.join(tmpdir, 'story_test_names.json')
        try:
            if os.path.exists(storyfile):
                os.remove(storyfile)
            out, cmap, warnings = improve_chapter_text(self.SAMPLE, story_id='test', storage_dir=tmpdir, llm_client=LLMClient(), dry_run=True)
            self.assertTrue(os.path.exists(storyfile))
        finally:
            if os.path.exists(storyfile):
                os.remove(storyfile)

    def test_skip_multiline_ui_noise(self):
        tmpdir = tempfile.gettempdir()
        storyfile = os.path.join(tmpdir, 'story_test_names.json')
        try:
            # prepare a pre-existing canonical so accidental matching could occur
            with open(storyfile, 'w', encoding='utf-8') as fh:
                json.dump({'ignored': 'Kim Quy trước'}, fh, ensure_ascii=False)

            noisy = 'Chương\ntrước\ntiếp\nTuỳ chỉnh\nTheme\nFont chữ\nPalatino'
            out, cmap, warnings = improve_chapter_text(noisy, story_id='test', storage_dir=tmpdir, llm_client=LLMClient(), dry_run=True)
            # The noisy multi-line UI chunk should not be canonicalized to a short name
            self.assertIn(noisy, cmap)
            self.assertEqual(cmap[noisy], noisy)
            self.assertTrue(any('Skipping' in w for w in warnings))
        finally:
            if os.path.exists(storyfile):
                os.remove(storyfile)

    def test_allow_small_typo(self):
        tmpdir = tempfile.gettempdir()
        storyfile = os.path.join(tmpdir, 'story_test_names.json')
        try:
            # pre-populate canonical names
            with open(storyfile, 'w', encoding='utf-8') as fh:
                json.dump({'foo': 'Thanh Long'}, fh, ensure_ascii=False)

            sample = 'Thanh Longggg xuất hiện'
            out, cmap, warnings = improve_chapter_text(sample, story_id='test', storage_dir=tmpdir, llm_client=LLMClient(), dry_run=True)
            # small typo should be canonicalized (extractor may normalize the candidate so verify
            # that some discovered name maps to the canonical 'Thanh Long')
            self.assertTrue(any(v == 'Thanh Long' for v in cmap.values()))
        finally:
            if os.path.exists(storyfile):
                os.remove(storyfile)

    def test_block_unrelated_long_match(self):
        tmpdir = tempfile.gettempdir()
        storyfile = os.path.join(tmpdir, 'story_test_names.json')
        try:
            with open(storyfile, 'w', encoding='utf-8') as fh:
                json.dump({'foo': 'Ngũ Long Luyện Ma, Lục Long Luân Hồi'}, fh, ensure_ascii=False)

            sample = 'Lục Thi xuất hiện'
            out, cmap, warnings = improve_chapter_text(sample, story_id='test', storage_dir=tmpdir, llm_client=LLMClient(), dry_run=True)
            # should not map improbable short name to very long canonical
            self.assertIn('Lục Thi', cmap)
            self.assertEqual(cmap['Lục Thi'], 'Lục Thi')
            self.assertTrue(any('length mismatch' in w.lower() or 'ambiguous' in w.lower() for w in warnings))
        finally:
            if os.path.exists(storyfile):
                os.remove(storyfile)


if __name__ == '__main__':
    unittest.main()
