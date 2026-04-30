# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import importlib
from pathlib import Path

# Third Party Library
import pytest

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

_FIXTURE_SPECS = [
    ("sample.pdf",  "tests.fixtures.pdf",  "create_sample_pdf"),
    ("sample.docx", "tests.fixtures.docx", "create_sample_docx"),
    ("sample.md",   "tests.fixtures.md",   "create_sample_md"),
    ("sample.txt",  "tests.fixtures.txt",  "create_sample_txt"),
    ("sample.html", "tests.fixtures.html", "create_sample_html"),
    ("sample.py",   "tests.fixtures.py",   "create_sample_py"),
]


def pytest_configure(config) -> None:
    """Generate parser fixture files once before the test session starts.

    Skips silently if the required optional dependency is missing, so that
    schema and chunker test suites can run without the parser extras.
    """
    for filename, module, func in _FIXTURE_SPECS:
        dest = _FIXTURES_DIR / filename
        if dest.exists():
            continue
        try:
            getattr(importlib.import_module(module), func)(dest)
        except Exception:
            pass


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    """Absolute path to the generated sample PDF fixture."""
    return _FIXTURES_DIR / "sample.pdf"


@pytest.fixture(scope="session")
def sample_docx_path() -> Path:
    """Absolute path to the generated sample DOCX fixture."""
    return _FIXTURES_DIR / "sample.docx"


@pytest.fixture(scope="session")
def sample_md_path() -> Path:
    """Absolute path to the generated sample Markdown fixture."""
    return _FIXTURES_DIR / "sample.md"


@pytest.fixture(scope="session")
def sample_txt_path() -> Path:
    """Absolute path to the generated sample plain-text fixture."""
    return _FIXTURES_DIR / "sample.txt"


@pytest.fixture(scope="session")
def sample_html_path() -> Path:
    """Absolute path to the generated sample HTML fixture."""
    return _FIXTURES_DIR / "sample.html"


@pytest.fixture(scope="session")
def sample_py_path() -> Path:
    """Absolute path to the generated sample Python fixture."""
    return _FIXTURES_DIR / "sample.py"
