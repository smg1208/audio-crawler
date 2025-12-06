import unittest
from crawler.name_utils import extract_person_names, make_placeholders, restore_placeholders


class TestNameUtils(unittest.TestCase):
    SAMPLE = 'Tần Mục và Tư bà bà đi tới Tàn Lão thôn. Mã lão cũng theo sau.'

    def test_extract(self):
        names = extract_person_names(self.SAMPLE)
        self.assertTrue(any('Tần Mục' in n or 'Tư bà bà' in n or 'Mã lão' in n for n in names))

    def test_placeholders_roundtrip(self):
        names = extract_person_names(self.SAMPLE)
        text_with_ph, mapping = make_placeholders(self.SAMPLE, names)
        # placeholders exist
        self.assertTrue(any('<<NAME_' in v for v in mapping.values()))

        # restore -> should contain original canonical names
        canonical_map = {n: n for n in mapping.keys()}
        restored = restore_placeholders(text_with_ph, mapping, canonical_map)
        self.assertIn('Tần Mục', restored)


if __name__ == '__main__':
    unittest.main()
