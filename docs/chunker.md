# Cleave Chunkers

## Class Diagram

```
BaseChunker (ABC)
├── FixedChunker       (ChunkerType.fixed)
├── SentenceChunker    (ChunkerType.sentence)
└── RecursiveChunker   (ChunkerType.recursive)
```

`BaseChunker` owns tiktoken token counting, `make_chunk`, `_chunk_page`, and `_measure`. Subclasses implement `chunk()` and `_chunk_text()`.

---

## Chunking Strategies

| Strategy | Class | Flat | Tree | Best for |
|----------|-------|------|------|----------|
| `fixed` | `FixedChunker` | ✓ | via bridge | Uniform retrieval, token-budget control |
| `sentence` | `SentenceChunker` | ✓ | via bridge | Prose documents where sentence boundaries matter |
| `recursive` | `RecursiveChunker` | ✓ | ✓ native | Structured documents with headings and mixed content |

---

## Chunk Params

```python
from cleave.schemas import ChunkParams, ChunkUnit

# Character mode (default)
params = ChunkParams(chunk_size=500, chunk_overlap=50)

# Token mode
params = ChunkParams(chunk_size=128, chunk_overlap=16, unit=ChunkUnit.tokens)
```

| Field | Type | Description |
|-------|------|-------------|
| `chunk_size` | `int` | Maximum chunk length in the configured unit |
| `chunk_overlap` | `int` | Overlap shared between adjacent chunks (`>= 0`, must be `< chunk_size`) |
| `unit` | `ChunkUnit` | `characters` (default) or `tokens` (tiktoken `cl100k_base`) |

---

## Basic Usage

```python
from cleave.parsers.factory import ParserFactory
from cleave.chunker.factory import ChunkerFactory

doc    = ParserFactory.create("paper.pdf").parse()
chunks = ChunkerFactory.create("fixed", chunk_size=500, chunk_overlap=50).chunk(doc)

for c in chunks:
    print(f"[{c.index}] type={c.content_type.value}  tokens={c.token_count}  {c.text[:60]!r}")
```

---

## Content Type Handling

All chunkers handle mixed-content pages. Text blocks are split by the chunker's strategy; table and image blocks are always emitted as single atomic chunks in their natural position order.

| Content type | FixedChunker | SentenceChunker | RecursiveChunker |
|---|---|---|---|
| `text` | Split by fixed window | Split at sentence boundaries | Split by delimiter hierarchy |
| `table` | Single chunk | Single chunk | Single chunk (atomicity rule) |
| `image` | Single chunk | Single chunk | Single chunk (atomicity rule) |

`token_count` is `0` for image chunks — base64 data has no meaningful token count.

---

## FixedChunker

Slides a fixed-size window over each page's text with a fixed step (`chunk_size - chunk_overlap`).

```
text:  [──────────window──────────]
                [──────overlap──][──────window──────────]
```

### Character mode

```python
chunker = ChunkerFactory.create("fixed", chunk_size=200, chunk_overlap=20)
```

### Token mode

Encodes to tiktoken tokens, slides the window over the token list, decodes each window back to a string. More precise for LLM context limits.

```python
chunker = ChunkerFactory.create("fixed", chunk_size=128, chunk_overlap=16, unit="tokens")
```

---

## SentenceChunker

Accumulates text until `chunk_size` is reached at a sentence boundary (`.`, `!`, `?`). Cross-page sentences are carried over via `spare_text`.

```
text:  First sentence. Second sentence. Third sentence!
       [──── accumulate ────][commit at boundary][──next──]
```

- Sentence trimming is applied at **page boundaries only** — within-page text flushes (triggered by table/image blocks) do not trim.
- Overlap is applied in the configured unit (character slice or token decode).

---

## RecursiveChunker

Dual-path chunker that adapts to document structure.

### Tree path (`document.root`)

Walks the `TreeNode` hierarchy. Nodes whose full text fits within `chunk_size` are emitted as one chunk. Oversized nodes are recursed into; oversized leaf nodes fall back to string splitting.

```
root
 └─ heading[H1]  → fits → single chunk
     └─ heading[H2] → too large → recurse
         └─ paragraph → fits → single chunk
         └─ table     → atomic → single chunk
```

### Flat path (`document.pages`)

Applies a delimiter hierarchy over each page's text, grouping pieces greedily:

```
Delimiters (priority order):
  "\n# "  →  "\n## "  →  "\n### "  →  "\n\n"  →  "\n"  →  " "
```

Falls back to a fixed-size sliding window only when a single piece cannot be reduced further.

### Bridge — flat chunkers on tree documents

Pass a tree document through `to_markdown()` to use `FixedChunker` or `SentenceChunker` while preserving heading structure:

```python
doc       = ParserFactory.create("report.pdf", mode="tree").parse()
md_string = doc.to_markdown()

# Wrap in a synthetic flat Document
from cleave.schemas import ContentBlock, ContentType, Document, DocumentPage, Source, SourceType
flat_doc = Document(
    source=doc.source,
    pages=[DocumentPage(page_number=None, blocks=[
        ContentBlock(type=ContentType.text, content=md_string, position=0)
    ])],
    total_pages=1,
)
chunks = ChunkerFactory.create("sentence", chunk_size=300, chunk_overlap=30).chunk(flat_doc)
```

---

## Chunk Schema

```python
from cleave.schemas import Chunk

chunk.chunk_id      # str  — 16-char SHA-256 hex of "{source.location}:{index}" (deterministic)
chunk.text          # str  — chunk text content
chunk.source        # Source
chunk.page_number   # int | None
chunk.content_type  # ContentType (text / table / image)
chunk.index         # int  — 0-based global position
chunk.token_count   # int  — tiktoken cl100k_base (0 for images)
chunk.char_start    # int  — start offset within page text
chunk.char_end      # int  — end offset within page text
```

`chunk_id` is computed automatically by a `model_validator` — callers never need to set it.

---

## Factory

```python
from cleave.chunker.factory import ChunkerFactory

chunker = ChunkerFactory.create("fixed",     chunk_size=200, chunk_overlap=20)
chunker = ChunkerFactory.create("sentence",  chunk_size=300, chunk_overlap=30)
chunker = ChunkerFactory.create("recursive", chunk_size=512, chunk_overlap=64)
```

`ChunkerFactory._CHUNKER_REGISTRY` maps strategy name → chunker class. Add new chunkers there.
