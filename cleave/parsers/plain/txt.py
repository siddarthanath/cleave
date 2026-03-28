# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library

# Private Library
from cleave.parsers.base import BaseParser
from cleave.schemas import ContentBlock, ContentType, Document, DocumentPage, Source, SourceType
from cleave.utils.file import load_text_file

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TextParser(BaseParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(BaseParser._make_source(file_path=file_path))

    def parse(self) -> Document:
        """This function executes the following behaviour:
        1. Open file/URL.
        2. Extract contents page by page.
        3. Return a populated Document.
        """
        text_contents = load_text_file(self.source.location)
        # Text file load will only be one full page
        doc_page = DocumentPage(page_number=None,
                                blocks=[ContentBlock(type=ContentType.text,
                                                    content=text_contents,
                                                    position=0)])
        return Document(source=self.source, 
                        pages=[doc_page],
                        total_pages=1)