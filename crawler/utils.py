import os
import shutil
from typing import Iterable


def ensure_dirs(paths: Iterable[str]):
    for p in paths:
        os.makedirs(p, exist_ok=True)


def is_cli_available(cmd: str) -> bool:
    """Return True if command is available in PATH."""
    return shutil.which(cmd) is not None
