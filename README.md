# Cleave ✂️

> A minimal unified Python pipeline for document parsing, chunking, embedding and retrieval.

One document in. Embedding-ready chunks out. Swap parsers, chunkers, embedders and stores without touching your application code.

Implementations are done from scratch by utilising existing libraries and extracting core functionalities, so you can see exactly what provider libraries are doing under the hood.

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

### 1. Parse

```python
# Imports
from cleave.parser import ParserFactory
# Arrange (Paper Load)
parser = ParserFactory.create("paper.pdf")
# Act (Parse execution)
document = parser.parse()

print(document.full_text)        # all text across all pages
print(document.total_pages)      # page count
print(document.all_images)       # extracted image blocks
print(document.all_tables)       # extracted table blocks
```

Supported formats: `.pdf`, `.docx`, `.pptx`, `.html`, `.md`, `.txt`, and URLs.

### 2. Chunk

```python
# Imports
from cleave.chunker import ChunkerFactory
# Arrange (Chunk creation)
chunker = ChunkerFactory.create("sentence", chunk_size=512, chunk_overlap=50)
# # Act (Chunk generation)
chunks = chunker.chunk(document)

for chunk in chunks:
    print(chunk.index, chunk.token_count, chunk.text[:80])
```

Available strategies: `fixed`, `sentence`, `recursive`, `semantic`.

### 3. Embed

```python
# Imports
from cleave.embedder import EmbedderFactory
# Arrange (Embedder creation)
embedder = EmbedderFactory.create("openai", api_key="sk-...")
# Act (Embedding generation)
embedded = embedder.embed(chunks)
```

Supported providers: `openai`, `anthropic`, `google`.

### 4. Store

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

### 5. Retrieve

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
from cleave.parser import ParserFactory
from cleave.chunker import ChunkerFactory
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
| v1 | Parse, chunk, embed, store, retrieve | ✓
| v2 | Hybrid retrieval (semantic + BM25 combined) | ✗
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