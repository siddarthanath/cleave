# Chunker

## Setup

Install the core package (tiktoken is included as a base dependency):

```bash
pip install cleave
```

To use a specific chunker:

```python
# Imports
from cleave.chunker.factory import ChunkerFactory
from cleave.schemas import ChunkerType, ChunkParams, ChunkUnit
# Arrange
params = ChunkParams(chunk_size=200, chunk_overlap=20)
chunker = ChunkerFactory.create(ChunkerType.fixed, params)
# Act
chunks = chunker.chunk(document)
```

`chunk_size` and `chunk_overlap` are in **characters** by default. Pass `unit=ChunkUnit.tokens` to measure in tokens (uses tiktoken `cl100k_base`).

---

## Architecture

```mermaid
classDiagram
    class ChunkerFactory {
        +_CHUNKER_REGISTRY : Dict
        +create(chunk_type, chunk_params) BaseChunker$
    }

    class BaseChunker {
        <<abstract>>
        +chunk_params : ChunkParams
        +token_enc : Encoding
        +chunk(document) List~Chunk~*
        +make_chunk(text, source, page_number, index, char_start, content_type) Chunk
        #_measure(text) int
        #_count_tokens(text) int
        #_make_text_chunk(...)  Chunk
        #_make_table_chunk(...) Chunk
        #_make_image_chunk(...) Chunk
    }

    class FixedChunker {
        +chunk(document) List~Chunk~
        -_chunk_text(text, page_number, source, start_index) List~Chunk~
    }

    class ChunkParams {
        +chunk_size : int
        +chunk_overlap : int
        +unit : ChunkUnit
    }

    class Chunk {
        +text : str
        +source : Source
        +page_number : int
        +content_type : ContentType
        +index : int
        +token_count : int
        +char_start : int
        +char_end : int
    }

    class ChunkUnit {
        <<enumeration>>
        characters
        tokens
    }

    class ChunkerType {
        <<enumeration>>
        fixed
        recursive
    }

    ChunkerFactory ..> BaseChunker : creates
    ChunkerFactory ..> ChunkerType : keyed by
    BaseChunker <|-- FixedChunker
    BaseChunker --> ChunkParams : uses
    BaseChunker ..> Chunk : produces
    ChunkParams --> ChunkUnit : unit
```

---

## How Each Chunker Works

### FixedChunker

Splits text into **fixed-size, overlapping windows**. The window slides forward by `step = chunk_size - chunk_overlap` each iteration. The two modes share the same algorithm — they only differ in what the window slides over.

```mermaid
flowchart TD
    A([Document]) --> B[For each page]
    B --> C{page.text blank?}
    C -- yes --> B
    C -- no --> D["i = 0"]

    D --> E{unit?}
    E -- characters --> F["window = text[i : i+size]\nchar_start = i"]
    E -- tokens --> G["tokens = encode(text)\nwindow = tokens[i : i+size]\nchunk_text = decode(window)\nchar_start = text.find(chunk_text)"]

    F --> H["make_chunk(chunk_text, char_start)"]
    G --> H

    H --> I{"i + size >= len(sequence)?"}
    I -- yes --> J([done])
    I -- no --> K["i += step"]
    K --> E
```

---

#### Character mode example — `chunk_size=10, chunk_overlap=3, step=7`

Window slides over the raw string. Every character, including spaces, counts.

```
text:    The quick brown fox jumps
char:    0123456789012345678901234  (mod 10)

chunk 0: [The quick ]                   i=0,  text[0:10]
chunk 1:        [ck brown f]            i=7,  text[7:17]
chunk 2:               [n fox jump]     i=14, text[14:24]
chunk 3:                      [umps]    i=21, text[21:25]
```

Each space counts as a character. The 3-character overlap between adjacent chunks:
- chunk 0 / chunk 1: `"ck "` (chars 7–9)
- chunk 1 / chunk 2: `"n f"` (chars 14–16)
- chunk 2 / chunk 3: `"ump"` (chars 21–23)

---

#### Token mode example — `chunk_size=5, chunk_overlap=2, step=3`

Text is encoded to token IDs once; the window slides over that list and each window is decoded back to a string. `char_start` is then located by searching the original text.

```
text:    "hello world is a different era"
tokens:  [ 15339 ][ 1917 ][  374 ][  264 ][ 2204 ][ 4325 ][ 11639]
decoded:   hello    world    is      a      diff-   -er-    -ent era

chunk 0: [ 15339  1917  374  264  2204 ]  → "hello world is a diff"    i=0
chunk 1:                [ 264  2204  4325  11639 ... ]  → "a different era"  i=3
```

The overlap (2 tokens) is shared in decoded text - context at boundaries is preserved without re-running the full encode.

---
