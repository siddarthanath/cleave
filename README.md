# Cleave ✂️

<p align="center">
  <img src="docs/cleave.png" width="400" />
</p>

> A minimal unified Python pipeline for document parsing, chunking, embedding and retrieval.

One document in. Embedding-ready chunks out. Swap parsers, chunkers, embedders and stores without touching your application code.

## Why 

- Building a RAG pipeline always ends up with the same problem - parsing libraries don't chunk, chunking libraries don't embed, and everything expects a different input format. You end up gluing together five packages and hoping they agree on what a _document_ is.
- Cleave owns the full journey: raw file in, embedding-ready chunks out. One typed schema flows through every stage - `Document → Chunk → EmbeddedChunk` - so every layer speaks the same language.
- It's also LLM-agnostic for embeddings. Use Relay, the raw OpenAI SDK, or any provider you already have. Cleave just needs something that turns text into vectors.

Implementations are done from scratch by utilising existing libraries and extracting core functionalities, so you can see exactly what provider libraries are doing under the hood - it is not magic!

---

## Install

### Approach 1: GitHub
```bash
git clone https://github.com/siddarthanath/cleave
cd cleave
pip install -e .
```

### Approach 2: PyPI
```bash
pip install cleave
```

Install only what you need:
```bash
pip install cleave[pdf,chroma,openai]
pip install cleave[all]
```

---

## Usage

### 1. Parse (Loading Phase)

```python
# Imports
from cleave.parsers.factory import ParserFactory
# Arrange (Parser creation)
parser = ParserFactory.create("paper.pdf")  
# Act (Parser generation)
document = parser.parse()

print(document.full_text)        # all text across all pages / nodes
print(document.total_pages)      # page count (flat mode only)
print(document.all_images)       # extracted image blocks
print(document.all_tables)       # extracted table blocks
```

Supported formats: `.pdf` (text, images, tables), `.docx` (text, images, tables), `.md` (text, images, tables), `.html` / URLs (text), `.txt` (text), `.py` (text).

#### Parsing modes

Every parser supports two output modes that trade off simplicity against structure.

| Mode | Description | `Document` field | Best for |
|------|-------------|-----------------|----------|
| `flat` _(default)_ | Content extracted as an ordered list of pages, each containing text / image / table blocks - no structure preserved | `.pages` — one `DocumentPage` per logical page | Simple text retrieval, fixed or sentence chunking |
| `tree` | Content organised into a heading-scoped hierarchy - headings become parent nodes, body paragraphs / tables / images become their children | `.root` - recursive `TreeNode` hierarchy | Semantic / layout-aware chunking, heading-scoped retrieval |

```python
# Flat mode — ordered pages of content blocks (default)
document = ParserFactory.create("paper.pdf", mode="flat").parse()

# Tree mode — heading-scoped TreeNode hierarchy
document = ParserFactory.create("paper.pdf", mode="tree").parse()
document.to_markdown()   # bridge: convert tree back to a plain string
```

The `to_markdown()` bridge serialises a tree document back into a plain Markdown string, so it can be passed to any string-based chunker (e.g. `FixedChunker`, `SentenceChunker`, `RecursiveChunker`) without losing heading structure in the text. Image bytes are never lost — they remain in `TreeNode.content` — but are not emitted into the bridge string.

- **bridge** → text pipeline (chunking, retrieval)
- **tree** → multimodal pipeline (vision embeddings, image extraction)

> **Note - Code Parsing:** `.py` files (and future languages) are parsed using [TreeSitter](https://tree-sitter.github.io/tree-sitter/), a concrete syntax tree parser. Both `flat` and `tree` modes work identically to all other parsers via `ParserFactory`. The difference is what _tree_ means: 
- For documents (PDF, DOCX, Markdown) the hierarchy is built from heading heuristics.
- For code it mirrors the real syntax — `module → class → method`. 
The output is the same `TreeNode` schema either way.

### 2. Chunk (Transformation Phase)

```python
# Imports
from cleave.chunker.factory import ChunkerFactory
# Arrange (Chunk creation)
chunker = ChunkerFactory.create("sentence", chunk_size=512, chunk_overlap=50)
# Act (Chunk generation)
chunks = chunker.chunk(document)

for chunk in chunks:
    print(chunk.index, chunk.token_count, chunk.text[:80])
```

Available strategies: `fixed`, `sentence`, `recursive`.

### 3. Embed (Indexing Phase)

```python
# Imports
from cleave.embedder import EmbedderFactory
# Arrange (Embedder creation)
embedder = EmbedderFactory.create("openai", api_key="sk-...")
# Act (Embedding generation)
embedded = embedder.embed(chunks)
```

Supported providers: `openai`, `anthropic`, `google`.

### 4. Store (Persistance Phase)

```python
# Imports
from cleave.store import StoreFactory
# Arrange (Storage creation)
store = StoreFactory.create("chroma", path="./db")
# Act (Storage execution)
store.connect()
store.insert(embedded)
```

Supported backends: `chroma`, `sqlite`, `pinecone`.

### 5. Retrieve (Query Phase)

```python
# Imports
from cleave.retriever import RetrieverFactory
# Arrange (Retriever creation)
query_vector = embedder.embed_texts(["what is the main argument?"])[0]
retriever = RetrieverFactory.create("cosine")
# Act (Retrieval execution)
results = retriever.retrieve(query_vector, embedded, top_k=5)

for result in results:
    print(result.chunk.text)
```

Available algorithms: `cosine`, `bm25`, `mmr`.

### 6. End to end

Ultimately, `Cleave` is the Retrieval Augmented Generation (RAG) complete interface for context engineering 
with LLMs.

```python
# Imports
from cleave.parsers.factory import ParserFactory
from cleave.chunker.factory import ChunkerFactory
from cleave.embedder import EmbedderFactory
from cleave.store import StoreFactory
from cleave.retriever import RetrieverFactory
# Step 1: Parse document
parser = ParserFactory.create("paper.pdf")
document = parser.parse()
# Step 2: Chunk parsed document
chunker = ChunkerFactory.create("sentence", chunk_size=512)
chunks = chunker.chunk(document)
# Step 3: Embed chunks
embedder = EmbedderFactory.create("openai", api_key="sk-...")
embedded = embedder.embed(chunks)
# Step 4: Store embedded chunks
store = StoreFactory.create("chroma", path="./db")
store.connect()
store.insert(embedded)
# Step 5: Retrieval Augmented Generation (RAG)
query = embedder.embed_texts(["what is the main argument?"])[0]
results = RetrieverFactory.create("cosine").retrieve(query, embedded, top_k=5)
```

### 7. Switching providers

```python
# Same chunks, different embedder — no other changes needed
embedder = EmbedderFactory.create("google", api_key="AIza...")
embedded = embedder.embed(chunks)
```

---

<!-- ## Supported formats

| Format | Parser | Text | Images | Tables |
|:---:|:---:|:---:|:---:|:---:|
| PDF | `PdfParser` | ✓ | ✓ | ✓ |
| DOCX | `DocxParser` | ✓ | | ✓ |
| PPTX | `PptxParser` | ✓ | ✓ | |
| HTML | `HtmlParser` | ✓ | | |
| Markdown | `MarkdownParser` | ✓ | | |
| TXT | `TxtParser` | ✓ | | |
| URL | `HtmlParser` | ✓ | | |

---

## Roadmap

| Version | Feature | Status 
|:---:|:---| :---|
| v1 | Parse, chunk, embed, store, retrieve (text only) | ✓
| v2 | Image & Table handling with hybrid retrieval (semantic + BM25 combined) | ✗
| v3 | Vision embeddings for image blocks | ✗
| v4 | Table-aware chunking | ✗
| v5 | CLI + Streamlit interface | ✗
 
--- -->

## Citation

If you use Cleave in your work, please cite:

```text
@software{cleave2026,
  author = {Siddartha Nath},
  title = {Cleave: A Minimal Unified Python Interface for Document Parsing, Chunking, Embedding and Retrieval},
  year = {2026},
  url = {https://github.com/siddarthanath/cleave}
}
```