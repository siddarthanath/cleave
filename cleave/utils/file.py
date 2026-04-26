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

def load_text_file(path: str) -> str:
    """Load a plain text file, falling back to latin-1 if the file is not valid UTF-8.

    Args:
        path (str): The path to the text file.

    Returns:
        str: The string contents of the file.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, encoding="latin-1") as f:
            return f.read()