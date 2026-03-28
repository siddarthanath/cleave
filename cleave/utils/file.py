# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path
from typing import Tuple

# Third Party Library

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

def get_path_and_extension(path: str) -> Tuple[Path, str]:
    """This function gets the file path object and extension from a path string.
    
    Args:
        path (str): File path (local).
    
    Returns:
        Tuple[Path, str]: A tuple containing the Path object and the file extension.
    """
    path_ = Path(path)
    ext = path_.suffix.lower()
    return path_, ext