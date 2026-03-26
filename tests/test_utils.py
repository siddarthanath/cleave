# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library

# Third Party Library
import pytest
from pathlib import Path

# Private Library
from cleave.utils.file import get_path_and_extension

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class TestGetPathAndExtension:
    def test_returns_path_object(self):
        path_, _ = get_path_and_extension("some/file.pdf")
        assert isinstance(path_, Path)

    def test_extracts_extension(self):
        _, ext = get_path_and_extension("some/file.pdf")
        assert ext == ".pdf"

    def test_lowercases_extension(self):
        _, ext = get_path_and_extension("some/file.PDF")
        assert ext == ".pdf"

    def test_mixed_case_extension(self):
        _, ext = get_path_and_extension("doc.Docx")
        assert ext == ".docx"

    def test_no_extension_returns_empty_string(self):
        _, ext = get_path_and_extension("somefile")
        assert ext == ""

    def test_multiple_dots_returns_last_suffix(self):
        _, ext = get_path_and_extension("archive.tar.gz")
        assert ext == ".gz"

    def test_path_object_preserves_stem(self):
        path_, _ = get_path_and_extension("dir/report.pdf")
        assert path_.stem == "report"

    def test_path_object_preserves_full_name(self):
        path_, _ = get_path_and_extension("dir/report.pdf")
        assert path_.name == "report.pdf"
