# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Dict

# Third Party Library

# Private Library
from cleave.parsers.base import BaseParser
from cleave.parsers.office.docx import DocxParser
from cleave.parsers.office.pdf import PdfParser
from cleave.parsers.markup.md import MarkdownParser
from cleave.parsers.markup.html import HtmlParser
from cleave.parsers.plain.txt import TextParser
from cleave.parsers.code.py import PythonParser
from cleave.utils.file import get_path_and_extension

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ParserFactory:

    _PARSER_REGISTRY: Dict[str, type[BaseParser]] = {
        ".pdf":  PdfParser,
        ".docx": DocxParser,
        ".txt":  TextParser,
        ".md":   MarkdownParser,
        ".html": HtmlParser,
        ".htm":  HtmlParser,
        ".py":   PythonParser,
    }

    @classmethod
    def create(cls, input_path: str, mode: str = "flat") -> BaseParser:
        """Dynamically create a Parser from a file path or URL.

        Args:
            input_path (str): Local file path or URL.
            mode (str): Extraction mode — "flat" (pages) or "tree" (TreeNode hierarchy).
                        Defaults to "flat". Ignored for parsers that do not support mode.

        Raises:
            ValueError: If the file extension has no registered parser.

        Returns:
            BaseParser: Configured parser ready for .parse().
        """
        if input_path.startswith("http://") or input_path.startswith("https://"):
            return HtmlParser(file_path=input_path, mode=mode)

        _, ext = get_path_and_extension(path=input_path)

        if ext not in cls._PARSER_REGISTRY:
            raise ValueError(
                f"Unsupported extension '{ext}'. "
                f"Supported: {list(cls._PARSER_REGISTRY.keys())}"
            )

        return cls._PARSER_REGISTRY[ext](file_path=input_path, mode=mode)
