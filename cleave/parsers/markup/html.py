# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path
from typing import List, Optional, Tuple

# Third Party Library
from bs4 import BeautifulSoup, Tag

# Private Library
from cleave.parsers.base import BaseParser, BaseModeParser
from cleave.utils.image import encode_image, resolve_image
from cleave.schemas import (
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class HtmlParser(BaseModeParser):
    """Parser for HTML (.html / .htm) files and HTTP/HTTPS URLs.

    Accepts either a local file path or a URL. For URLs, fetches the HTML
    via httpx (requires cleave[html]) and parses the response in-memory.

    Flat mode  — one virtual DocumentPage containing text, table, and image
                 ContentBlocks extracted in document order. Heading tags are
                 emitted as individual text blocks (plain text, no markup).

    Tree mode  — a TreeNode hierarchy built from heading levels (h1–h6).
                 Body paragraphs and list items become children of the nearest
                 ancestor heading. Tables are atomic leaf nodes.

    Local image paths are resolved relative to the HTML file and base64-encoded
    as data URIs. Remote image URLs are stored as-is.
    """

    _HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
    _TEXT_TAGS    = ("p", "li", "blockquote", "dd", "dt")
    _BLOCK_TAGS   = ("div", "section", "article", "main")
    _TABLE_TAG    = "table"
    _IMAGE_TAG    = "img"
    _CODE_TAG     = "pre"

    def __init__(self, file_path: str, mode: str = "flat") -> None:
        self._raw_html: Optional[str] = None

        if file_path.startswith("http://") or file_path.startswith("https://"):
            try:
                import httpx
            except ImportError as e:
                raise ImportError(
                    "Fetching URLs requires httpx. Install it with: pip install cleave[html]"
                ) from e
            response = httpx.get(file_path, follow_redirects=True, timeout=30)
            response.raise_for_status()
            self._raw_html = response.text
            # Bypass BaseModeParser (which calls _make_source expecting a file path)
            # and initialise manually using the URL source.
            BaseParser.__init__(self, BaseParser._make_url_source(file_path))
            if mode not in ("flat", "tree"):
                raise ValueError(f"mode must be 'flat' or 'tree', got {mode!r}")
            self._mode = mode
        else:
            super().__init__(file_path, mode)

    def _parse_soup(self) -> BeautifulSoup:
        """Return a BeautifulSoup tree from fetched HTML or a local file.

        Returns:
            BeautifulSoup: Parsed HTML document.
        """
        if self._raw_html is not None:
            raw = self._raw_html
        else:
            raw = Path(self.source.location).read_text(encoding="utf-8")
        if not raw.strip():
            raise ValueError(f"No extractable content found in '{self.source.location}'")
        return BeautifulSoup(raw, "html.parser")

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    FLAT PATH                                       ║
# ║                        (Sequential Block Extraction)                               ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_flat(self) -> Document:
        """Extract blocks in document order into a single virtual page."""
        soup = self._parse_soup()
        blocks = self._extract_blocks(soup)
        if not blocks:
            raise ValueError(f"No extractable content found in '{self.source.location}'")
        page = DocumentPage(page_number=None, blocks=blocks)
        return Document(source=self.source, pages=[page], total_pages=1)

    def _extract_blocks(self, soup: BeautifulSoup) -> List[ContentBlock]:
        """Walk the DOM in document order and classify elements into ContentBlocks.

        Headings → text block. Paragraphs and list items → text block.
        Tables → markdown-formatted table block. Images → image block (src as content).
        Block-level containers (div, section, etc.) are traversed but not emitted.

        Args:
            soup: Parsed BeautifulSoup document.

        Returns:
            Ordered list of ContentBlocks.
        """
        blocks: List[ContentBlock] = []
        position = 0
        body = soup.find("body") or soup

        for element in body.descendants:
            if not isinstance(element, Tag):
                continue

            tag = element.name

            if tag in self._HEADING_TAGS:
                text = element.get_text(strip=True)
                if text:
                    blocks.append(ContentBlock(
                        type=ContentType.text,
                        content=text,
                        position=position,
                    ))
                    position += 1

            elif tag in self._TEXT_TAGS:
                # Skip list items that are nested inside a table cell
                if element.find_parent(self._TABLE_TAG):
                    continue
                text = element.get_text(separator=" ", strip=True)
                if text:
                    blocks.append(ContentBlock(
                        type=ContentType.text,
                        content=text,
                        position=position,
                    ))
                    position += 1

            elif tag == self._CODE_TAG:
                code = element.get_text()
                if code.strip():
                    lang = ""
                    inner = element.find("code")
                    if inner:
                        cls = " ".join(inner.get("class", []))
                        lang = cls.replace("language-", "").strip()
                    blocks.append(ContentBlock(
                        type=ContentType.text,
                        content=f"```{lang}\n{code.rstrip()}\n```",
                        position=position,
                    ))
                    position += 1

            elif tag == self._TABLE_TAG:
                md = self._table_to_markdown(element)
                if md:
                    blocks.append(ContentBlock(
                        type=ContentType.table,
                        content=md,
                        position=position,
                    ))
                    position += 1

            elif tag == self._IMAGE_TAG:
                src = element.get("src", "").strip()
                if src:
                    image_path = resolve_image(src, Path(self.source.location).parent)
                    content = encode_image(image_path) if image_path else src
                    blocks.append(ContentBlock(
                        type=ContentType.image,
                        content=content,
                        position=position,
                    ))
                    position += 1

        return blocks

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    TREE PATH                                       ║
# ║                        (Heading-Scoped Hierarchy Building)                         ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_tree(self) -> Document:
        """Build a TreeNode hierarchy from heading levels."""
        soup = self._parse_soup()
        root = self._build_tree(soup)
        return Document(source=self.source, root=root)

    def _build_tree(self, soup: BeautifulSoup) -> TreeNode:
        """Parse heading tags as tree nodes and attach body content as children.

        Uses the same heading-level stack pattern as MarkdownParser and DocxParser.
        Text elements attach to the current top-of-stack heading. Tables and images
        are atomic leaf nodes.

        Args:
            soup: Parsed BeautifulSoup document.

        Returns:
            Populated root TreeNode.
        """
        root = TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
        )
        # Stack entries: (heading_level, node) — level 0 = root, never popped
        stack: List[Tuple[int, TreeNode]] = [(0, root)]

        body = soup.find("body") or soup

        for element in body.descendants:
            if not isinstance(element, Tag):
                continue

            tag = element.name

            if tag in self._HEADING_TAGS:
                level = int(tag[1])
                content = element.get_text(strip=True)
                if not content:
                    continue
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                node = TreeNode(
                    content_type=ContentType.text,
                    content=content,
                    metadata={"role": "heading", "level": level},
                )
                stack[-1][1].children.append(node)
                stack.append((level, node))

            elif tag in self._TEXT_TAGS:
                if element.find_parent(self._TABLE_TAG):
                    continue
                text = element.get_text(separator=" ", strip=True)
                if text:
                    node = TreeNode(
                        content_type=ContentType.text,
                        content=text,
                        metadata={"role": "paragraph"},
                    )
                    stack[-1][1].children.append(node)

            elif tag == self._CODE_TAG:
                code = element.get_text()
                if code.strip():
                    lang = ""
                    inner = element.find("code")
                    if inner:
                        cls = " ".join(inner.get("class", []))
                        lang = cls.replace("language-", "").strip()
                    node = TreeNode(
                        content_type=ContentType.text,
                        content=f"```{lang}\n{code.rstrip()}\n```",
                        metadata={"role": "code"},
                    )
                    stack[-1][1].children.append(node)

            elif tag == self._TABLE_TAG:
                # Skip nested tables already captured by a parent table element
                if element.find_parent(self._TABLE_TAG):
                    continue
                md = self._table_to_markdown(element)
                if md:
                    node = TreeNode(
                        content_type=ContentType.table,
                        content=md,
                        metadata={},
                    )
                    stack[-1][1].children.append(node)

            elif tag == self._IMAGE_TAG:
                src = element.get("src", "").strip()
                alt = element.get("alt", "").strip()
                if src:
                    image_path = resolve_image(src, Path(self.source.location).parent)
                    content = encode_image(image_path) if image_path else src
                    node = TreeNode(
                        content_type=ContentType.image,
                        content=content,
                        metadata={"alt": alt, "src": src},
                    )
                    stack[-1][1].children.append(node)

        return root

    @staticmethod
    def _table_to_markdown(table: Tag) -> str:
        """Convert an HTML table element to a GFM markdown table string.

        Only the first header row is used for column headers. Subsequent rows
        become data rows. Empty tables return an empty string.

        Args:
            table: BeautifulSoup Tag for the <table> element.

        Returns:
            GFM markdown table string, or "" if the table has no usable rows.
        """
        rows: List[List[str]] = []

        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        col_count = max(len(r) for r in rows)

        def pad(row: List[str]) -> List[str]:
            return row + [""] * (col_count - len(row))

        header = pad(rows[0])
        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in rows[1:]:
            md_lines.append("| " + " | ".join(pad(row)) + " |")

        return "\n".join(md_lines)
