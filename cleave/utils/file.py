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
    """This function loads and reads any plain text file from memory with UTf-8 encoding
    e.g., .txt, .csv, .json, .xml, .html, .py, .md, .log etc...

    Args:
        path (str): The path to the text file.

    Returns:
        str: The string format of the text file.
    """
    with open(path, encoding='utf-8') as f:
        return f.read()