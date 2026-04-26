# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Literal

# Third Party Library

# Private Library
from cleave.parsers.base import BaseParser
from cleave.schemas import ContentBlock, ContentType, Document, DocumentPage
from cleave.utils.file import load_text_file

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class TextParser(BaseParser):
    """Parser for plain-text (.txt) files.

    Only flat mode is supported. Plain text has no structural markers
    (headings, sections) so a semantic tree cannot be constructed.
    Use MarkdownParser for .md files if tree mode is needed.
    """

    def __init__(self, file_path: str, mode: Literal["flat", "tree"] = "flat") -> None:
        super().__init__(BaseParser._make_source(file_path=file_path))
        if mode not in ("flat", "tree"):
            raise ValueError(f"mode must be 'flat' or 'tree', got {mode!r}")
        if mode == "tree":
            raise NotImplementedError(
                "TextParser does not support tree mode - plain text files have no "
                "structural markers. Use MarkdownParser for .md files."
            )
        self._mode = mode

    def parse(self) -> Document:
        """Read the text file and return a single-page flat Document.

        Returns:
            Document with one DocumentPage containing the full file text.
        """
        text_contents = load_text_file(self.source.location)
        doc_page = DocumentPage(
            page_number=None,
            blocks=[ContentBlock(type=ContentType.text, content=text_contents, position=0)],
        )
        return Document(source=self.source, pages=[doc_page], total_pages=1)
