# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path
from urllib.parse import urlparse

# Third Party Library
from abc import ABC, abstractmethod

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
}

class BaseParser(ABC):

    def __init__(self, source: Source) -> None:
        self._source = source

    @property
    def source(self):
        return self._source
    
    @abstractmethod
    def parse(self) -> Document:
        """This function executes the following behaviour:
        1. Open file/URL.
        2. Extract contents page by page.
        3. Return a populated Document.
        """
        raise NotImplementedError("Subclasses must implement this method!")
        
    @staticmethod
    def _make_source(file_path: str) -> Source:
        """This function creates the Source structure from a given file path (not URL).

        Args:
            file_path (str): The file path of the document.

        Returns:
            Source: Golden truth for file.
        """       
        path_, ext = get_path_and_extension(path=file_path)
        if ext not in _EXTENSION_MAP:
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Supported: {list(_EXTENSION_MAP.keys())}"
            )
        return Source(type=_EXTENSION_MAP[ext],
                      name=path_.name,
                      location=str(path_.resolve()),)

    @staticmethod
    def _make_url_source(url: str) -> Source:
        """This function creates Source structure for URL.

        Args:
            url (str): The URL link.

        Returns:
            Source: Golden truth for URL.
        """
        parsed = urlparse(url)
        return Source(type=SourceType.url,
                      name=parsed.netloc,
                      location=url,)