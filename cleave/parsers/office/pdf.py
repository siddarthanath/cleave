# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import base64
from collections import Counter
from typing import List

# Third Party Library
try:
    import fitz  # pymupdf
except ImportError as e:
    raise ImportError(
        "PdfParser requires pymupdf. Install it with: pip install cleave[pdf]"
    ) from e

# Private Library
from cleave.parsers.base import BaseModeParser
from cleave.schemas import (
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class PdfParser(BaseModeParser):
    """Parser for PDF documents supporting flat and tree output modes.

    Flat mode  — one DocumentPage per PDF page; text, images, and tables
                 extracted as ContentBlocks in position order.

    Tree mode  — a single TreeNode hierarchy built from font-size heuristics.
                 Spans whose font size exceeds the body-text mode are treated
                 as headings; their level is determined by size rank (largest
                 font → H1). Body paragraphs become children of the nearest
                 ancestor heading. Tables and images are atomic leaf nodes.
    """

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    FLAT PATH                                       ║
# ║                        (Sequential Page-Block Extraction)                          ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_flat(self) -> Document:
        """Extract text, images, and tables page-by-page into a flat Document."""
        pdf = fitz.open(self.source.location)
        pages: List[DocumentPage] = []

        for page_num, page in enumerate(pdf, start=1):
            blocks: List[ContentBlock] = []
            position = 0

            text = page.get_text().strip()
            if text:
                blocks.append(ContentBlock(
                    type=ContentType.text,
                    content=text,
                    position=position,
                ))
                position += 1

            for img_info in page.get_images(full=True):
                b64 = self._extract_image_b64(pdf, img_info[0])
                if b64:
                    blocks.append(ContentBlock(
                        type=ContentType.image,
                        content=b64,
                        position=position,
                    ))
                    position += 1

            for table in page.find_tables().tables:
                md = self._table_to_markdown(table.extract())
                if md:
                    blocks.append(ContentBlock(
                        type=ContentType.table,
                        content=md,
                        position=position,
                    ))
                    position += 1

            if blocks:
                pages.append(DocumentPage(page_number=page_num, blocks=blocks))

        pdf.close()

        if not pages:
            raise ValueError(f"No extractable content found in '{self.source.location}'")

        return Document(source=self.source, pages=pages, total_pages=len(pages))

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    TREE PATH                                       ║
# ║                        (Font-Size Heading Hierarchy Building)                      ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_tree(self) -> Document:
        """Build a TreeNode hierarchy from font-size heading detection."""
        pdf = fitz.open(self.source.location)
        size_to_level = self._detect_heading_levels(pdf)

        root = TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
        )
        # Stack entries: (heading_level, node) — level 0 = root, never popped
        stack: List[tuple] = [(0, root)]

        for page_num, page in enumerate(pdf, start=1):
            events = self._collect_page_events(pdf, page, page_num, size_to_level)
            events.sort(key=lambda e: e[0])  # process top-to-bottom by y

            for _, item in events:
                if isinstance(item, TreeNode):
                    stack[-1][1].children.append(item)
                else:
                    content, level = item
                    if level is not None:
                        while len(stack) > 1 and stack[-1][0] >= level:
                            stack.pop()
                        node = TreeNode(
                            content_type=ContentType.text,
                            content=content,
                            metadata={"role": "heading", "level": level, "page_number": page_num},
                        )
                        stack[-1][1].children.append(node)
                        stack.append((level, node))
                    else:
                        node = TreeNode(
                            content_type=ContentType.text,
                            content=content,
                            metadata={"role": "paragraph", "page_number": page_num},
                        )
                        stack[-1][1].children.append(node)

        pdf.close()
        return Document(source=self.source, root=root)

    def _collect_page_events(
        self,
        pdf: "fitz.Document",
        page: "fitz.Page",
        page_num: int,
        size_to_level: dict,
    ) -> list:
        """Collect all content events for one page as (y, item) tuples.

        Items are either a TreeNode (image or table) or a ``(content, level)``
        tuple where level is an int for headings or None for paragraphs.
        Table bounding boxes are collected first so overlapping text blocks are
        skipped, avoiding duplicate cell text as paragraph nodes.

        Args:
            pdf: Open pymupdf document used for image extraction.
            page: The current pymupdf page being processed.
            page_num: 1-based page number, stored in node metadata.
            size_to_level: Mapping from rounded font size to heading level.

        Returns:
            List of (y_coordinate, item) tuples unsorted — caller sorts by y.
        """
        events = []

        # Collect tables first so their bboxes can mask overlapping text
        table_bboxes = []
        for table in page.find_tables().tables:
            md = self._table_to_markdown(table.extract())
            if md:
                table_bboxes.append(table.bbox)
                node = TreeNode(
                    content_type=ContentType.table,
                    content=md,
                    metadata={"page_number": page_num},
                )
                events.append((table.bbox[1], node))

        for img_info in page.get_images(full=True):
            xref = img_info[0]
            b64 = self._extract_image_b64(pdf, xref)
            if not b64:
                continue
            rects = page.get_image_rects(xref)
            y = rects[0].y0 if rects else 0
            node = TreeNode(
                content_type=ContentType.image,
                content=b64,
                metadata={"page_number": page_num, "alt": f"image_p{page_num}"},
            )
            events.append((y, node))

        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            if any(self._bbox_overlaps(block["bbox"], tb) for tb in table_bboxes):
                continue

            span_texts: List[str] = []
            span_sizes: List[float] = []
            for line in block["lines"]:
                for span in line["spans"]:
                    t = span["text"].strip()
                    if t:
                        span_texts.append(t)
                        span_sizes.append(round(span["size"], 1))

            if not span_texts:
                continue

            content = " ".join(span_texts)
            dominant_size = Counter(span_sizes).most_common(1)[0][0]
            level = size_to_level.get(dominant_size)
            events.append((block["bbox"][1], (content, level)))

        return events

    def _detect_heading_levels(self, pdf: "fitz.Document") -> dict:
        """Two-pass font-size analysis to produce a ``{size: heading_level}`` mapping.

        The body-text size is the statistical mode across all spans. Any size
        more than 0.5pt above body is considered a heading; sizes are ranked
        largest-first so the biggest font becomes H1.

        Args:
            pdf: Open pymupdf document to analyse.

        Returns:
            Mapping of rounded font size (float) to heading level (int, 1-based).
            Empty dict when no heading sizes are detected.
        """
        all_sizes: List[float] = []
        for page in pdf:
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            all_sizes.append(round(span["size"], 1))

        if not all_sizes:
            return {}

        body_size = Counter(all_sizes).most_common(1)[0][0]
        heading_sizes = sorted(
            {s for s in all_sizes if s > body_size + 0.5},
            reverse=True,
        )
        return {size: level for level, size in enumerate(heading_sizes, start=1)}

    @staticmethod
    def _bbox_overlaps(a: tuple, b: tuple) -> bool:
        """Return True if two ``(x0, y0, x1, y1)`` bounding boxes overlap.

        Args:
            a: First bounding box as (x0, y0, x1, y1).
            b: Second bounding box as (x0, y0, x1, y1).

        Returns:
            True if the boxes share any area, False if they are disjoint.
        """
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    @staticmethod
    def _extract_image_b64(pdf: "fitz.Document", xref: int) -> str:
        """Extract an image by xref and return it as a base64 string.

        Args:
            pdf: Open pymupdf document.
            xref: Image cross-reference number.

        Returns:
            Base64-encoded image bytes, or "" on failure.
        """
        try:
            img_data = pdf.extract_image(xref)
            return base64.b64encode(img_data["image"]).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def _table_to_markdown(data: List[List]) -> str:
        """Convert a list-of-lists table to a GitHub-Flavoured Markdown string.

        Args:
            data: Rows of cell values as returned by ``fitz.Table.extract()``.

        Returns:
            Markdown table string, or "" if data is empty.
        """
        if not data:
            return ""
        rows: List[str] = []
        for i, row in enumerate(data):
            cells = [str(c or "").replace("\n", " ").strip() for c in row]
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                rows.append("| " + " | ".join("---" for _ in cells) + " |")
        return "\n".join(rows)
