# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path, Tuple

# Third Party Library
from abc import ABC, abstractmethod

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

def get_path_and_extension(path: str) -> Tuple[str, Path]:
    """This function gets the file extension of a path to create a Source.

    Args:
        path (str): File path (local).

    Returns:
        str: Extension.
    """
    path_ = Path(path)
    ext = path_.suffix.lower()
    return path_, ext