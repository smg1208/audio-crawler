"""Name extraction, canonicalization and placeholder helper utilities.

This module provides a pragmatic, dependency-tolerant implementation so the
project can extract PERSON-like tokens from chapter text, create stable
placeholders, and perform fuzzy canonicalization against an existing registry.

It will prefer stanza (stronger NER for Vietnamese) when available, otherwise
fall back to a conservative regex-based heuristic.
"""
from typing import List, Tuple, Dict
import re
import logging

try:
    import stanza
    _HAS_STANZA = True
except Exception:
    stanza = None  # type: ignore
    _HAS_STANZA = False

try:
    from rapidfuzz import process, fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    process = None  # type: ignore
    fuzz = None  # type: ignore
    _HAS_RAPIDFUZZ = False
    import difflib

logger = logging.getLogger(__name__)


def _init_stanza():
    if not _HAS_STANZA:
        return None
    try:
        # ensure Vietnamese model is available
        stanza.download('vi', logging_level='ERROR')
    except Exception:
        # if download fails, pipeline creation may still work if already installed
        pass
    try:
        return stanza.Pipeline(lang='vi', processors='tokenize,ner', logging_level='ERROR')
    except Exception:
        return None


_STANZA_PIPELINE = _init_stanza()


def extract_person_names(text: str) -> List[str]:
    """Extract PERSON-like names from text.

    Returns a list of candidate strings (may include duplicates) in order of appearance.
    """
    if _STANZA_PIPELINE is not None:
        try:
            doc = _STANZA_PIPELINE(text)
            out = [ent.text for ent in doc.ents if ent.type == 'PERSON']
            if out:
                return out
        except Exception:
            logger.debug('stanza pipeline failed, falling back to regex', exc_info=True)

    # Fallback heuristic: look for multi-word tokens starting with uppercase / Vietnamese letters
    # This is conservative and may miss some corner cases but works reasonably for most text.
    pattern = re.compile(r"\b[\wÀ-ÖØ-öø-ÿẀ-ỿ][\wÀ-ÖØ-öø-ÿẀ-ỿ.'`-]{1,}(?:\s+[\wÀ-ÖØ-öø-ÿẀ-ỿ][\wÀ-ÖØ-öø-ÿẀ-ỿ.'`-]{1,})+\b")
    candidates = pattern.findall(text)

    # refine: drop purely numeric or too short results
    refined = []
    for c in candidates:
        cw = c.strip()
        if len(cw) < 3:
            continue
        if any(ch.isdigit() for ch in cw):
            continue
        refined.append(cw)
    return refined


def canonicalize_name(candidate: str, canonical_list: List[str], threshold: int = 85) -> Tuple[str, int]:
    """Fuzzy-match candidate against canonical_list and return best match + score.

    If no match meets the threshold it returns the candidate itself with score 100.
    """
    if not canonical_list:
        return candidate, 100

    if _HAS_RAPIDFUZZ:
        match = process.extractOne(candidate, canonical_list, scorer=fuzz.WRatio)
        if not match:
            return candidate, 100

        matched_str, score, _ = match
    else:
        # fallback using difflib to avoid hard dependency in minimal environments
        close = difflib.get_close_matches(candidate, canonical_list, n=1, cutoff=0.0)
        if not close:
            return candidate, 100
        matched_str = close[0]
        score = int(difflib.SequenceMatcher(None, candidate, matched_str).ratio() * 100)
    if score >= threshold:
        return matched_str, score
    return candidate, score


def is_likely_name(s: str) -> bool:
    """Quick heuristic to filter out obviously-not-name candidates.

    Rules:
    - reject if contains newline/control chars
    - reject if far too long (site chrome / paragraphs)
    - reject if contains common UI terms that sometimes leak into extraction
    - accept otherwise
    """
    if not s or '\n' in s:
        return False
    s = s.strip()
    if len(s) < 2:
        return False
    if len(s) > 60:
        return False

    # blacklist some UI words that were observed in crawled HTML
    ui_terms = ('theme', 'font', 'palatino', 'times', 'arial', 'georgia', 'cỡ', 'chữ', 'tuỳ', 'chỉnh', 'chương', 'trước', 'tiếp')
    low = s.lower()
    for w in ui_terms:
        if w in low:
            return False

    return True


def make_placeholders(text: str, names: List[str]) -> Tuple[str, Dict[str, str]]:
    """Replace names with placeholders and return (new_text, mapping original->placeholder).

    Replaces the longer names first to avoid partial replacement (e.g. "Tần Mục" before "Mục").
    Matching is exact (case-sensitive) to reduce accidental replacements.
    """
    # produce unique-preserving name list in order of decreasing length
    unique_names = []
    for n in names:
        if n not in unique_names:
            unique_names.append(n)
    unique_names = sorted(unique_names, key=lambda s: -len(s))

    mapping: Dict[str, str] = {}
    out = text
    for i, name in enumerate(unique_names, start=1):
        token = f"<<NAME_{i}>>"
        # use word boundary or exact sequence to replace
        # Escape name for regex
        esc = re.escape(name)
        out, count = re.subn(rf"\b{esc}\b", token, out)
        if count > 0:
            mapping[name] = token

    return out, mapping


def restore_placeholders(text: str, mapping: Dict[str, str], canonical_map: Dict[str, str]) -> str:
    """Restore placeholders back to canonical names.

    mapping: original_name -> placeholder
    canonical_map: original_name -> canonical_name
    """
    out = text
    # invert mapping: placeholder -> original_name
    inv = {v: k for k, v in mapping.items()}
    # to avoid partial collisions, replace placeholders directly
    for placeholder, orig in inv.items():
        canonical = canonical_map.get(orig, orig)
        out = out.replace(placeholder, canonical)
    return out
