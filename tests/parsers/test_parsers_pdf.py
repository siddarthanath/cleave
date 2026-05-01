# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# Private Library
from cleave.parsers.office.pdf import PdfParser
from cleave.schemas import ContentType, Document, SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

pytestmark = pytest.mark.usefixtures("sample_pdf_path")


# ── Flat mode ─────────────────────────────────────────────────────────────── #

class TestPdfParserFlat:

    def test_returns_document(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert isinstance(doc, Document)

    def test_source_type_is_pdf(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert doc.source.source_type == SourceType.pdf

    def test_pages_populated(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert doc.pages is not None
        assert len(doc.pages) >= 1

    def test_root_is_none_in_flat_mode(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert doc.root is None

    def test_total_pages_matches_pages_length(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert doc.total_pages == len(doc.pages)

    def test_text_extracted(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        full = doc.full_text
        assert len(full) > 0

    def test_known_content_present(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        full = doc.full_text
        # The fixture contains these strings — case-insensitive check for PDF rendering quirks
        assert "introduction" in full.lower() or "sample" in full.lower()

    def test_page_number_starts_at_1(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert doc.pages[0].page_number == 1

    def test_each_page_has_at_least_one_block(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        for page in doc.pages:
            assert len(page.blocks) >= 1

    def test_content_types_are_valid(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}
        for page in doc.pages:
            for block in page.blocks:
                assert block.type in valid

    def test_invalid_mode_raises(self, sample_pdf_path: Path):
        with pytest.raises(ValueError, match="mode"):
            PdfParser(str(sample_pdf_path), mode="invalid")

    def test_missing_file_raises(self):
        with pytest.raises(Exception):
            PdfParser("/nonexistent/path/file.pdf").parse()

    def test_image_extracted(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        assert len(doc.all_images) >= 1

    def test_image_content_is_valid_base64(self, sample_pdf_path: Path):
        import base64
        doc = PdfParser(str(sample_pdf_path), mode="flat").parse()
        decoded = base64.b64decode(doc.all_images[0].content)
        assert len(decoded) > 0


# ── Tree mode ──────────────────────────────────────────────────────────────── #

class TestPdfParserTree:

    def test_returns_document(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert isinstance(doc, Document)

    def test_root_populated(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert doc.root is not None

    def test_pages_is_none_in_tree_mode(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert doc.pages is None

    def test_root_has_children(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert len(doc.root.children) >= 1

    def test_full_text_non_empty(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert len(doc.full_text) > 0

    def test_content_types_valid_in_tree(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        valid = {ContentType.text, ContentType.image, ContentType.table}

        def walk(node):
            assert node.content_type in valid
            for child in node.children:
                walk(child)

        walk(doc.root)

    def test_heading_nodes_have_role_metadata(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()

        def collect_roles(node):
            roles = []
            if node.metadata.get("role"):
                roles.append(node.metadata["role"])
            for child in node.children:
                roles.extend(collect_roles(child))
            return roles

        roles = collect_roles(doc.root)
        # At least some nodes should have explicit roles
        assert len(roles) >= 1

    def test_to_markdown_produces_non_empty_string(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        md = doc.to_markdown()
        assert len(md) > 0

    def test_source_type_is_pdf_in_tree_mode(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        assert doc.source.source_type == SourceType.pdf

    def test_image_node_in_tree(self, sample_pdf_path: Path):
        doc = PdfParser(str(sample_pdf_path), mode="tree").parse()
        images = doc.root.get_nodes_by_type(ContentType.image)
        assert len(images) >= 1
        assert images[0].content
