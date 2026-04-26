# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# Private Library
from cleave.parsers.office.docx import DocxParser
from cleave.schemas import ContentType, Document, SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

pytestmark = pytest.mark.usefixtures("sample_docx_path")


# ── Flat mode ─────────────────────────────────────────────────────────────── #

class TestDocxParserFlat:

    def test_returns_document(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert isinstance(doc, Document)

    def test_source_type_is_docx(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert doc.source.source_type == SourceType.docx

    def test_single_virtual_page(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert doc.pages is not None
        assert len(doc.pages) == 1

    def test_page_number_is_none(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert doc.pages[0].page_number is None

    def test_root_is_none_in_flat_mode(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert doc.root is None

    def test_text_extracted(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert len(doc.full_text) > 0

    def test_known_headings_in_text(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        text = doc.full_text.lower()
        assert "introduction" in text
        assert "conclusion" in text

    def test_table_extracted_as_markdown(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        tables = doc.all_tables
        assert len(tables) >= 1
        # GFM table has pipe characters
        assert "|" in tables[0].content

    def test_table_has_header_separator_row(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "---" in table_md

    def test_fixture_table_contains_known_values(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        table_md = doc.all_tables[0].content
        assert "Alpha" in table_md
        assert "Beta" in table_md

    def test_content_types_are_valid(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}
        for block in doc.pages[0].blocks:
            assert block.type in valid

    def test_invalid_mode_raises(self, sample_docx_path: Path):
        with pytest.raises(ValueError, match="mode"):
            DocxParser(str(sample_docx_path), mode="bad")

    def test_missing_file_raises(self):
        with pytest.raises(Exception):
            DocxParser("/nonexistent/file.docx").parse()

    def test_image_extracted(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        assert len(doc.all_images) >= 1

    def test_image_content_is_valid_base64(self, sample_docx_path: Path):
        import base64
        doc = DocxParser(str(sample_docx_path), mode="flat").parse()
        decoded = base64.b64decode(doc.all_images[0].content)
        assert len(decoded) > 0


# ── Tree mode ──────────────────────────────────────────────────────────────── #

class TestDocxParserTree:

    def test_returns_document(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        assert isinstance(doc, Document)

    def test_root_populated(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        assert doc.root is not None

    def test_pages_is_none_in_tree_mode(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        assert doc.pages is None

    def test_root_has_children(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        assert len(doc.root.children) >= 1

    def test_heading_nodes_present(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()

        def find_headings(node):
            headings = []
            if node.metadata.get("role") == "heading":
                headings.append(node.content)
            for child in node.children:
                headings.extend(find_headings(child))
            return headings

        headings = find_headings(doc.root)
        assert len(headings) >= 1

    def test_known_headings_in_tree(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()

        def find_headings(node):
            headings = []
            if node.metadata.get("role") == "heading":
                headings.append(node.content.lower())
            for child in node.children:
                headings.extend(find_headings(child))
            return headings

        headings = find_headings(doc.root)
        heading_text = " ".join(headings)
        assert "introduction" in heading_text
        assert "conclusion" in heading_text

    def test_heading_levels_are_positive_integers(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()

        def check_levels(node):
            if node.metadata.get("role") == "heading":
                level = node.metadata.get("level")
                assert isinstance(level, int)
                assert level >= 1
            for child in node.children:
                check_levels(child)

        check_levels(doc.root)

    def test_h1_heading_has_level_1(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()

        def find_by_content(node, text):
            if node.content.lower() == text.lower():
                return node
            for child in node.children:
                result = find_by_content(child, text)
                if result:
                    return result
            return None

        h1 = find_by_content(doc.root, "Sample Document")
        if h1:
            assert h1.metadata.get("level") == 1

    def test_table_in_tree_is_atomic(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        from cleave.schemas import ContentType

        def find_tables(node):
            tables = []
            if node.content_type == ContentType.table:
                tables.append(node)
            for child in node.children:
                tables.extend(find_tables(child))
            return tables

        tables = find_tables(doc.root)
        assert len(tables) >= 1
        assert "|" in tables[0].content

    def test_table_node_has_no_children(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        from cleave.schemas import ContentType

        def check(node):
            if node.content_type == ContentType.table:
                assert node.children == []
            for child in node.children:
                check(child)

        check(doc.root)

    def test_paragraph_nodes_have_paragraph_role(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()

        def check(node):
            if node.metadata.get("role") == "paragraph":
                assert node.content_type == ContentType.text
                assert len(node.content) > 0
            for child in node.children:
                check(child)

        check(doc.root)

    def test_full_text_contains_known_content(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        text = doc.full_text.lower()
        assert "introduction" in text

    def test_to_markdown_contains_heading_markers(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        md = doc.to_markdown()
        assert "#" in md

    def test_content_types_valid_in_tree(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}

        def walk(node):
            assert node.content_type in valid
            for child in node.children:
                walk(child)

        walk(doc.root)

    def test_image_node_in_tree(self, sample_docx_path: Path):
        doc = DocxParser(str(sample_docx_path), mode="tree").parse()
        images = doc.root.get_nodes_by_type(ContentType.image)
        assert len(images) >= 1
        assert images[0].content
