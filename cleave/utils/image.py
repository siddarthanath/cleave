# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import base64
import mimetypes
from pathlib import Path
from typing import Optional

# Third Party Library

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def encode_image(image_path: Path) -> str:
    """Encode a local image file as a base64 data URI.

    Args:
        image_path: Resolved absolute path to the image file.

    Returns:
        Base64 data URI string (e.g. ``data:image/png;base64,...``).
    """
    mime, _ = mimetypes.guess_type(str(image_path))
    mime = mime or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def resolve_image(src: str, base_dir: Path) -> Optional[Path]:
    """Resolve a local image src to an absolute Path, or return None for URLs/missing files.

    Args:
        src: Image src value — a URL, data URI, or local file path.
        base_dir: Directory to resolve relative local paths against.

    Returns:
        Resolved Path if the file exists locally, None otherwise.
    """
    if src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
        return None
    candidate = (base_dir / src).resolve()
    return candidate if candidate.exists() else None
