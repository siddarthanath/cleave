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
    return Source(type=SourceType.txt, name="sample.txt", location="/tmp/sample.txt")

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
