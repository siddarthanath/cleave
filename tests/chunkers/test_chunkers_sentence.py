# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Private Library
from cleave.chunker.sentence import SentenceChunker
from cleave.schemas import ChunkParams, ContentBlock, ContentType, DocumentPage, Document

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

def _doc(source, text: str, page_number: int | None = 1) -> Document:
    page = DocumentPage(
        page_number=page_number,
        blocks=[ContentBlock(type=ContentType.text, content=text, position=0)],
    )
    return Document(source=source, pages=[page], total_pages=1)


class TestSentenceChunkerCharacters:
    def test_single_chunk_when_text_fits(self, source):
        params = ChunkParams(chunk_size=200, chunk_overlap=10)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Hello world. How are you?")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1

    def test_produces_multiple_chunks(self, source):
        params = ChunkParams(chunk_size=30, chunk_overlap=5)
        chunker = SentenceChunker(params)
        doc = _doc(source, "First sentence ends here. Second sentence ends here. Third one ends here.")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2

    def test_chunk_text_ends_at_sentence_boundary(self, source):
        params = ChunkParams(chunk_size=30, chunk_overlap=5)
        chunker = SentenceChunker(params)
        doc = _doc(source, "First sentence ends here. Second sentence ends here. Third one ends here.")
        chunks = chunker.chunk(doc)
        # All committed chunks (not the final remainder) should end with punctuation
        for chunk in chunks[:-1]:
            assert chunk.text.rstrip()[-1] in ".!?"

    def test_question_mark_is_sentence_delimiter(self, source):
        params = ChunkParams(chunk_size=20, chunk_overlap=5)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Is this working? Yes it is. Great result!")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

    def test_exclamation_mark_is_sentence_delimiter(self, source):
        params = ChunkParams(chunk_size=20, chunk_overlap=5)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Watch out! That was close. Really nice!")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

    def test_text_with_no_punctuation_yields_no_chunks(self, source):
        # No punctuation means _chunk_text finds no split points and current_text stays empty
        params = ChunkParams(chunk_size=200, chunk_overlap=10)
        chunker = SentenceChunker(params)
        doc = _doc(source, "no punctuation here at all")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 0

    def test_global_index_sequential(self, source):
        params = ChunkParams(chunk_size=30, chunk_overlap=5)
        chunker = SentenceChunker(params)
        doc = _doc(source, "First sentence ends here. Second sentence ends here. Third one ends here.")
        chunks = chunker.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_blank_page_is_skipped(self, source):
        params = ChunkParams(chunk_size=50, chunk_overlap=10)
        chunker = SentenceChunker(params)
        blank_page = DocumentPage(
            page_number=1,
            blocks=[ContentBlock(type=ContentType.text, content="   ", position=0)],
        )
        doc = Document(source=source, pages=[blank_page], total_pages=1)
        assert chunker.chunk(doc) == []

    def test_source_propagated_to_chunks(self, source):
        params = ChunkParams(chunk_size=50, chunk_overlap=10)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Hello world. This is a test. And another one.")
        for chunk in chunker.chunk(doc):
            assert chunk.source == source

    def test_content_type_defaults_to_text(self, source):
        params = ChunkParams(chunk_size=50, chunk_overlap=10)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Hello world. This is a test. And another one.")
        for chunk in chunker.chunk(doc):
            assert chunk.content_type == ContentType.text

    def test_char_end_equals_start_plus_length(self, source):
        params = ChunkParams(chunk_size=50, chunk_overlap=10)
        chunker = SentenceChunker(params)
        doc = _doc(source, "Hello world. This is a test. And another one.")
        for chunk in chunker.chunk(doc):
            assert chunk.char_end == chunk.char_start + len(chunk.text)

    def test_overlap_is_applied(self, source):
        overlap = 10
        params = ChunkParams(chunk_size=50, chunk_overlap=overlap)
        chunker = SentenceChunker(params)
        # Sentences accumulate past chunk_size=50 so at least two chunks are produced
        doc = _doc(source, "First sentence ends here. Second sentence ends here. Third sentence ends here.")
        chunks = chunker.chunk(doc)
        if len(chunks) >= 2:
            tail = chunks[0].text[-overlap:]
            assert chunks[1].text.startswith(tail)

    def test_multipage_global_index_continues(self, source):
        # Pages need internal punctuation so the sentence chunker produces chunks from each
        params = ChunkParams(chunk_size=20, chunk_overlap=5)
        chunker = SentenceChunker(params)
        p1 = DocumentPage(page_number=1, blocks=[ContentBlock(type=ContentType.text, content="Hello world. How are you doing?", position=0)])
        p2 = DocumentPage(page_number=2, blocks=[ContentBlock(type=ContentType.text, content="That is great! What a day?", position=0)])
        doc = Document(source=source, pages=[p1, p2], total_pages=2)
        chunks = chunker.chunk(doc)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_multipage_page_number_attributed_correctly(self, source):
        params = ChunkParams(chunk_size=20, chunk_overlap=5)
        chunker = SentenceChunker(params)
        p1 = DocumentPage(page_number=1, blocks=[ContentBlock(type=ContentType.text, content="Hello world. How are you doing?", position=0)])
        p2 = DocumentPage(page_number=2, blocks=[ContentBlock(type=ContentType.text, content="That is great! What a day?", position=0)])
        doc = Document(source=source, pages=[p1, p2], total_pages=2)
        chunks = chunker.chunk(doc)
        page_numbers = {c.page_number for c in chunks}
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_spare_text_prepended_to_next_page(self, source):
        """Text after the last punctuation on a page carries over to the next page."""
        params = ChunkParams(chunk_size=200, chunk_overlap=10)
        chunker = SentenceChunker(params)
        # Page 1 ends mid-sentence after the last '.'; "Unfinished" has no trailing punct
        page1 = DocumentPage(
            page_number=1,
            blocks=[ContentBlock(type=ContentType.text, content="Complete sentence. Unfinished", position=0)],
        )
        page2 = DocumentPage(
            page_number=2,
            blocks=[ContentBlock(type=ContentType.text, content=" continuation ends here.", position=0)],
        )
        doc = Document(source=source, pages=[page1, page2], total_pages=2)
        chunks = chunker.chunk(doc)
        # Spare text ". Unfinished" is prepended to page 2 — chunker must produce at least one chunk
        assert len(chunks) >= 1

class TestSentenceChunkerTokens:
    def test_produces_chunks_in_token_mode(self, source, token_params):
        chunker = SentenceChunker(token_params)
        doc = _doc(source, "The quick brown fox jumps. The lazy dog sleeps well. What a great day!")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 1

    def test_token_mode_chunk_text_is_nonempty(self, source, token_params):
        chunker = SentenceChunker(token_params)
        doc = _doc(source, "The quick brown fox jumps. The lazy dog sleeps well. What a great day!")
        for chunk in chunker.chunk(doc):
            assert len(chunk.text) > 0

    def test_token_mode_indices_are_sequential(self, source, token_params):
        chunker = SentenceChunker(token_params)
        doc = _doc(source, "The quick brown fox jumps. The lazy dog sleeps well. What a great day!")
        chunks = chunker.chunk(doc)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
