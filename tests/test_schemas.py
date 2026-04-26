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
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Helpers

def _source(**kwargs) -> Source:
    defaults = dict(source_type=SourceType.pdf, name="doc.pdf", location="/doc.pdf")
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

def _flat_document(**kwargs) -> Document:
    defaults = dict(
        source=_source(),
        pages=[DocumentPage(page_number=1, blocks=[_block(content="Page one text")])],
        total_pages=1,
    )
    return Document(**(defaults | kwargs))

def _tree_document(**kwargs) -> Document:
    root = TreeNode(
        content_type=ContentType.text,
        content="Root",
        metadata={"role": "root"},
    )
    defaults = dict(source=_source(), root=root)
    return Document(**(defaults | kwargs))


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
        assert s.source_type == SourceType.pdf
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

class TestTreeNode:
    def _heading(self, text: str, level: int, children=None) -> TreeNode:
        return TreeNode(
            content_type=ContentType.text,
            content=text,
            metadata={"role": "heading", "level": level},
            children=children or [],
        )

    def _para(self, text: str) -> TreeNode:
        return TreeNode(
            content_type=ContentType.text,
            content=text,
            metadata={"role": "paragraph"},
        )

    def _image(self, b64: str = "abc123") -> TreeNode:
        return TreeNode(
            content_type=ContentType.image,
            content=b64,
            metadata={"alt": "fig"},
        )

    def _table(self, md: str = "| a | b |\n| --- | --- |") -> TreeNode:
        return TreeNode(
            content_type=ContentType.table,
            content=md,
        )

    # ── Construction ──────────────────────────────────────────────────────── #

    def test_defaults(self):
        node = TreeNode(content_type=ContentType.text)
        assert node.content == ""
        assert node.children == []
        assert node.metadata == {}

    def test_children_are_ordered(self):
        parent = self._heading("Title", 1, children=[
            self._para("First"),
            self._para("Second"),
        ])
        assert parent.children[0].content == "First"
        assert parent.children[1].content == "Second"

    # ── get_full_text ──────────────────────────────────────────────────────── #

    def test_get_full_text_leaf(self):
        node = self._para("Hello world")
        assert node.get_full_text() == "Hello world"

    def test_get_full_text_recursive(self):
        root = TreeNode(
            content_type=ContentType.text,
            content="Root",
            children=[
                self._para("Child one"),
                self._para("Child two"),
            ],
        )
        assert root.get_full_text() == "Root\nChild one\nChild two"

    def test_get_full_text_skips_images(self):
        root = TreeNode(
            content_type=ContentType.text,
            content="Text",
            children=[self._image("base64data")],
        )
        assert root.get_full_text() == "Text"

    def test_get_full_text_image_node_returns_empty(self):
        assert self._image().get_full_text() == ""

    def test_get_full_text_empty_content_node(self):
        root = TreeNode(
            content_type=ContentType.text,
            content="",
            children=[self._para("child")],
        )
        assert root.get_full_text() == "child"

    # ── get_nodes_by_type ─────────────────────────────────────────────────── #

    def test_get_nodes_by_type_self_match(self):
        img = self._image()
        result = img.get_nodes_by_type(ContentType.image)
        assert result == [img]

    def test_get_nodes_by_type_dfs_order(self):
        root = TreeNode(
            content_type=ContentType.text,
            content="root",
            children=[
                self._image("img1"),
                TreeNode(
                    content_type=ContentType.text,
                    content="section",
                    children=[self._image("img2")],
                ),
            ],
        )
        imgs = root.get_nodes_by_type(ContentType.image)
        assert len(imgs) == 2
        assert imgs[0].content == "img1"
        assert imgs[1].content == "img2"

    def test_get_nodes_by_type_no_match(self):
        root = self._para("no tables here")
        assert root.get_nodes_by_type(ContentType.table) == []

    # ── to_markdown ───────────────────────────────────────────────────────── #

    def test_to_markdown_heading(self):
        node = self._heading("My Title", level=1)
        assert node.to_markdown() == "# My Title"

    def test_to_markdown_heading_level_2(self):
        node = self._heading("Section", level=2)
        assert node.to_markdown() == "## Section"

    def test_to_markdown_paragraph(self):
        node = self._para("Some text.")
        assert node.to_markdown() == "Some text."

    def test_to_markdown_table_verbatim(self):
        md = "| a | b |\n| --- | --- |"
        node = self._table(md)
        assert node.to_markdown() == md

    def test_to_markdown_image_uses_alt(self):
        node = TreeNode(
            content_type=ContentType.image,
            content="b64",
            metadata={"alt": "diagram", "src": ""},
        )
        assert "diagram" in node.to_markdown()

    def test_to_markdown_nested(self):
        root = self._heading("Title", 1, children=[
            self._para("Paragraph text."),
        ])
        md = root.to_markdown()
        assert "# Title" in md
        assert "Paragraph text." in md

    def test_to_markdown_heading_level_clamped_to_6(self):
        node = self._heading("Deep", level=9)
        assert node.to_markdown().startswith("######")

    def test_to_markdown_empty_node_returns_empty(self):
        node = TreeNode(content_type=ContentType.text, content="")
        assert node.to_markdown() == ""


class TestDocument:
    def _make_flat(self) -> Document:
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

    def _make_tree(self) -> Document:
        root = TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
            children=[
                TreeNode(
                    content_type=ContentType.text,
                    content="Introduction",
                    metadata={"role": "heading", "level": 1},
                    children=[
                        TreeNode(
                            content_type=ContentType.text,
                            content="Body paragraph.",
                            metadata={"role": "paragraph"},
                        ),
                        TreeNode(
                            content_type=ContentType.image,
                            content="img_b64",
                            metadata={},
                        ),
                        TreeNode(
                            content_type=ContentType.table,
                            content="| a | b |",
                            metadata={},
                        ),
                    ],
                )
            ],
        )
        return Document(source=_source(), root=root)

    # ── Flat document ─────────────────────────────────────────────────────── #

    def test_flat_full_text_joins_pages(self):
        assert self._make_flat().full_text == "Page one text\nPage two text"

    def test_flat_all_images_across_pages(self):
        doc = self._make_flat()
        assert len(doc.all_images) == 1
        assert doc.all_images[0].content == "img_data"

    def test_flat_all_tables_across_pages(self):
        doc = self._make_flat()
        assert len(doc.all_tables) == 1
        assert doc.all_tables[0].content == "| x | y |"

    def test_flat_to_markdown_joins_with_double_newline(self):
        md = self._make_flat().to_markdown()
        assert "Page one text" in md
        assert "Page two text" in md

    def test_flat_full_text_page_with_no_text_contributes_empty_string(self):
        source = _source()
        page1 = DocumentPage(blocks=[_block(content="text", position=0)])
        page2 = DocumentPage(blocks=[_block(content="img", position=0, type=ContentType.image)])
        doc = Document(source=source, pages=[page1, page2], total_pages=2)
        assert doc.full_text == "text\n"

    # ── Tree document ──────────────────────────────────────────────────────── #

    def test_tree_full_text_uses_root(self):
        doc = self._make_tree()
        text = doc.full_text
        assert "Introduction" in text
        assert "Body paragraph." in text

    def test_tree_all_images_collected(self):
        doc = self._make_tree()
        imgs = doc.all_images
        assert len(imgs) == 1
        assert imgs[0].content == "img_b64"
        assert imgs[0].type == ContentType.image

    def test_tree_all_tables_collected(self):
        doc = self._make_tree()
        tables = doc.all_tables
        assert len(tables) == 1
        assert tables[0].content == "| a | b |"
        assert tables[0].type == ContentType.table

    def test_tree_to_markdown_contains_heading(self):
        md = self._make_tree().to_markdown()
        assert "# Introduction" in md
        assert "Body paragraph." in md

    # ── Validation ────────────────────────────────────────────────────────── #

    def test_neither_pages_nor_root_invalid(self):
        with pytest.raises(ValidationError):
            Document(source=_source())

    def test_both_pages_and_root_invalid(self):
        root = TreeNode(content_type=ContentType.text, content="x")
        page = DocumentPage(blocks=[_block()])
        with pytest.raises(ValidationError):
            Document(source=_source(), pages=[page], total_pages=1, root=root)

    def test_empty_pages_invalid(self):
        with pytest.raises(ValidationError):
            Document(source=_source(), pages=[], total_pages=0)

    def test_total_pages_zero_invalid(self):
        with pytest.raises(ValidationError):
            Document(source=_source(), pages=[DocumentPage(blocks=[])], total_pages=0)

    def test_tree_document_does_not_require_total_pages(self):
        doc = _tree_document()
        assert doc.total_pages is None
        assert doc.pages is None

    def test_multiple_images_collected_flat(self):
        source = _source()
        page1 = DocumentPage(blocks=[_block(content="img1", position=0, type=ContentType.image)])
        page2 = DocumentPage(blocks=[_block(content="img2", position=0, type=ContentType.image)])
        doc = Document(source=source, pages=[page1, page2], total_pages=2)
        assert len(doc.all_images) == 2


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
        ec = EmbeddedChunk(chunk=_chunk(), embedding=[0.1, 0.2, 0.3], embedding_model="text-embedding-3-small")
        assert len(ec.embedding) == 3
        assert ec.embedding[0] == pytest.approx(0.1)

    def test_empty_embedding_invalid(self):
        with pytest.raises(ValidationError):
            EmbeddedChunk(chunk=_chunk(), embedding=[])
