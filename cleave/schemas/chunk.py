# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import hashlib
from enum import Enum
from typing import Any, Dict, List

# Third Party Library
from pydantic import BaseModel, Field, model_validator

# Private Library
from cleave.schemas.content import ContentType
from cleave.schemas.source import Source

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ChunkerType(str, Enum):
    fixed     = "fixed"
    sentence  = "sentence"
    recursive = "recursive"


class ChunkUnit(str, Enum):
    characters = "characters"
    tokens     = "tokens"


class ChunkParams(BaseModel):
    chunk_size: int = Field(description="The length of each chunk of text.", gt=0)
    chunk_overlap: int = Field(description="The length that each nearby chunk shares with its neighbours.", ge=0)
    unit: ChunkUnit = ChunkUnit.characters
    metadata: Dict[str, Any] = Field(
        description="Arbitrary key-value pairs merged into every Chunk produced with these params.",
        default_factory=dict,
    )

    @model_validator(mode="after")
    def _validate(self) -> "ChunkParams":
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        return self


class Chunk(BaseModel):
    text: str = Field(description="The chunk text content.", min_length=1)
    source: Source = Field(description="Origin document this chunk was derived from.")
    page_number: int | None = Field(
        description="Page this chunk came from. None if source has no page concept.",
        ge=1,
        default=None,
    )
    content_type: ContentType = Field(description="Type of content this chunk represents.")
    index: int = Field(description="0-based position of this chunk across the whole document.", ge=0)
    token_count: int = Field(description="Token count computed via tiktoken cl100k_base.", ge=0)
    char_start: int = Field(description="Start character offset within the page text.", ge=0)
    char_end: int = Field(description="End character offset within the page text.", ge=1)
    metadata: Dict[str, Any] = Field(
        description="Arbitrary key-value pairs forwarded from ChunkParams.metadata.",
        default_factory=dict,
    )
    chunk_id: str = Field(
        description="Deterministic identifier derived from source location and chunk index.",
        default="",
    )

    @model_validator(mode="after")
    def _set_chunk_id(self) -> "Chunk":
        if not self.chunk_id:
            self.chunk_id = hashlib.sha256(
                f"{self.source.location}:{self.index}".encode()
            ).hexdigest()[:16]
        return self


class EmbeddedChunk(BaseModel):
    chunk: Chunk = Field(description="The original chunk this embedding was generated from.")
    embedding: List[float] = Field(description="Dense vector representation of the chunk text.", min_length=1)
    embedding_model: str = Field(description="Name of the model used to produce the embedding vector.")
