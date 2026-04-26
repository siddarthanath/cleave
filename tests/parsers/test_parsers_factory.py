# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library
import pytest

# Private Library
from cleave.parsers.factory import ParserFactory
from cleave.parsers.markup.html import HtmlParser

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TestUrlInputs:
    def test_https_returns_html_parser(self, monkeypatch):
        import httpx
        mock_response = type("R", (), {
            "text": "<html><body><p>Hello</p></body></html>",
            "raise_for_status": lambda self: None,
        })()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_response)
        parser = ParserFactory.create("https://example.com")
        assert isinstance(parser, HtmlParser)

    def test_http_returns_html_parser(self, monkeypatch):
        import httpx
        mock_response = type("R", (), {
            "text": "<html><body><p>Hello</p></body></html>",
            "raise_for_status": lambda self: None,
        })()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_response)
        parser = ParserFactory.create("http://example.com/page")
        assert isinstance(parser, HtmlParser)

class TestUnsupportedExtensions:
    def test_unknown_extension_raises_value_error(self, tmp_path):
        fake = tmp_path / "file.xyz"
        fake.touch()
        with pytest.raises(ValueError, match="Unsupported extension"):
            ParserFactory.create(str(fake))

    def test_txt_extension_is_supported(self, tmp_path):
        from cleave.parsers.plain.txt import TextParser
        fake = tmp_path / "notes.txt"
        fake.touch()
        assert isinstance(ParserFactory.create(str(fake)), TextParser)

class TestRegistry:
    def test_supported_extensions_present(self):
        assert ".pdf" in ParserFactory._PARSER_REGISTRY
        assert ".docx" in ParserFactory._PARSER_REGISTRY

    def test_pdf_extension_creates_parser(self, tmp_path):
        from cleave.parsers.office.pdf import PdfParser
        fake = tmp_path / "doc.pdf"
        fake.touch()
        assert isinstance(ParserFactory.create(str(fake)), PdfParser)
