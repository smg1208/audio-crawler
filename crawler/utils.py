import os
import shutil
from typing import Iterable, Optional


def ensure_dirs(paths: Iterable[str]):
    for p in paths:
        os.makedirs(p, exist_ok=True)


def is_cli_available(cmd: str) -> bool:
    """Return True if command is available in PATH."""
    return shutil.which(cmd) is not None


def extract_chapter_number_from_text(text: str, title: str = None) -> Optional[str]:
    """Try to extract an explicit chapter number from chapter text or title.

    Returns a string (e.g. '12' or '12.5') if found, otherwise None.
    """
    import re
    if not text and not title:
        return None

    hay = (text or '')[:2000]
    patterns = [
        r'Chương\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)',
        r'Chương\s+([0-9]+(?:\.[0-9]+)?)',
        r'Ch\.?\s*([0-9]+(?:\.[0-9]+)?)',
        r'Chapter\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, hay, flags=re.IGNORECASE)
        if m:
            return m.group(1)

    # fallback to searching title
    if title:
        for pat in patterns:
            m = re.search(pat, title, flags=re.IGNORECASE)
            if m:
                return m.group(1)

    return None
