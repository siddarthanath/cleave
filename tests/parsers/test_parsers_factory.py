# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library
import pytest

# Private Library
from cleave.parsers.factory import ParserFactory

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TestUrlInputs:
    def test_https_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            ParserFactory.create("https://example.com")

    def test_http_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            ParserFactory.create("http://example.com/page")

class TestUnsupportedExtensions:
    def test_unknown_extension_raises_value_error(self, tmp_path):
        fake = tmp_path / "file.xyz"
        fake.touch()
        with pytest.raises(ValueError, match="Unsupported extension"):
            ParserFactory.create(str(fake))

    def test_extension_not_in_registry_raises_value_error(self, tmp_path):
        # .txt is in BaseParser._EXTENSION_MAP but NOT in ParserFactory._PARSER_REGISTRY
        fake = tmp_path / "notes.txt"
        fake.touch()
        with pytest.raises(ValueError, match="Unsupported extension"):
            ParserFactory.create(str(fake))

class TestRegistry:
    def test_supported_extensions_present(self):
        assert ".pdf" in ParserFactory._PARSER_REGISTRY
        assert ".docx" in ParserFactory._PARSER_REGISTRY

    def test_pdf_extension_reaches_registry_lookup(self, tmp_path):
        fake = tmp_path / "doc.pdf"
        fake.touch()
        # Extension is recognised so no ValueError; registry value is Ellipsis
        # (not callable) until real parsers are wired up.
        with pytest.raises(TypeError):
            ParserFactory.create(str(fake))
