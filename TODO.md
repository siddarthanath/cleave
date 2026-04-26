# Cleave — TODO

Issues are split into **faults** (bugs / broken behaviour) and **improvements** (competitive gaps vs LangChain/LlamaIndex).

---

## Chunkers

| File | Issues | Next Steps |
|------|--------|------------|
| `chunker/base.py` | `tiktoken cl100k_base` hardcoded — can't use other models' tokenizers (GPT-4o, Claude, etc.) | Move encoder config into `ChunkParams`; accept a tokenizer callable or enum |

---

## Parsers

| File | Issues | Next Steps |
|------|--------|------------|

---

## Schemas

| File | Issues | Next Steps |
|------|--------|------------|

---

## Code Parsing (TreeSitter)

| Area | Issues | Next Steps |
|------|--------|------------|
| `parsers/code/` | No AST-aware code parser — current naive delimiter splitting misses semantic boundaries (class/function scope) | Implement `CodeParser` using TreeSitter; emit `TreeNode` hierarchy mirroring the AST |
| `parsers/factory.py` | No code file extensions registered (`.py`, `.ts`, `.js`, `.java`, etc.) | Add to factory registry once `CodeParser` exists |
| `chunker/recursive.py` | `DELIMITER_PRESETS` is a stopgap — string splitting cannot respect scope boundaries | Replace with TreeSitter-based chunking for code once `CodeParser` lands |

---

## Infrastructure / DX

| Area | Issues | Next Steps |
|------|--------|------------|
| Commit convention | No enforced format | Adopt Conventional Commits (`feat(parsers): ...`, `fix(chunker): ...`) |
| PR template | No `.github/PULL_REQUEST_TEMPLATE.md` | Add minimal template (summary, test plan, breaking changes) |
| Linting | No `ruff` / `black` config in `pyproject.toml` | Add `[tool.ruff]` with line-length and import-sort rules |
| Type checking | No `mypy` config | Add `[tool.mypy]` with `strict = true` |
| CI/CD | No `.github/workflows/` | Add workflow running `pytest tests/` on push |
| Changelog | No version history | Add `CHANGELOG.md` once published to PyPI |
