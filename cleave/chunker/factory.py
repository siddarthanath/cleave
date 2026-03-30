# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Dict

# Third Party Library

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import ChunkParams, ChunkerType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class ChunkerFactory:
    
    _CHUNKER_REGISTRY : Dict[ChunkerType, type[BaseChunker]] = {ChunkerType.fixed: ...,
                                                                ChunkerType.recursive: ...}

    @classmethod
    def create(cls, chunk_type: ChunkerType, chunk_params: ChunkParams) -> BaseChunker:
        """This function dynamically creates a Chunker object from the input path.

        Args:
            chunk_type (ChunkerType): The chunker enum.
            chunk_params (ChunkParams): File path to local document or URL.

        Raises:
            ValueError: If chunker type is not supported.

        Returns:
            BaseChunker: Chunker object.
        """ 
        if chunk_type not in cls._CHUNKER_REGISTRY:
            raise ValueError(f"Unsupported chunker: '{chunk_type}'")
        return cls._CHUNKER_REGISTRY[chunk_type](chunk_params=chunk_params)