# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# Private Library
from cleave.parsers.markup.html import HtmlParser
from cleave.schemas import ContentType, Document, SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


# ── HtmlParser flat mode ──────────────────────────────────────────────────── #

class TestHtmlParserFlat:

    def test_returns_document(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert isinstance(doc, Document)

    def test_source_type_is_html(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert doc.source.source_type == SourceType.html

    def test_single_virtual_page(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert len(doc.pages) == 1

    def test_page_number_is_none(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert doc.pages[0].page_number is None

    def test_root_is_none(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert doc.root is None

    def test_text_extracted(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert len(doc.full_text) > 0

    def test_known_content_in_text(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        text = doc.full_text.lower()
        assert "introduction" in text
        assert "conclusion" in text

    def test_table_extracted(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert len(doc.all_tables) >= 1

    def test_table_is_gfm_format(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "|" in table_md
        assert "---" in table_md

    def test_table_contains_known_values(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "Alpha" in table_md
        assert "Beta" in table_md

    def test_image_extracted(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert len(doc.all_images) >= 1

    def test_image_content_is_base64(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        assert doc.all_images[0].content.startswith("data:image/")

    def test_content_types_valid(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}
        for block in doc.pages[0].blocks:
            assert block.type in valid

    def test_blocks_ordered_by_position(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="flat").parse()
        positions = [b.position for b in doc.pages[0].blocks]
        assert positions == sorted(positions)

    def test_invalid_mode_raises(self, sample_html_path: Path):
        with pytest.raises(ValueError, match="mode"):
            HtmlParser(str(sample_html_path), mode="bad")

    def test_empty_file_raises(self, tmp_path):
        f = tmp_path / "empty.html"
        f.write_text("   ", encoding="utf-8")
        with pytest.raises(ValueError):
            HtmlParser(str(f), mode="flat").parse()

    def test_no_content_elements_raises(self, tmp_path):
        f = tmp_path / "bare.html"
        f.write_text("<html><body></body></html>", encoding="utf-8")
        with pytest.raises(ValueError):
            HtmlParser(str(f), mode="flat").parse()

    def test_inline_table_single_block(self, tmp_path):
        f = tmp_path / "table.html"
        f.write_text(
            "<html><body><table>"
            "<tr><th>A</th><th>B</th></tr>"
            "<tr><td>1</td><td>2</td></tr>"
            "<tr><td>3</td><td>4</td></tr>"
            "</table></body></html>",
            encoding="utf-8",
        )
        doc = HtmlParser(str(f), mode="flat").parse()
        assert len(doc.all_tables) == 1
        assert "1" in doc.all_tables[0].content
        assert "3" in doc.all_tables[0].content


# ── HtmlParser tree mode ──────────────────────────────────────────────────── #

class TestHtmlParserTree:

    def test_returns_document(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        assert isinstance(doc, Document)

    def test_root_populated(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        assert doc.root is not None

    def test_pages_is_none(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        assert doc.pages is None

    def test_root_has_children(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        assert len(doc.root.children) >= 1

    def test_heading_nodes_present(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()

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

    def test_h1_has_level_1(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()

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

    def test_h2_nodes_have_level_2(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node)
            for child in node.children:
                out.extend(find_headings(child))
            return out

        h2s = [n for n in find_headings(doc.root) if n.metadata.get("level") == 2]
        assert len(h2s) >= 1

    def test_paragraphs_are_children_of_headings(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node)
            for child in node.children:
                out.extend(find_headings(child))
            return out

        for heading in find_headings(doc.root):
            para_children = [c for c in heading.children if c.metadata.get("role") == "paragraph"]
            if para_children:
                assert all(c.content_type == ContentType.text for c in para_children)

    def test_table_is_atomic_tree_node(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        tables = doc.root.get_nodes_by_type(ContentType.table)
        assert len(tables) >= 1
        assert "|" in tables[0].content
        assert tables[0].children == []

    def test_image_node_in_tree(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        images = doc.root.get_nodes_by_type(ContentType.image)
        assert len(images) >= 1
        assert images[0].content.startswith("data:image/")
        assert images[0].metadata.get("alt") is not None

    def test_full_text_contains_known_content(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        text = doc.full_text.lower()
        assert "introduction" in text

    def test_to_markdown_contains_heading_markers(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        md = doc.to_markdown()
        assert "#" in md

    def test_content_types_valid(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}

        def walk(node):
            assert node.content_type in valid
            for child in node.children:
                walk(child)

        walk(doc.root)

    def test_heading_nesting(self, tmp_path):
        f = tmp_path / "nested.html"
        f.write_text(
            "<html><body>"
            "<h1>H1</h1><p>Top.</p>"
            "<h2>H2</h2><p>Mid.</p>"
            "<h3>H3</h3><p>Deep.</p>"
            "</body></html>",
            encoding="utf-8",
        )
        doc = HtmlParser(str(f), mode="tree").parse()

        def find_headings(node):
            out = []
            if node.metadata.get("role") == "heading":
                out.append(node.metadata["level"])
            for child in node.children:
                out.extend(find_headings(child))
            return out

        levels = find_headings(doc.root)
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels

    def test_source_type_is_html(self, sample_html_path: Path):
        doc = HtmlParser(str(sample_html_path), mode="tree").parse()
        assert doc.source.source_type == SourceType.html


# ── Factory integration ───────────────────────────────────────────────────── #

class TestParserFactoryHtml:

    def test_factory_creates_html_parser_html_ext(self, sample_html_path: Path):
        from cleave.parsers.factory import ParserFactory
        parser = ParserFactory.create(str(sample_html_path), mode="flat")
        assert isinstance(parser, HtmlParser)

    def test_factory_creates_html_parser_htm_ext(self, tmp_path):
        from cleave.parsers.factory import ParserFactory
        f = tmp_path / "page.htm"
        f.write_text("<html><body><p>Hello.</p></body></html>", encoding="utf-8")
        parser = ParserFactory.create(str(f), mode="flat")
        assert isinstance(parser, HtmlParser)

    def test_factory_html_tree_mode(self, sample_html_path: Path):
        from cleave.parsers.factory import ParserFactory
        parser = ParserFactory.create(str(sample_html_path), mode="tree")
        doc = parser.parse()
        assert doc.root is not None
