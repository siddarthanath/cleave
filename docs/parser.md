# Cleave Parsers

## Class Diagram

```
BaseParser
├── BaseModeParser
│   ├── PdfParser        (.pdf)
│   ├── DocxParser       (.docx)
│   ├── MarkdownParser   (.md)
│   └── HtmlParser       (.html / .htm)
└── TextParser           (.txt)
```

`BaseModeParser` owns mode validation and `parse()` dispatch. Subclasses implement `_parse_flat()` and `_parse_tree()`.  
`TextParser` extends `BaseParser` directly — tree mode is not supported and raises `NotImplementedError`.

---

## Parsing Modes

| Mode | `Document` field | Use when |
|------|-----------------|----------|
| `flat` _(default)_ | `.pages` — ordered `DocumentPage` list | Simple text retrieval, fixed or sentence chunking |
| `tree` | `.root` — recursive `TreeNode` hierarchy | Semantic chunking, heading-scoped retrieval, multimodal pipelines |

---

## Parser Comparison

| Format | Parser | Flat | Tree | Images | Tables | Heading detection |
|--------|--------|------|------|--------|--------|-------------------|
| `.pdf` | `PdfParser` | ✓ | ✓ | ✓ base64 | ✓ GFM | Font-size heuristic |
| `.docx` | `DocxParser` | ✓ | ✓ | ✓ base64 | ✓ GFM | Word `Heading N` styles |
| `.md` | `MarkdownParser` | ✓ | ✓ | ✓ base64 (local) | ✓ GFM | ATX markers (`# … ######`) |
| `.html` | `HtmlParser` | ✓ | ✓ | ✓ src string¹ | ✓ GFM | `<h1>`–`<h6>` tags |
| `.txt` | `TextParser` | ✓ | ✗ | ✗ | ✗ | n/a |

¹ HTML images store the `src` attribute value. Base64 encoding for local paths is a future enhancement.

---

## Flat Mode Flow

```
file
 └─ read raw text / bytes
     └─ walk content in document order
         ├─ heading / paragraph / list item → ContentBlock(type=text)
         ├─ table                           → ContentBlock(type=table, GFM markdown)
         └─ image                          → ContentBlock(type=image, base64 or src)
             └─ DocumentPage(page_number, blocks=[...])
                 └─ Document(source, pages=[page], total_pages=N)
```

### Per-parser flat specifics

**PdfParser** — uses PyMuPDF; text blocks sorted by y-coordinate; table bboxes masked to prevent duplicate cell text; images extracted via xref.

**DocxParser** — iterates `document.paragraphs` and `document.tables` in XML order; images extracted from `document.inline_shapes`.

**MarkdownParser** — regex line-scanner; `_HEADING_RE`, `_TABLE_ROW_RE`, `_STANDALONE_IMAGE_RE`; local images base64-encoded relative to the `.md` file.

**HtmlParser** — BeautifulSoup DOM walk; `_HEADING_TAGS`, `_TEXT_TAGS`, `_TABLE_TAG`, `_IMAGE_TAG` class constants; `<table>` converted to GFM via `_table_to_markdown`.

**TextParser** — splits on blank lines; no heading, image, or table detection.

---

## Tree Mode Flow

```
file
 └─ read raw text / bytes
     └─ heading-level stack  (level 0 = root, never popped)
         ├─ heading tag/marker → push TreeNode(role="heading", level=N) onto stack
         ├─ paragraph / text  → TreeNode(role="paragraph") child of stack top
         ├─ table             → atomic TreeNode(type=table) child of stack top
         └─ image             → atomic TreeNode(type=image) child of stack top
             └─ Document(source, root=TreeNode)
```

### Heading detection comparison

| Parser | Source of heading signal | Reliability |
|--------|--------------------------|-------------|
| `DocxParser` | Word `Heading N` paragraph styles | Deterministic |
| `MarkdownParser` | ATX `#` prefix count | Deterministic |
| `HtmlParser` | `<h1>`–`<h6>` tag name | Deterministic |
| `PdfParser` | Largest font size → H1, next → H2, … | Heuristic |

---

## Bridge — Tree → Text Chunker

`Document.to_markdown()` serialises a tree document back to a flat Markdown string, preserving heading levels as `#` prefixes.

```python
doc = ParserFactory.create("paper.pdf", mode="tree").parse()
md  = doc.to_markdown()   # pass to FixedChunker / SentenceChunker / RecursiveChunker
```

Image bytes stay in `TreeNode.content` and are never emitted into the bridge string.

---

## Factory

```python
from cleave.parsers.factory import ParserFactory

doc = ParserFactory.create("report.pdf").parse()             # flat (default)
doc = ParserFactory.create("notes.md", mode="tree").parse()  # tree
doc = ParserFactory.create("page.html", mode="flat").parse() # html flat
```

`ParserFactory._PARSER_REGISTRY` maps extension → parser class. Add new parsers there.
