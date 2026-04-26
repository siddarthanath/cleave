# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party Library
import pytest

# Private Library
from cleave.chunker.factory import ChunkerFactory
from cleave.schemas import ChunkerType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TestChunkerFactoryRegistry:
    def test_fixed_type_in_registry(self):
        assert ChunkerType.fixed in ChunkerFactory._CHUNKER_REGISTRY

    def test_recursive_type_in_registry(self):
        assert ChunkerType.recursive in ChunkerFactory._CHUNKER_REGISTRY

    def test_fixed_type_creates_chunker(self, char_params):
        from cleave.chunker.fixed import FixedChunker
        assert isinstance(ChunkerFactory.create(ChunkerType.fixed, char_params), FixedChunker)

    def test_sentence_type_creates_chunker(self, char_params):
        from cleave.chunker.sentence import SentenceChunker
        assert isinstance(ChunkerFactory.create(ChunkerType.sentence, char_params), SentenceChunker)

    def test_recursive_type_creates_chunker(self, char_params):
        from cleave.chunker.recursive import RecursiveChunker
        assert isinstance(ChunkerFactory.create(ChunkerType.recursive, char_params), RecursiveChunker)
