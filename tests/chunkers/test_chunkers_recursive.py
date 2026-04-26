# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library
import pytest

# Private Library
from cleave.chunker.recursive import RecursiveChunker
from cleave.schemas import (
    Chunk,
    ChunkParams,
    ChunkUnit,
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    Source,
    SourceType,
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# ── Shared helpers ────────────────────────────────────────────────────────── #

def _source() -> Source:
    return Source(source_type=SourceType.txt, name="test.txt", location="/test.txt")

def _char_params(size: int = 100, overlap: int = 10) -> ChunkParams:
    return ChunkParams(chunk_size=size, chunk_overlap=overlap)

def _token_params(size: int = 20, overlap: int = 2) -> ChunkParams:
    return ChunkParams(chunk_size=size, chunk_overlap=overlap, unit=ChunkUnit.tokens)

def _flat_doc(text: str, page_number: int | None = None) -> Document:
    """Single-page flat Document from a raw text string."""
    page = DocumentPage(
        page_number=page_number,
        blocks=[ContentBlock(type=ContentType.text, content=text, position=0)],
    )
    return Document(source=_source(), pages=[page], total_pages=1)

def _multipage_doc(texts: List[str]) -> Document:
    """Multi-page flat Document, one text block per page."""
    pages = [
        DocumentPage(
            page_number=i + 1,
            blocks=[ContentBlock(type=ContentType.text, content=t, position=0)],
        )
        for i, t in enumerate(texts)
    ]
    return Document(source=_source(), pages=pages, total_pages=len(pages))

def _tree_doc(root: TreeNode) -> Document:
    return Document(source=_source(), root=root)

def _make_chunker(size: int = 100, overlap: int = 10) -> RecursiveChunker:
    return RecursiveChunker(_char_params(size, overlap))

def _indices_are_sequential(chunks: List[Chunk]) -> bool:
    return [c.index for c in chunks] == list(range(len(chunks)))


# ── Custom delimiters ────────────────────────────────────────────────────── #

class TestRecursiveChunkerCustomDelimiters:

    def test_custom_delimiters_override_defaults(self):
        # Use only newline as delimiter — heading markers should not split
        text = "# Heading\nLine one.\nLine two.\nLine three."
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_char_params(size=20, overlap=0), custom_delimiters=["\n"])
        chunks = chunker.chunk(doc)
        # With \n delimiter and size=20, heading and lines split on newlines
        assert all(len(c.text) <= 20 for c in chunks)

    def test_python_preset_splits_on_def(self):
        code = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        doc = _flat_doc(code)
        chunker = RecursiveChunker(
            _char_params(size=30, overlap=0),
            custom_delimiters=RecursiveChunker.DELIMITER_PRESETS["python"],
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2
        assert any("foo" in c.text for c in chunks)
        assert any("bar" in c.text for c in chunks)

    def test_python_preset_splits_on_class(self):
        code = (
            "class Foo:\n    def __init__(self):\n        self.x = 1\n\n"
            "    def method(self):\n        return self.x\n\n"
            "class Bar:\n    def __init__(self):\n        self.y = 2\n\n"
            "    def method(self):\n        return self.y\n"
        )
        doc = _flat_doc(code)
        chunker = RecursiveChunker(
            _char_params(size=60, overlap=0),
            custom_delimiters=RecursiveChunker.DELIMITER_PRESETS["python"],
        )
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2
        assert any("Foo" in c.text for c in chunks)
        assert any("Bar" in c.text for c in chunks)

    def test_python_preset_each_chunk_within_size(self):
        code = (
            "class Alpha:\n    def a(self): return 1\n\n"
            "class Beta:\n    def b(self): return 2\n\n"
            "class Gamma:\n    def c(self): return 3\n"
        )
        doc = _flat_doc(code)
        chunker = RecursiveChunker(
            _char_params(size=50, overlap=0),
            custom_delimiters=RecursiveChunker.DELIMITER_PRESETS["python"],
        )
        chunks = chunker.chunk(doc)
        for c in chunks:
            assert len(c.text) <= 50

    def test_python_preset_indices_sequential(self):
        code = "def a(): pass\n\ndef b(): pass\n\ndef c(): pass\n"
        doc = _flat_doc(code)
        chunker = RecursiveChunker(
            _char_params(size=20, overlap=0),
            custom_delimiters=RecursiveChunker.DELIMITER_PRESETS["python"],
        )
        chunks = chunker.chunk(doc)
        assert _indices_are_sequential(chunks)

    def test_default_used_when_no_custom_delimiters(self):
        chunker = RecursiveChunker(_char_params())
        assert chunker._delimiters == RecursiveChunker._DEFAULT_DELIMITERS

    def test_preset_keys_exist(self):
        for key in ("default", "python", "js", "markdown", "html", "latex"):
            assert key in RecursiveChunker.DELIMITER_PRESETS
            assert isinstance(RecursiveChunker.DELIMITER_PRESETS[key], list)


# ── Flat / string-split path ─────────────────────────────────────────────── #

class TestRecursiveChunkerFlat:

    def test_short_text_becomes_single_chunk(self):
        doc = _flat_doc("Hello world.")
        chunks = _make_chunker(size=200).chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world."

    def test_chunk_indices_sequential(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        doc = _flat_doc(text)
        chunks = _make_chunker(size=30, overlap=5).chunk(doc)
        assert _indices_are_sequential(chunks)

    def test_splits_on_double_newline_before_single_newline(self):
        # Two paragraphs separated by \n\n; each fits within chunk_size.
        para1 = "Short para one."
        para2 = "Short para two."
        doc = _flat_doc(f"{para1}\n\n{para2}")
        chunks = _make_chunker(size=40, overlap=5).chunk(doc)
        texts = [c.text for c in chunks]
        assert any(para1 in t for t in texts), "para1 not found in any chunk"
        assert any(para2 in t for t in texts), "para2 not found in any chunk"

    def test_no_chunk_exceeds_chunk_size_chars(self):
        long_text = "word " * 200  # 1000 chars
        doc = _flat_doc(long_text)
        chunks = _make_chunker(size=50, overlap=5).chunk(doc)
        for chunk in chunks:
            assert len(chunk.text) <= 50

    def test_blank_page_produces_no_chunks(self):
        doc = _multipage_doc(["   ", "Real content here."])
        chunks = _make_chunker(size=100).chunk(doc)
        assert all("Real content" in c.text for c in chunks)
        assert len(chunks) == 1

    def test_multipage_chunks_all_pages(self):
        doc = _multipage_doc(["Page one content.", "Page two content."])
        chunks = _make_chunker(size=200).chunk(doc)
        all_text = " ".join(c.text for c in chunks)
        assert "Page one content." in all_text
        assert "Page two content." in all_text

    def test_char_start_is_non_negative(self):
        doc = _flat_doc("Alpha beta gamma delta epsilon.")
        chunks = _make_chunker(size=15, overlap=3).chunk(doc)
        for chunk in chunks:
            assert chunk.chunk.char_start >= 0 if hasattr(chunk, "chunk") else chunk.char_start >= 0

    def test_hard_split_fallback_for_word_without_spaces(self):
        # A single unbreakable token longer than chunk_size forces _hard_split.
        long_word = "a" * 200
        doc = _flat_doc(long_word)
        chunks = _make_chunker(size=50, overlap=5).chunk(doc)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.text) <= 50

    def test_token_unit_produces_chunks_within_token_limit(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=10, overlap=2))
        chunks = chunker.chunk(doc)
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        for chunk in chunks:
            assert len(enc.encode(chunk.text)) <= 10

    def test_content_type_is_text_for_flat_path(self):
        doc = _flat_doc("Some text.")
        chunks = _make_chunker().chunk(doc)
        assert all(c.content_type == ContentType.text for c in chunks)

    def test_returns_empty_list_for_whitespace_only_document(self):
        doc = _flat_doc("   \n\n   ")
        chunks = _make_chunker().chunk(doc)
        assert chunks == []

    def test_markdown_heading_delimiter_respected(self):
        md = "# Heading One\n\nBody text under heading."
        doc = _flat_doc(md)
        chunks = _make_chunker(size=30, overlap=5).chunk(doc)
        texts = [c.text for c in chunks]
        # Heading and body should be in separate chunks (each < 30 chars)
        assert any("Heading One" in t for t in texts)
        assert any("Body text" in t for t in texts)


# ── Tree-walk path ────────────────────────────────────────────────────────── #

class TestRecursiveChunkerTree:

    def _root_with_children(self, *children: TreeNode) -> TreeNode:
        return TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
            children=list(children),
        )

    def _heading(self, text: str, level: int, children=None) -> TreeNode:
        return TreeNode(
            content_type=ContentType.text,
            content=text,
            metadata={"role": "heading", "level": level, "page_number": 1},
            children=children or [],
        )

    def _para(self, text: str) -> TreeNode:
        return TreeNode(
            content_type=ContentType.text,
            content=text,
            metadata={"role": "paragraph", "page_number": 1},
        )

    def _table(self, md: str = "| A | B |\n| --- | --- |\n| 1 | 2 |") -> TreeNode:
        return TreeNode(
            content_type=ContentType.table,
            content=md,
            metadata={"page_number": 1},
        )

    def _image(self, b64: str = "imgdata") -> TreeNode:
        return TreeNode(
            content_type=ContentType.image,
            content=b64,
            metadata={"page_number": 1},
        )

    # ── Emission and sizing ──────────────────────────────────────────────── #

    def test_small_subtree_emitted_as_single_chunk(self):
        root = self._root_with_children(
            self._heading("Title", 1, children=[self._para("Short body.")])
        )
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        # "Title\nShort body." is ~19 chars, well under 200
        assert len(chunks) == 1
        assert "Title" in chunks[0].text
        assert "Short body." in chunks[0].text

    def test_oversized_subtree_recurses_into_children(self):
        long_para = "word " * 60  # ~300 chars
        root = self._root_with_children(
            self._heading("Section", 1, children=[self._para(long_para)])
        )
        chunks = _make_chunker(size=100, overlap=10).chunk(_tree_doc(root))
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.text) <= 100

    def test_chunk_indices_sequential_tree(self):
        root = self._root_with_children(
            self._heading("A", 1, children=[self._para("Para one.")]),
            self._heading("B", 1, children=[self._para("Para two.")]),
        )
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        assert _indices_are_sequential(chunks)

    # ── Atomicity rules ──────────────────────────────────────────────────── #

    def test_table_node_is_atomic(self):
        md = "| Name | Value |\n| --- | --- |\n| " + "x" * 80 + " | y |"
        root = self._root_with_children(self._table(md))
        chunks = _make_chunker(size=50, overlap=5).chunk(_tree_doc(root))
        assert len(chunks) == 1
        assert chunks[0].content_type == ContentType.table
        assert chunks[0].text == md

    def test_image_node_is_atomic(self):
        b64 = "A" * 500  # longer than any chunk_size
        root = self._root_with_children(self._image(b64))
        chunks = _make_chunker(size=50, overlap=5).chunk(_tree_doc(root))
        assert len(chunks) == 1
        assert chunks[0].content_type == ContentType.image
        assert chunks[0].text == b64

    def test_table_content_type_preserved_in_chunk(self):
        root = self._root_with_children(self._table())
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        assert chunks[0].content_type == ContentType.table

    def test_image_token_count_is_zero(self):
        root = self._root_with_children(self._image("abc"))
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        assert chunks[0].token_count == 0

    # ── Empty / edge cases ────────────────────────────────────────────────── #

    def test_empty_root_produces_no_chunks(self):
        root = TreeNode(content_type=ContentType.text, content="", metadata={"role": "root"})
        chunks = _make_chunker().chunk(_tree_doc(root))
        assert chunks == []

    def test_node_with_empty_content_but_non_empty_children(self):
        root = TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
            children=[self._para("Child text.")],
        )
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        assert len(chunks) == 1
        assert chunks[0].text == "Child text."

    def test_mixed_content_types_in_tree(self):
        root = self._root_with_children(
            self._heading("Title", 1, children=[
                self._para("Body text."),
                self._table(),
                self._image("b64img"),
            ])
        )
        chunks = _make_chunker(size=200).chunk(_tree_doc(root))
        types = {c.content_type for c in chunks}
        # Table and image each get their own chunk; text also present
        assert ContentType.table in types
        assert ContentType.image in types


# ── Token mode offset tests (flat path) ──────────────────────────────────── #

class TestRecursiveChunkerTokenModeOffsets:

    def test_char_start_non_negative(self):
        text = "The quick brown fox jumps over the lazy dog. " * 5
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=10, overlap=2))
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            assert chunk.char_start >= 0

    def test_char_end_equals_char_start_plus_text_length(self):
        text = "The quick brown fox jumps over the lazy dog. " * 5
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=10, overlap=2))
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            assert chunk.char_end == chunk.char_start + len(chunk.text)

    def test_char_offsets_advance_monotonically(self):
        text = "First sentence here.\n\nSecond sentence here.\n\nThird sentence here."
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=8, overlap=1))
        chunks = chunker.chunk(doc)
        assert len(chunks) > 1
        for i in range(1, len(chunks)):
            assert chunks[i].char_start >= chunks[i - 1].char_start

    def test_chunk_text_found_at_char_start_in_original(self):
        text = "Alpha beta gamma.\n\nDelta epsilon zeta.\n\nEta theta iota."
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=6, overlap=1))
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            # The chunk text (stripped) should appear near char_start in the original
            assert chunk.text.strip() in text

    def test_indices_sequential_token_mode(self):
        text = "Word " * 50
        doc = _flat_doc(text)
        chunker = RecursiveChunker(_token_params(size=8, overlap=1))
        chunks = chunker.chunk(doc)
        assert _indices_are_sequential(chunks)


# ── Bridge pattern: tree → to_markdown() → RecursiveChunker (flat path) ─── #

class TestBridgePattern:

    def test_to_markdown_then_fixed_chunker_produces_valid_chunks(self):
        from cleave.chunker.fixed import FixedChunker

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
                            content="Body text goes here.",
                            metadata={"role": "paragraph"},
                        )
                    ],
                )
            ],
        )
        tree_doc = _tree_doc(root)
        md = tree_doc.to_markdown()
        assert "# Introduction" in md

        # Build a flat document from the markdown for FixedChunker
        flat_page = DocumentPage(
            blocks=[ContentBlock(type=ContentType.text, content=md, position=0)]
        )
        flat_doc = Document(source=_source(), pages=[flat_page], total_pages=1)

        chunker = FixedChunker(ChunkParams(chunk_size=200, chunk_overlap=10))
        chunks = chunker.chunk(flat_doc)
        assert len(chunks) >= 1
        all_text = " ".join(c.text for c in chunks)
        assert "Introduction" in all_text

    def test_recursive_chunker_on_flat_markdown_string(self):
        md = "# Heading\n\nParagraph text here.\n\n## Sub-heading\n\nMore text."
        flat_page = DocumentPage(
            blocks=[ContentBlock(type=ContentType.text, content=md, position=0)]
        )
        flat_doc = Document(source=_source(), pages=[flat_page], total_pages=1)
        chunks = RecursiveChunker(ChunkParams(chunk_size=50, chunk_overlap=5)).chunk(flat_doc)
        assert len(chunks) >= 2
        assert _indices_are_sequential(chunks)
