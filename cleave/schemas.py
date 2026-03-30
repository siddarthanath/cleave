# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from enum import Enum
from typing import List

# Third Party Library
from pydantic import BaseModel, Field, model_validator

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Source 

class SourceType(str, Enum):
    pdf = "pdf"
    docx = "docx"
    pptx = "pptx"
    html = "html"
    markdown = "markdown"
    txt = "txt"
    url = "url"

class Source(BaseModel):
    type: SourceType = Field(description="File format or source type.")
    name: str = Field(description="Human-readable label e.g. filename or domain.", min_length=1)
    location: str = Field(description="Absolute filepath or full URL.", min_length=1)

# Content

class ContentType(str, Enum):
    text  = "text"
    image = "image"
    table = "table"


class ContentBlock(BaseModel):
    type: ContentType = Field(description="Type of content: text, image, or table.")
    content: str = Field(description=("The content payload. "
                                      "text  → raw string. "
                                      "image → base64-encoded bytes as string. "
                                      "table → markdown-formatted table string."),
                                      min_length=1,)
    position: int = Field(description="0-based position of this block within the page.", ge=0)

# Document

class DocumentPage(BaseModel):
    page_number: int | None = Field(description="1-based page number. None for sources with no page concept (txt, url, docx).",
                                    ge=1,
                                    default=None,)
    blocks: List[ContentBlock] = Field(description="Ordered content blocks that make up this page.",
                                       min_length=0,)

    @property
    def text(self) -> str:
        return "\n".join(
            b.content
            for b in sorted(self.blocks, key=lambda b: b.position)
            if b.type == ContentType.text
        )

    @property
    def images(self) -> List[ContentBlock]:
        return [b for b in self.blocks if b.type == ContentType.image]

    @property
    def tables(self) -> List[ContentBlock]:
        return [b for b in self.blocks if b.type == ContentType.table]

class Document(BaseModel):
    source: Source = Field(description="Origin of this document.")
    pages: List[DocumentPage] = Field(description="Ordered List of pages.", min_length=1)
    total_pages: int = Field(description="Total number of pages in the document.", ge=1)

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def all_images(self) -> List[ContentBlock]:
        return [block for page in self.pages for block in page.images]

    @property
    def all_tables(self) -> List[ContentBlock]:
        return [block for page in self.pages for block in page.tables]

# Embeddings

class ChunkerType(str, Enum):
    fixed = "fixed"
    sentence = "sentence"
    recursive = "recursive"
    semantic = "semantic"

class ChunkUnit(str, Enum):
    characters = "characters"
    tokens     = "tokens"

class ChunkParams(BaseModel):
    chunk_size: int = Field(description="The length of each chunk of text", gt=0)
    chunk_overlap: int = Field(description="The length that each nearby chunks share text.", ge=0)
    unit: ChunkUnit = ChunkUnit.characters

    @model_validator(mode="after")
    def _validate(self):
        if self.chunk_overlap <= 0:
            raise ValueError("chunk_overlap must be > 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        return self

class Chunk(BaseModel):
    text: str = Field(description="The chunk text content.", min_length=1)
    source: Source = Field(description="Origin document this chunk was derived from.")
    page_number: int | None = Field(description="Page this chunk came from. None if source has no page concept.", ge=1, default=None)
    content_type: ContentType = Field(description="Type of content this chunk represents.")
    index: int = Field(description="0-based position of this chunk across the whole document.", ge=0)
    token_count: int = Field(description="Token count computed via tiktoken cl100k_base.", ge=0)
    char_start: int = Field(description="Start character offset within the page text.", ge=0)
    char_end: int = Field(description="End character offset within the page text.", ge=1)

class EmbeddedChunk(BaseModel):
    chunk: Chunk = Field(description="The original chunk this embedding was generated from.")
    embedding: List[float] = Field(description="Dense vector representation of the chunk text.", min_length=1)