# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlparse

# Third Party Library

# Private Library
from cleave.schemas import Document, Source, SourceType
from cleave.utils.file import get_path_and_extension

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_EXTENSION_MAP = {
    ".pdf":  SourceType.pdf,
    ".docx": SourceType.docx,
    ".pptx": SourceType.pptx,
    ".html": SourceType.html,
    ".htm":  SourceType.html,
    ".md":   SourceType.markdown,
    ".txt":  SourceType.txt,
    ".py":   SourceType.python,
}


class BaseParser(ABC):

    def __init__(self, source: Source) -> None:
        self._source = source

    @property
    def source(self) -> Source:
        return self._source

    @abstractmethod
    def parse(self) -> Document:
        """Open the source, extract its contents, and return a populated Document."""
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def _make_source(file_path: str) -> Source:
        """Create a Source from a local file path.

        Args:
            file_path: Absolute or relative path to the document file.

        Returns:
            Source instance with type, name, and resolved location.
        """
        path_, ext = get_path_and_extension(path=file_path)
        if ext not in _EXTENSION_MAP:
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Supported: {list(_EXTENSION_MAP.keys())}"
            )
        resolved = path_.resolve()
        file_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return Source(
            source_type=_EXTENSION_MAP[ext],
            name=path_.name,
            location=str(resolved),
            file_hash=file_hash,
        )

    @staticmethod
    def _make_url_source(url: str) -> Source:
        """Create a Source from a URL.

        Args:
            url: Full URL string.

        Returns:
            Source instance with type=url.
        """
        parsed = urlparse(url)
        return Source(source_type=SourceType.url, name=parsed.netloc, location=url)


class BaseModeParser(BaseParser):
    """BaseParser extension for parsers that support both flat and tree output modes.

    Subclasses implement `_parse_flat` and `_parse_tree`; this class owns
    mode validation and dispatches `parse()` to the correct strategy.
    """

    def __init__(self, file_path: str, mode: str = "flat") -> None:
        super().__init__(BaseParser._make_source(file_path=file_path))
        if mode not in ("flat", "tree"):
            raise ValueError(f"mode must be 'flat' or 'tree', got {mode!r}")
        self._mode = mode

    def parse(self) -> Document:
        """Delegate to `_parse_flat` or `_parse_tree` based on the chosen mode.

        Returns:
            Document with `.pages` populated (flat) or `.root` populated (tree).
        """
        if self._mode == "flat":
            return self._parse_flat()
        return self._parse_tree()

    @abstractmethod
    def _parse_flat(self) -> Document:
        """Extract content into a flat page-based Document."""
        ...

    @abstractmethod
    def _parse_tree(self) -> Document:
        """Extract content into a heading-scoped TreeNode Document."""
        ...
