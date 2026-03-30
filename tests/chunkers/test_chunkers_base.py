# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library
import pytest

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import Chunk, ContentType, Document

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class DummyChunker(BaseChunker):
    def chunk(self, document: Document) -> List[Chunk]:
        return []


class TestMeasure:
    def test_characters_mode_returns_string_length(self, dummy_chunker):
        assert dummy_chunker._measure("hello world") == 11

    def test_tokens_mode_returns_token_count(self, token_params, source):
        chunker = DummyChunker(token_params)
        text = "hello world"
        assert chunker._measure(text) == chunker._count_tokens(text)

    def test_empty_string_characters(self, dummy_chunker):
        assert dummy_chunker._measure("") == 0


class TestCountTokens:
    def test_non_empty_string_returns_positive_count(self, dummy_chunker):
        assert dummy_chunker._count_tokens("hello world") > 0

    def test_empty_string_returns_zero(self, dummy_chunker):
        assert dummy_chunker._count_tokens("") == 0

    def test_longer_text_produces_more_tokens(self, dummy_chunker):
        short = dummy_chunker._count_tokens("hi")
        long_ = dummy_chunker._count_tokens("hello world, this is a much longer sentence")
        assert long_ > short

    def test_sample_text_token_count(self, dummy_chunker, sample_text):
        assert dummy_chunker._count_tokens(sample_text) > 0


class TestMakeChunk:
    def test_text_chunk_fields(self, dummy_chunker, source):
        chunk = dummy_chunker.make_chunk("hello world", source, 1, 0, 5, ContentType.text)
        assert chunk.text == "hello world"
        assert chunk.content_type == ContentType.text
        assert chunk.index == 0
        assert chunk.char_start == 5
        assert chunk.char_end == 5 + len("hello world")
        assert chunk.page_number == 1
        assert chunk.source == source
        assert chunk.token_count >= 1

    def test_table_chunk_content_type(self, dummy_chunker, source):
        chunk = dummy_chunker.make_chunk("| a | b |", source, 1, 0, 0, ContentType.table)
        assert chunk.content_type == ContentType.table

    def test_page_number_none(self, dummy_chunker, source):
        chunk = dummy_chunker.make_chunk("hello", source, None, 0, 0, ContentType.text)
        assert chunk.page_number is None

    def test_index_value(self, dummy_chunker, source):
        chunk = dummy_chunker.make_chunk("hello", source, 1, 7, 0, ContentType.text)
        assert chunk.index == 7

    def test_image_chunk_token_count_is_zero(self, dummy_chunker, source):
        chunk = dummy_chunker.make_chunk("base64data", source, 1, 0, 0, ContentType.image)
        assert chunk.content_type == ContentType.image
        assert chunk.token_count == 0

    def test_unsupported_content_type_raises(self, dummy_chunker, source):
        with pytest.raises((ValueError, AttributeError)):
            dummy_chunker.make_chunk("text", source, 1, 0, 0, "unsupported")  # type: ignore[arg-type]
