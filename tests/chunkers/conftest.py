# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library
import pytest

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import (
    Chunk,
    ChunkParams,
    ChunkUnit,
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    Source,
    SourceType,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class DummyChunker(BaseChunker):
    """Minimal concrete subclass used to test BaseChunker methods directly."""

    def chunk(self, document: Document) -> List[Chunk]:
        return []


@pytest.fixture
def source() -> Source:
    return Source(source_type=SourceType.txt, name="sample.txt", location="/tmp/sample.txt")

@pytest.fixture
def char_params() -> ChunkParams:
    return ChunkParams(chunk_size=50, chunk_overlap=10)

@pytest.fixture
def token_params() -> ChunkParams:
    return ChunkParams(chunk_size=10, chunk_overlap=2, unit=ChunkUnit.tokens)

@pytest.fixture
def multipage_document(source) -> Document:
    """Two-page Document with short distinct text per page."""
    def make_page(num: int, text: str) -> DocumentPage:
        return DocumentPage(
            page_number=num,
            blocks=[ContentBlock(type=ContentType.text, content=text, position=0)],
        )

    return Document(
        source=source,
        pages=[
            make_page(1, "Hello world this is page one."),
            make_page(2, "And here we have page two content."),
        ],
        total_pages=2,
    )


@pytest.fixture
def dummy_chunker(char_params) -> DummyChunker:
    return DummyChunker(char_params)


@pytest.fixture
def mixed_content_document(source) -> Document:
    """Single-page Document with text, table, and image blocks."""
    return Document(
        source=source,
        pages=[
            DocumentPage(
                page_number=1,
                blocks=[
                    ContentBlock(type=ContentType.text,  content="Hello world. This is some text.", position=0),
                    ContentBlock(type=ContentType.table, content="| A | B |\n|---|---|\n| 1 | 2 |", position=1),
                    ContentBlock(type=ContentType.image, content="base64encodeddata", position=2),
                    ContentBlock(type=ContentType.text,  content="More text after the table.", position=3),
                ],
            )
        ],
        total_pages=1,
    )
