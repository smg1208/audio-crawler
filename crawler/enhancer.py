"""Enhancer pipeline to safely improve chapter text while preserving names.

Functions here perform: NER -> canonicalization -> placeholdering -> LLM improvement -> restore -> validation
"""
from typing import Dict, Tuple, List, Optional
import json
import os
import logging

from .name_utils import extract_person_names, canonicalize_name, make_placeholders, restore_placeholders, is_likely_name
from .llm_wrapper import LLMClient

logger = logging.getLogger(__name__)


def load_canonical_map(storage_path: str) -> Dict[str, str]:
    if os.path.exists(storage_path):
        with open(storage_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    return {}


def save_canonical_map(storage_path: str, mapping: Dict[str, str]) -> None:
    with open(storage_path, 'w', encoding='utf-8') as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2)


def improve_chapter_text(
    text: str,
    story_id: Optional[str] = None,
    storage_dir: str = '.',
    llm_client: Optional[LLMClient] = None,
    dry_run: bool = True,
    fuzzy_threshold: int = 85,
) -> Tuple[str, Dict[str, str], List[str]]:
    """Improve text while preserving and canonicalizing character names.

    Returns (improved_text, updated_canonical_map, warnings)
    - updated_canonical_map maps original discovered names -> canonical names
    - warnings contains strings describing suspicious or ambiguous matches
    """
    warnings: List[str] = []

    storage_path = os.path.join(storage_dir, f'story_{story_id}_names.json') if story_id else None
    canonical_map = load_canonical_map(storage_path) if storage_path else {}

    # 1) Extract names
    found = extract_person_names(text)
    unique_found = []
    for n in found:
        if n not in unique_found:
            unique_found.append(n)

    # 2) Try to map to existing canonicals
    for name in unique_found:
        if name in canonical_map:
            continue
        # fuzzy match against known canonicals
        existing = list(set(canonical_map.values())) if canonical_map else []
        canonical, score = canonicalize_name(name, existing, threshold=fuzzy_threshold)
        if canonical != name:
            # Additional safety checks: ensure both candidate and matched canonical look like names
            def _tokens(s: str):
                return [t for t in s.replace('"', '').split() if len(t) > 1]

            if not is_likely_name(name) or not is_likely_name(canonical):
                warnings.append(f'Skipping unsafe canonicalization: "{name}" -> "{canonical}" (not likely a name)')
                canonical_map[name] = name
            else:
                # require token overlap and reasonable length similarity
                ks = set(_tokens(name))
                vs = set(_tokens(canonical))
                if len(ks & vs) == 0:
                    warnings.append(f'Skipping ambiguous canonicalization: "{name}" -> "{canonical}" (no shared tokens)')
                    canonical_map[name] = name
                else:
                    maxlen = max(len(name), len(canonical))
                    if abs(len(name) - len(canonical)) / maxlen > 0.5:
                        warnings.append(f'Skipping canonicalization due to length mismatch: "{name}" -> "{canonical}"')
                        canonical_map[name] = name
                    else:
                        # Accept mapping
                        canonical_map[name] = canonical
        else:
            # treat as new by default — keep original as canonical (may want manual confirm later)
            canonical_map[name] = name

    # 3) Substitute placeholders
    placeholder_text, mapping = make_placeholders(text, unique_found)

    # 4) Improve with LLM if available (or perform local cleaning)
    if llm_client and llm_client.available() and not dry_run:
        system_prompt = (
            "You are an assistant that improves chapter text for readability, grammar and punctuation. "
            "Do NOT change any placeholders like <<NAME_1>> etc. Return only the improved text body and do not add commentary."
        )
        try:
            improved = llm_client.improve_text(placeholder_text, system_prompt=system_prompt)
        except Exception as e:
            warnings.append(f'LLM improvement failed: {e}')
            improved = placeholder_text
    else:
        # local lightweight improvement: normalize whitespace and punctuation spacing and preserve placeholders
        # replace multiple spaces/newlines
        import re

        # collapse multiple blank lines to two
        improved = re.sub(r"\n\s*\n+", "\n\n", placeholder_text)
        # collapse multiple spaces
        improved = re.sub(r" {2,}", " ", improved)

    # 5) restore placeholders back to canonical names
    final_text = restore_placeholders(improved, mapping, canonical_map)

    # 6) Post-check: ensure canonical names are present
    post_found = extract_person_names(final_text)
    post_unique = list(dict.fromkeys(post_found))
    for orig, canon in list(canonical_map.items()):
        if canon not in post_unique:
            warnings.append(f'Canonical name "{canon}" derived from "{orig}" not found after improvement')

    # 7) Persist canonical map
    if storage_path and story_id:
        try:
            save_canonical_map(storage_path, canonical_map)
        except Exception as ex:
            warnings.append(f'Failed to save canonical map: {ex}')

    return final_text, canonical_map, warnings
