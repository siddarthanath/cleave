# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library
import pytest

# Private Library
from cleave.parsers.base import BaseParser, _EXTENSION_MAP
from cleave.schemas import SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TestExtensionMap:
    def test_has_all_supported_extensions(self):
        expected = {".pdf", ".docx", ".pptx", ".html", ".htm", ".md", ".txt"}
        assert expected == set(_EXTENSION_MAP.keys())

    def test_correct_source_types(self):
        assert _EXTENSION_MAP[".pdf"] == SourceType.pdf
        assert _EXTENSION_MAP[".docx"] == SourceType.docx
        assert _EXTENSION_MAP[".pptx"] == SourceType.pptx
        assert _EXTENSION_MAP[".html"] == SourceType.html
        assert _EXTENSION_MAP[".htm"] == SourceType.html
        assert _EXTENSION_MAP[".md"] == SourceType.markdown
        assert _EXTENSION_MAP[".txt"] == SourceType.txt

    def test_htm_and_html_map_to_same_type(self):
        assert _EXTENSION_MAP[".htm"] == _EXTENSION_MAP[".html"]

class TestMakeUrlSource:
    def test_type_is_url(self):
        source = BaseParser._make_url_source("https://example.com/page")
        assert source.type == SourceType.url

    def test_name_is_netloc(self):
        source = BaseParser._make_url_source("https://example.com/page")
        assert source.name == "example.com"

    def test_location_is_full_url(self):
        url = "https://example.com/some/path?q=1#anchor"
        source = BaseParser._make_url_source(url)
        assert source.location == url

    def test_http_scheme(self):
        source = BaseParser._make_url_source("http://docs.python.org")
        assert source.type == SourceType.url
        assert source.name == "docs.python.org"

    def test_subdomain_preserved_in_name(self):
        source = BaseParser._make_url_source("https://api.github.com/repos")
        assert source.name == "api.github.com"

class TestMakeSource:
    def test_unsupported_extension_raises_value_error(self, tmp_path):
        fake = tmp_path / "file.xyz"
        fake.touch()
        with pytest.raises(ValueError, match="Unsupported file extension"):
            BaseParser._make_source(str(fake))

    def test_pdf_type(self, tmp_path):
        fake = tmp_path / "report.pdf"
        fake.touch()
        source = BaseParser._make_source(str(fake))
        assert source.type == SourceType.pdf

    def test_name_is_filename(self, tmp_path):
        fake = tmp_path / "report.pdf"
        fake.touch()
        source = BaseParser._make_source(str(fake))
        assert source.name == "report.pdf"

    def test_location_is_absolute(self, tmp_path):
        fake = tmp_path / "doc.txt"
        fake.touch()
        source = BaseParser._make_source(str(fake))
        assert source.location == str(fake.resolve())

    def test_docx(self, tmp_path):
        fake = tmp_path / "presentation.docx"
        fake.touch()
        source = BaseParser._make_source(str(fake))
        assert source.type == SourceType.docx

    def test_markdown(self, tmp_path):
        fake = tmp_path / "notes.md"
        fake.touch()
        source = BaseParser._make_source(str(fake))
        assert source.type == SourceType.markdown
