# Cleave — Development Guidelines

This document provides context for understanding the Cleave codebase and assisting with development.

## Project architecture

### Repository structure

```
cleave/
├── cleave/                    # Main package
│   ├── parsers/               # Document parsers (PDF, DOCX, MD, TXT)
│   │   ├── base.py            # BaseParser and BaseModeParser abstractions
│   │   ├── factory.py         # ParserFactory — selects parser by file extension
│   │   ├── office/            # PdfParser, DocxParser
│   │   └── markup/            # MarkdownParser
│   │   └── plain/             # TextParser
│   ├── chunker/               # Chunking strategies (fixed, sentence, recursive)
│   │   ├── base.py            # BaseChunker — tiktoken token counting
│   │   └── factory.py         # ChunkerFactory
│   ├── embedder/              # Embedding providers (openai, anthropic, google)
│   ├── store/                 # Vector stores (chroma, sqlite, pinecone)
│   ├── retriever/             # Retrieval algorithms (cosine, bm25, mmr)
│   ├── schemas.py             # All shared Pydantic models
│   └── utils/                 # Shared utilities (file loading)
├── tests/
│   ├── fixtures/              # Fixture generators (pdf.py, docx.py, md.py, txt.py, _image.py)
│   ├── parsers/               # Parser tests + conftest (owns fixture generation)
│   └── chunkers/              # Chunker tests + conftest
├── notebooks/
│   ├── parsers/               # Per-parser demo notebooks (office/, markup/, plain/)
│   └── chunkers/              # Per-chunker demo notebooks
├── docs/
│   ├── parser.md              # Parser class diagram, mode table, per-parser flat/tree flow, heading detection comparison
│   └── chunker.md             # Chunker class diagram, strategy comparison, content type handling, Chunk schema
├── pyproject.toml
└── AGENTS.md
```

### Core data flow

```
raw file → Parser → Document → Chunker → [Chunk] → Embedder → [EmbeddedChunk] → Store / Retriever
```

Every stage is typed. The shared schema is `cleave/schemas.py`:

- `Document` — holds either `.pages` (flat mode) or `.root` (tree mode), never both
- `DocumentPage` — list of `ContentBlock` items with `type` (text/image/table), `content`, `position`
- `TreeNode` — recursive node with `content_type`, `content`, `children`, `metadata`
- `Chunk` — text slice with `index`, `token_count`, `text`, `source`
- `EmbeddedChunk` — `Chunk` plus `vector: List[float]`

### Parsing modes

Every parser (except `TextParser`) supports two modes selected at construction time:

| Mode | Output | Use when |
|------|--------|----------|
| `flat` | `.pages` populated; `.root = None` | Simple text retrieval, fixed/sentence chunking |
| `tree` | `.root` populated; `.pages = None` | Semantic chunking, heading-scoped retrieval, multimodal pipelines |

The `Document.to_markdown()` bridge serialises a tree document back to a plain Markdown string so it can be passed to any string-based chunker without losing heading structure.

### Factory pattern

All public entry points are factories — never import parser/chunker classes directly:

```python
from cleave.parsers.factory import ParserFactory
from cleave.chunker.factory import ChunkerFactory

parser = ParserFactory.create("paper.pdf", mode="flat")
chunker = ChunkerFactory.create("sentence", chunk_size=512)
```

---

## Development tools

- `pip install -e .` — editable install
- `pip install cleave[pdf,docx,openai,dev]` — install with extras
- `pytest tests/` — run all tests
- `pytest tests/parsers/` — run parser tests only

### Optional extras

| Extra | Installs |
|-------|----------|
| `pdf` | `pymupdf`, `pymupdf-layout` |
| `docx` | `python-docx` |
| `chroma` | `chromadb` |
| `openai` | `openai` |
| `anthropic` | `anthropic` |
| `google` | `google-genai` |
| `dev` | `pytest`, `pytest-cov`, `pytest-asyncio` |
| `all` | everything above |

---

## Code style

### File structure

Every Python source file follows this top-level layout:

```python
# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
...

# Third Party Library
...

# Private Library
...

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #
```

### Class section headers

Classes with distinct logical paths (e.g. flat vs tree) use box-style section headers between those sections:

```python
# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    FLAT PATH                                       ║
# ║                        (Sequential Page-Block Extraction)                          ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝
```

This is only used for major public logic sections. Private/helper methods (prefixed `_`) are self-explanatory and do not need section headers.

### Method ordering within a class

Methods should appear in this order:

1. `__init__`
2. Public abstract methods (e.g. `chunk`)
3. Public concrete methods (e.g. `make_chunk`)
4. Protected abstract methods (e.g. `_chunk_text`) — abstract before concrete within this group
5. Protected concrete helpers (e.g. `_chunk_page`, `_measure`, `_count_tokens`)

Within each group, abstract before concrete.

### Docstrings

Use Google-style docstrings. All public and protected methods must document every parameter and return value. Types belong in the function signature, not the docstring.

```python
def method(self, text: str, max_tokens: int = 512) -> List[Chunk]:
    """One-line summary.

    Optional extra context here.

    Args:
        text: The input text to chunk.
        max_tokens: Maximum tokens per chunk.

    Returns:
        List of Chunk objects in document order.
    """
```

- No full stops at the end of inline comments
- No multi-line comment blocks
- No comments that restate what the code does — only explain *why* when non-obvious

### Type hints

All functions must have full type hints including return types. Use `from __future__ import annotations` only if needed for forward references.

### Abstractions

- `BaseParser` — base for all parsers; owns `_make_source` and `_make_url_source`
- `BaseModeParser(BaseParser)` — adds mode validation and `parse()` dispatch; subclasses implement `_parse_flat` and `_parse_tree`
- `TextParser` extends `BaseParser` directly (tree mode unsupported — raises `NotImplementedError`)
- `BaseChunker` — owns tiktoken token counting via `cl100k_base`

---

## Testing

### Structure

Test structure mirrors source structure:

```
tests/parsers/   ↔   cleave/parsers/
tests/chunkers/  ↔   cleave/chunker/
```

Each subfolder owns its `conftest.py`. Fixtures (sample files) live in `tests/fixtures/` and are generated by `pytest_configure` hooks in `tests/parsers/conftest.py` — they are created once per session and reused.

### Fixture generators

| File | Function | Generates |
|------|----------|-----------|
| `tests/fixtures/pdf.py` | `create_sample_pdf` | `sample.pdf` — H1/H2 structure, real grid table, embedded image |
| `tests/fixtures/docx.py` | `create_sample_docx` | `sample.docx` — Word heading styles, table, embedded image |
| `tests/fixtures/md.py` | `create_sample_md` | `sample.md` — ATX headings, GFM table, local image reference |
| `tests/fixtures/txt.py` | `create_sample_txt` | `sample.txt` — plain prose, no markup |
| `tests/fixtures/_image.py` | `minimal_png` | stdlib-only 20×20 red PNG (no Pillow dependency) |

### Writing tests

- Happy path and edge cases both required
- No mocking of file I/O — tests read real generated fixture files
- Use `pytest.raises` for expected exceptions
- Test classes group by parser mode: `TestPdfParserFlat`, `TestPdfParserTree`

---

## Notebooks

Each parser and chunker has a demo notebook under `notebooks/`. Notebooks follow this cell order:

1. Title + mode table + pros/cons table (markdown)
2. `## Imports` (code)
3. `## Fixture` (markdown + code — loads from `tests/fixtures/`)
4. `## Flat mode` (markdown + code cells)
5. `## Tree mode` (markdown + code cells, parsers only)
6. `## Summary comparison` (code)

Notebooks use `ParserFactory` / `ChunkerFactory` — never import parser or chunker classes directly.

Section headings (e.g. `## Flat mode`) must be in their own markdown cell, not combined with explanatory prose. If a section needs a description, put it in a separate markdown cell immediately after the heading cell.

---

## POTENTIAL CHANGES

The following are missing from this codebase and worth adding:

- **Commit message convention** — no enforced format exists. Consider Conventional Commits (`feat(parsers): ...`, `fix(chunker): ...`) with a scope matching the package subfolder.
- **PR description template** — no `.github/PULL_REQUEST_TEMPLATE.md`. A minimal template (summary, test plan, breaking changes) would help reviewers.
- **Linting / formatting** — no `ruff` or `black` configuration in `pyproject.toml`. Adding `[tool.ruff]` with line-length and import-sort rules would enforce the import section style automatically.
- **Type checking** — no `mypy` configuration. Adding `[tool.mypy]` with `strict = true` would catch missing return types and untyped parameters.
- **CI/CD** — no `.github/workflows/` directory. A minimal workflow running `pytest tests/` on push would prevent regressions.
- **`CHANGELOG.md`** — no version history tracked. Useful once the package is published to PyPI.
