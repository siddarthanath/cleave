# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library
import pytest
from pydantic import ValidationError

# Private Library
from cleave.schemas import (
    Chunk,
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    EmbeddedChunk,
    Source,
    SourceType,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Helpers

def _source(**kwargs) -> Source:
    defaults = dict(type=SourceType.pdf, name="doc.pdf", location="/doc.pdf")
    return Source(**(defaults | kwargs))

def _block(content="hello", position=0, type=ContentType.text) -> ContentBlock:
    return ContentBlock(type=type, content=content, position=position)

def _chunk(**kwargs) -> Chunk:
    defaults = dict(
        text="some text",
        source=_source(),
        content_type=ContentType.text,
        index=0,
        token_count=2,
        char_start=0,
        char_end=9,
    )
    return Chunk(**(defaults | kwargs))


class TestSourceType:
    def test_is_str_enum(self):
        assert SourceType.pdf == "pdf"
        assert SourceType.docx == "docx"
        assert SourceType.pptx == "pptx"
        assert SourceType.html == "html"
        assert SourceType.markdown == "markdown"
        assert SourceType.txt == "txt"
        assert SourceType.url == "url"

class TestSource:
    def test_valid(self):
        s = _source()
        assert s.type == SourceType.pdf
        assert s.name == "doc.pdf"
        assert s.location == "/doc.pdf"

    def test_empty_name_invalid(self):
        with pytest.raises(ValidationError):
            _source(name="")

    def test_empty_location_invalid(self):
        with pytest.raises(ValidationError):
            _source(location="")

class TestContentBlock:
    def test_valid(self):
        b = _block(content="Hello", position=0)
        assert b.type == ContentType.text
        assert b.content == "Hello"
        assert b.position == 0

    def test_empty_content_invalid(self):
        with pytest.raises(ValidationError):
            _block(content="")

    def test_negative_position_invalid(self):
        with pytest.raises(ValidationError):
            ContentBlock(type=ContentType.text, content="x", position=-1)

    def test_position_zero_valid(self):
        b = ContentBlock(type=ContentType.text, content="x", position=0)
        assert b.position == 0

class TestDocumentPage:
    def test_text_joins_in_position_order(self):
        blocks = [
            _block(content="Second", position=1),
            _block(content="First", position=0),
        ]
        page = DocumentPage(page_number=1, blocks=blocks)
        assert page.text == "First\nSecond"

    def test_text_excludes_images_and_tables(self):
        blocks = [
            _block(content="text content", position=0),
            _block(content="base64img", position=1, type=ContentType.image),
            _block(content="| a | b |", position=2, type=ContentType.table),
        ]
        page = DocumentPage(page_number=1, blocks=blocks)
        assert page.text == "text content"

    def test_images_filters_correctly(self):
        blocks = [
            _block(content="text", position=0),
            _block(content="img1", position=1, type=ContentType.image),
            _block(content="img2", position=2, type=ContentType.image),
        ]
        page = DocumentPage(blocks=blocks)
        assert len(page.images) == 2
        assert all(b.type == ContentType.image for b in page.images)

    def test_tables_filters_correctly(self):
        blocks = [
            _block(content="text", position=0),
            _block(content="| a |", position=1, type=ContentType.table),
        ]
        page = DocumentPage(blocks=blocks)
        assert len(page.tables) == 1
        assert page.tables[0].type == ContentType.table

    def test_empty_blocks(self):
        page = DocumentPage(blocks=[])
        assert page.text == ""
        assert page.images == []
        assert page.tables == []

    def test_page_number_none_allowed(self):
        page = DocumentPage(page_number=None, blocks=[])
        assert page.page_number is None

    def test_page_number_zero_invalid(self):
        with pytest.raises(ValidationError):
            DocumentPage(page_number=0, blocks=[])

    def test_page_number_negative_invalid(self):
        with pytest.raises(ValidationError):
            DocumentPage(page_number=-1, blocks=[])

class TestDocument:
    def _make(self) -> Document:
        source = _source()
        page1 = DocumentPage(page_number=1, blocks=[
            _block(content="Page one text", position=0),
            _block(content="img_data", position=1, type=ContentType.image),
        ])
        page2 = DocumentPage(page_number=2, blocks=[
            _block(content="Page two text", position=0),
            _block(content="| x | y |", position=1, type=ContentType.table),
        ])
        return Document(source=source, pages=[page1, page2], total_pages=2)

    def test_full_text_joins_pages(self):
        assert self._make().full_text == "Page one text\nPage two text"

    def test_all_images_across_pages(self):
        doc = self._make()
        assert len(doc.all_images) == 1
        assert doc.all_images[0].content == "img_data"

    def test_all_tables_across_pages(self):
        doc = self._make()
        assert len(doc.all_tables) == 1
        assert doc.all_tables[0].content == "| x | y |"

    def test_empty_pages_invalid(self):
        with pytest.raises(ValidationError):
            Document(source=_source(), pages=[], total_pages=0)

    def test_total_pages_zero_invalid(self):
        with pytest.raises(ValidationError):
            Document(source=_source(), pages=[DocumentPage(blocks=[])], total_pages=0)

    def test_multiple_images_collected(self):
        source = _source()
        page1 = DocumentPage(blocks=[_block(content="img1", position=0, type=ContentType.image)])
        page2 = DocumentPage(blocks=[_block(content="img2", position=0, type=ContentType.image)])
        doc = Document(source=source, pages=[page1, page2], total_pages=2)
        assert len(doc.all_images) == 2

    def test_full_text_page_with_no_text_contributes_empty_string(self):
        source = _source()
        page1 = DocumentPage(blocks=[_block(content="text", position=0)])
        page2 = DocumentPage(blocks=[_block(content="img", position=0, type=ContentType.image)])
        doc = Document(source=source, pages=[page1, page2], total_pages=2)
        assert doc.full_text == "text\n"

class TestChunk:
    def test_valid(self):
        c = _chunk()
        assert c.text == "some text"
        assert c.index == 0
        assert c.token_count == 2

    def test_empty_text_invalid(self):
        with pytest.raises(ValidationError):
            _chunk(text="")

    def test_token_count_zero_valid(self):
        assert _chunk(token_count=0).token_count == 0

    def test_negative_index_invalid(self):
        with pytest.raises(ValidationError):
            _chunk(index=-1)

    def test_negative_char_start_invalid(self):
        with pytest.raises(ValidationError):
            _chunk(char_start=-1)

    def test_char_end_zero_invalid(self):
        with pytest.raises(ValidationError):
            _chunk(char_end=0)

    def test_page_number_none_allowed(self):
        assert _chunk(page_number=None).page_number is None

    def test_page_number_zero_invalid(self):
        with pytest.raises(ValidationError):
            _chunk(page_number=0)

class TestEmbeddedChunk:
    def test_valid(self):
        ec = EmbeddedChunk(chunk=_chunk(), embedding=[0.1, 0.2, 0.3])
        assert len(ec.embedding) == 3
        assert ec.embedding[0] == pytest.approx(0.1)

    def test_empty_embedding_invalid(self):
        with pytest.raises(ValidationError):
            EmbeddedChunk(chunk=_chunk(), embedding=[])
