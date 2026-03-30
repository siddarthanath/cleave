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

    def test_unsupported_type_raises_value_error(self, char_params):
        with pytest.raises(ValueError, match="Unsupported chunker"):
            ChunkerFactory.create(ChunkerType.sentence, char_params)

    def test_semantic_type_raises_value_error(self, char_params):
        with pytest.raises(ValueError, match="Unsupported chunker"):
            ChunkerFactory.create(ChunkerType.semantic, char_params)

    def test_fixed_type_in_registry_not_yet_wired(self, char_params):
        # Registry maps ChunkerType.fixed to Ellipsis until real chunker is wired up.
        with pytest.raises(TypeError):
            ChunkerFactory.create(ChunkerType.fixed, char_params)

    def test_recursive_type_in_registry_not_yet_wired(self, char_params):
        with pytest.raises(TypeError):
            ChunkerFactory.create(ChunkerType.recursive, char_params)
