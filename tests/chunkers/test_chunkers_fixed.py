# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Private Library
from cleave.chunker.fixed import FixedChunker
from cleave.schemas import ChunkParams, ContentBlock, ContentType, DocumentPage, Document

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

def _doc(source, text: str, page_number: int | None = 1) -> Document:
    page = DocumentPage(
        page_number=page_number,
        blocks=[ContentBlock(type=ContentType.text, content=text, position=0)],
    )
    return Document(source=source, pages=[page], total_pages=1)

class TestFixedChunkerCharacters:
    def test_single_chunk_when_text_fits(self, source):
        params = ChunkParams(chunk_size=100, chunk_overlap=10)
        chunker = FixedChunker(params)
        doc = _doc(source, "hello world")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].text == "hello world"

    def test_produces_multiple_chunks(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        # 26-char string → step=8 → chunks at i=0,8,16 → 3 chunks
        doc = _doc(source, "abcdefghijklmnopqrstuvwxyz")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 3

    def test_chunk_text_content(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        doc = _doc(source, "abcdefghijklmnopqrstuvwxyz")
        chunks = chunker.chunk(doc)
        assert chunks[0].text == "abcdefghij"
        assert chunks[1].text == "ijklmnopqr"
        assert chunks[2].text == "qrstuvwxyz"

    def test_char_start_offsets(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        doc = _doc(source, "abcdefghijklmnopqrstuvwxyz")
        chunks = chunker.chunk(doc)
        assert chunks[0].char_start == 0
        assert chunks[1].char_start == 8   # step = 10 - 2
        assert chunks[2].char_start == 16

    def test_char_end_equals_start_plus_length(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        doc = _doc(source, "abcdefghijklmnopqrstuvwxyz")
        for chunk in chunker.chunk(doc):
            assert chunk.char_end == chunk.char_start + len(chunk.text)

    def test_global_index_sequential(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        doc = _doc(source, "abcdefghijklmnopqrstuvwxyz")
        chunks = chunker.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_blank_page_is_skipped(self, source):
        params = ChunkParams(chunk_size=10, chunk_overlap=2)
        chunker = FixedChunker(params)
        blank_page = DocumentPage(
            page_number=1,
            blocks=[ContentBlock(type=ContentType.text, content="   ", position=0)],
        )
        doc = Document(source=source, pages=[blank_page], total_pages=1)
        assert chunker.chunk(doc) == []

    def test_multipage_global_index_continues(self, multipage_document, char_params):
        chunker = FixedChunker(char_params)
        chunks = chunker.chunk(multipage_document)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_multipage_page_number_attributed_correctly(self, multipage_document, char_params):
        chunker = FixedChunker(char_params)
        chunks = chunker.chunk(multipage_document)
        page_numbers = {c.page_number for c in chunks}
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_source_propagated_to_chunks(self, source, char_params):
        chunker = FixedChunker(char_params)
        doc = _doc(source, "hello world this is a test sentence for chunking")
        for chunk in chunker.chunk(doc):
            assert chunk.source == source

    def test_content_type_defaults_to_text(self, source, char_params):
        chunker = FixedChunker(char_params)
        doc = _doc(source, "hello world this is a test sentence for chunking")
        for chunk in chunker.chunk(doc):
            assert chunk.content_type == ContentType.text


class TestFixedChunkerTokens:
    def test_produces_chunks_in_token_mode(self, source, token_params):
        chunker = FixedChunker(token_params)
        # Use text long enough to produce more than one token-window chunk.
        doc = _doc(source, "The quick brown fox jumps over the lazy dog and runs away fast.")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

    def test_token_mode_chunk_text_is_nonempty(self, source, token_params):
        chunker = FixedChunker(token_params)
        doc = _doc(source, "The quick brown fox jumps over the lazy dog and runs away fast.")
        for chunk in chunker.chunk(doc):
            assert len(chunk.text) > 0

    def test_token_mode_indices_are_sequential(self, source, token_params):
        chunker = FixedChunker(token_params)
        doc = _doc(source, "The quick brown fox jumps over the lazy dog and runs away fast.")
        chunks = chunker.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
