# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# Private Library
from cleave.parsers.markup.md import MarkdownParser
from cleave.parsers.plain.txt import TextParser
from cleave.schemas import ContentType, Document, SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


# ── TextParser mode behaviour ─────────────────────────────────────────────── #

class TestTextParserMode:

    def test_flat_mode_accepted(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world.", encoding="utf-8")
        doc = TextParser(str(f), mode="flat").parse()
        assert doc.pages is not None
        assert "Hello world." in doc.full_text

    def test_tree_mode_raises_not_implemented(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello.", encoding="utf-8")
        with pytest.raises(NotImplementedError, match="tree"):
            TextParser(str(f), mode="tree")

    def test_invalid_mode_raises_value_error(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello.", encoding="utf-8")
        with pytest.raises(ValueError, match="mode"):
            TextParser(str(f), mode="invalid")

    def test_default_mode_is_flat(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello.", encoding="utf-8")
        doc = TextParser(str(f)).parse()
        assert doc.pages is not None


# ── MarkdownParser flat mode ──────────────────────────────────────────────── #

class TestMarkdownParserFlat:

    def test_returns_document(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert isinstance(doc, Document)

    def test_source_type_is_markdown(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert doc.source.source_type == SourceType.markdown

    def test_single_virtual_page(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert len(doc.pages) == 1

    def test_page_number_is_none(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert doc.pages[0].page_number is None

    def test_root_is_none(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert doc.root is None

    def test_text_extracted(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert len(doc.full_text) > 0

    def test_known_content_in_text(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        text = doc.full_text.lower()
        assert "introduction" in text
        assert "conclusion" in text

    def test_table_extracted(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert len(doc.all_tables) >= 1

    def test_table_is_gfm_format(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "|" in table_md
        assert "---" in table_md

    def test_table_contains_known_values(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "Alpha" in table_md
        assert "Beta" in table_md

    def test_content_types_valid(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}
        for block in doc.pages[0].blocks:
            assert block.type in valid

    def test_blocks_ordered_by_position(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        positions = [b.position for b in doc.pages[0].blocks]
        assert positions == sorted(positions)

    def test_inline_table_not_split_across_blocks(self, tmp_path):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n"
        f = tmp_path / "t.md"
        f.write_text(md, encoding="utf-8")
        doc = MarkdownParser(str(f), mode="flat").parse()
        assert len(doc.all_tables) == 1
        assert "| 1 | 2 |" in doc.all_tables[0].content
        assert "| 3 | 4 |" in doc.all_tables[0].content

    def test_invalid_mode_raises(self, sample_md_path: Path):
        with pytest.raises(ValueError, match="mode"):
            MarkdownParser(str(sample_md_path), mode="bad")

    def test_missing_file_raises(self):
        with pytest.raises(Exception):
            MarkdownParser("/nonexistent/file.md").parse()

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("   \n\n   ", encoding="utf-8")
        with pytest.raises(ValueError):
            MarkdownParser(str(f), mode="flat").parse()

    def test_image_extracted(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        assert len(doc.all_images) >= 1

    def test_image_content_is_data_uri(self, sample_md_path: Path):
        import base64
        doc = MarkdownParser(str(sample_md_path), mode="flat").parse()
        content = doc.all_images[0].content
        assert content.startswith("data:image/")
        b64_data = content.split(",", 1)[1]
        decoded = base64.b64decode(b64_data)
        assert len(decoded) > 0


# ── MarkdownParser tree mode ──────────────────────────────────────────────── #

class TestMarkdownParserTree:

    def test_returns_document(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        assert isinstance(doc, Document)

    def test_root_populated(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        assert doc.root is not None

    def test_pages_is_none(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        assert doc.pages is None

    def test_root_has_children(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        assert len(doc.root.children) >= 1

    def test_heading_nodes_present(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node.content.lower())
            for child in node.children:
                out.extend(find_headings(child))
            return out

        headings = find_headings(doc.root)
        assert any("introduction" in h for h in headings)
        assert any("conclusion" in h for h in headings)

    def test_h1_has_level_1(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()

        def find(node, text):
            if node.content.lower() == text.lower():
                return node
            for child in node.children:
                result = find(child, text)
                if result:
                    return result
            return None

        h1 = find(doc.root, "Sample Document")
        if h1:
            assert h1.metadata["level"] == 1

    def test_h2_has_level_2(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node)
            for child in node.children:
                out.extend(find_headings(child))
            return out

        h2s = [n for n in find_headings(doc.root) if n.metadata.get("level") == 2]
        assert len(h2s) >= 1

    def test_paragraphs_are_children_of_headings(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node)
            for child in node.children:
                out.extend(find_headings(child))
            return out

        for heading in find_headings(doc.root):
            para_children = [
                c for c in heading.children
                if c.metadata.get("role") == "paragraph"
            ]
            # At least some headings should have paragraph children
            if para_children:
                assert all(c.content_type == ContentType.text for c in para_children)

    def test_table_is_atomic_tree_node(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        tables = doc.root.get_nodes_by_type(ContentType.table)
        assert len(tables) >= 1
        assert "|" in tables[0].content
        assert tables[0].children == []

    def test_full_text_contains_known_content(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        text = doc.full_text.lower()
        assert "introduction" in text

    def test_to_markdown_contains_heading_markers(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        md = doc.to_markdown()
        assert "#" in md

    def test_content_types_valid(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}

        def walk(node):
            assert node.content_type in valid
            for child in node.children:
                walk(child)

        walk(doc.root)

    def test_heading_nesting(self, tmp_path):
        md = "# H1\n\n## H2\n\nParagraph.\n\n### H3\n\nDeeper.\n"
        f = tmp_path / "nested.md"
        f.write_text(md, encoding="utf-8")
        doc = MarkdownParser(str(f), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append((node.metadata["level"], node.content))
            for child in node.children:
                out.extend(find_headings(child))
            return out

        levels = [lvl for lvl, _ in find_headings(doc.root)]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels

    def test_source_type_is_markdown(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        assert doc.source.source_type == SourceType.markdown

    def test_image_node_in_tree(self, sample_md_path: Path):
        doc = MarkdownParser(str(sample_md_path), mode="tree").parse()
        images = doc.root.get_nodes_by_type(ContentType.image)
        assert len(images) >= 1
        assert images[0].content
        assert images[0].metadata.get("alt") is not None


# ── Factory integration ───────────────────────────────────────────────────── #

class TestParserFactoryMd:

    def test_factory_creates_markdown_parser(self, sample_md_path: Path):
        from cleave.parsers.factory import ParserFactory
        parser = ParserFactory.create(str(sample_md_path), mode="flat")
        assert isinstance(parser, MarkdownParser)

    def test_factory_creates_text_parser(self, tmp_path):
        from cleave.parsers.factory import ParserFactory
        f = tmp_path / "test.txt"
        f.write_text("Hello.", encoding="utf-8")
        parser = ParserFactory.create(str(f), mode="flat")
        assert isinstance(parser, TextParser)

    def test_factory_txt_tree_mode_raises(self, tmp_path):
        from cleave.parsers.factory import ParserFactory
        f = tmp_path / "test.txt"
        f.write_text("Hello.", encoding="utf-8")
        with pytest.raises(NotImplementedError):
            ParserFactory.create(str(f), mode="tree")
