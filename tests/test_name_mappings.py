import json
import difflib
import re
import os
import unittest


def _tokens(s: str):
    return set([t.lower() for t in re.findall(r"[\wÀ-ÖØ-öø-ÿẀ-ỿ']{2,}", s)])


class TestNameMappings(unittest.TestCase):
    def test_name_mapping_semblance(self):
        p = os.path.join(os.path.dirname(__file__), '..', 'story_17299_names.json')
        p = os.path.abspath(p)
        with open(p, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        bad = []
        for k, v in data.items():
            if k == v:
                continue
            # token overlap OR fairly close sequence match required
            ks = _tokens(k)
            vs = _tokens(v)
            if len(ks & vs) > 0:
                continue
            ratio = difflib.SequenceMatcher(None, k, v).ratio()
            if ratio >= 0.65:
                continue
            bad.append((k, v, ks, vs, ratio))

        self.assertFalse(bad, f'Found improbable mappings (key -> value):\n' + '\n'.join([f"{a} -> {b} tokens={c} vs {d} ratio={e:.2f}" for a,b,c,d,e in bad]))
