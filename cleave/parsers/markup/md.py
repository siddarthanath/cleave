# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import re
from pathlib import Path
from typing import List, Tuple

# Third Party Library

# Private Library
from cleave.parsers.base import BaseModeParser
from cleave.utils.image import encode_image, resolve_image
from cleave.schemas import (
    ContentBlock,
    ContentType,
    Document,
    DocumentPage,
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Matches ATX headings: "# Title", "## Title", up to H6
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Matches a GFM table row: any line that starts and ends with |
_TABLE_ROW_RE = re.compile(r"^\|.+\|$")

# Matches a standalone image reference occupying the whole line
_STANDALONE_IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


class MarkdownParser(BaseModeParser):
    """Parser for Markdown (.md) files supporting flat and tree output modes.

    Flat mode  — one virtual DocumentPage containing text, table, and image
                 ContentBlocks extracted in document order. Heading lines are
                 emitted as individual text blocks (raw Markdown syntax preserved).

    Tree mode  — a TreeNode hierarchy built from ATX heading levels (# … ######).
                 Body paragraphs become children of the nearest ancestor heading.
                 GFM tables and standalone images are atomic leaf nodes.
                 Remote image URLs are stored as-is; local image files are
                 base64-encoded when they can be resolved relative to the .md file.
    """

    def __init__(self, file_path: str, mode: str = "flat") -> None:
        super().__init__(file_path, mode)
        # Used to resolve relative image paths
        self._base_dir = Path(file_path).parent

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    FLAT PATH                                       ║
# ║                        (Sequential Block Extraction)                               ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_flat(self) -> Document:
        """Extract blocks in document order into a single virtual page."""
        raw = Path(self.source.location).read_text(encoding="utf-8")
        if not raw.strip():
            raise ValueError(f"No extractable content found in '{self.source.location}'")
        blocks = self._extract_blocks(raw)
        if not blocks:
            raise ValueError(f"No extractable content found in '{self.source.location}'")
        page = DocumentPage(page_number=None, blocks=blocks)
        return Document(source=self.source, pages=[page], total_pages=1)

    def _extract_blocks(self, raw: str) -> List[ContentBlock]:
        """Classify lines into text, table, and image ContentBlocks.

        Tables are grouped as single blocks. Standalone images become image
        blocks. ATX heading lines are emitted as individual text blocks.
        All other non-blank content is accumulated into paragraph text blocks.

        Args:
            raw: Full Markdown file content.

        Returns:
            Ordered list of ContentBlocks.
        """
        blocks: List[ContentBlock] = []
        position = 0
        lines = raw.splitlines()
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()

            if not stripped:
                i += 1
                continue

            # ATX heading — emit as a standalone text block in flat mode
            if _HEADING_RE.match(stripped):
                blocks.append(ContentBlock(
                    type=ContentType.text,
                    content=stripped,
                    position=position,
                ))
                position += 1
                i += 1
                continue

            # GFM table: collect all consecutive pipe-bordered rows
            if _TABLE_ROW_RE.match(stripped):
                table_lines, i = self._collect_table(lines, i)
                md = "\n".join(table_lines)
                blocks.append(ContentBlock(type=ContentType.table, content=md, position=position))
                position += 1
                continue

            # Standalone image on its own line
            img_match = _STANDALONE_IMAGE_RE.match(stripped)
            if img_match:
                alt, src = img_match.group(1), img_match.group(2)
                image_path = resolve_image(src, self._base_dir)
                content = encode_image(image_path) if image_path else src
                if content:
                    blocks.append(ContentBlock(
                        type=ContentType.image,
                        content=content,
                        position=position,
                    ))
                    position += 1
                i += 1
                continue

            # Paragraph: collect until blank line or structural element
            para_lines, i = self._collect_paragraph(lines, i)
            text = "\n".join(para_lines).strip()
            if text:
                blocks.append(ContentBlock(type=ContentType.text, content=text, position=position))
                position += 1

        return blocks

# ╔════════════════════════════════════════════════════════════════════════════════════╗
# ║                                    TREE PATH                                       ║
# ║                        (Heading-Scoped Hierarchy Building)                         ║
# ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_tree(self) -> Document:
        """Build a TreeNode hierarchy from heading levels."""
        raw = Path(self.source.location).read_text(encoding="utf-8")
        root = self._build_tree(raw)
        return Document(source=self.source, root=root)

    def _build_tree(self, raw: str) -> TreeNode:
        """Parse ATX headings as tree nodes and attach body content as children.

        Uses a heading-level stack (same pattern as DocxParser). Body paragraphs,
        tables, and images are attached as children of the current top-of-stack
        heading node.

        Args:
            raw: Full Markdown file content.

        Returns:
            Populated root TreeNode.
        """
        root = TreeNode(
            content_type=ContentType.text,
            content="",
            metadata={"role": "root"},
        )
        # Stack entries: (heading_level, node) — level 0 = root, never popped
        stack: List[tuple] = [(0, root)]

        lines = raw.splitlines()
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()

            if not stripped:
                i += 1
                continue

            heading_match = _HEADING_RE.match(stripped)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                node = TreeNode(
                    content_type=ContentType.text,
                    content=content,
                    metadata={"role": "heading", "level": level},
                )
                stack[-1][1].children.append(node)
                stack.append((level, node))
                i += 1
                continue

            if _TABLE_ROW_RE.match(stripped):
                table_lines, i = self._collect_table(lines, i)
                node = TreeNode(
                    content_type=ContentType.table,
                    content="\n".join(table_lines),
                    metadata={},
                )
                stack[-1][1].children.append(node)
                continue

            img_match = _STANDALONE_IMAGE_RE.match(stripped)
            if img_match:
                alt, src = img_match.group(1), img_match.group(2)
                image_path = resolve_image(src, self._base_dir)
                content = encode_image(image_path) if image_path else src
                node = TreeNode(
                    content_type=ContentType.image,
                    content=content,
                    metadata={"alt": alt, "src": src},
                )
                stack[-1][1].children.append(node)
                i += 1
                continue

            para_lines, i = self._collect_paragraph(lines, i)
            text = "\n".join(para_lines).strip()
            if text:
                node = TreeNode(
                    content_type=ContentType.text,
                    content=text,
                    metadata={"role": "paragraph"},
                )
                stack[-1][1].children.append(node)

        return root

    @staticmethod
    def _collect_table(lines: List[str], i: int) -> Tuple[List[str], int]:
        """Consume consecutive GFM table rows starting at index i.

        Args:
            lines: All document lines.
            i: Index of the first table row.

        Returns:
            Tuple of (collected row strings, next index after the table).
        """
        table_lines: List[str] = []
        while i < len(lines) and _TABLE_ROW_RE.match(lines[i].strip()):
            table_lines.append(lines[i])
            i += 1
        return table_lines, i

    @staticmethod
    def _collect_paragraph(lines: List[str], i: int) -> Tuple[List[str], int]:
        """Collect body-text lines until a blank line or structural element.

        Args:
            lines: All document lines.
            i: Index of the first paragraph line.

        Returns:
            Tuple of (collected lines, next index after the paragraph).
        """
        para_lines: List[str] = []
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                break
            if (
                _HEADING_RE.match(stripped)
                or _TABLE_ROW_RE.match(stripped)
                or _STANDALONE_IMAGE_RE.match(stripped)
            ):
                break
            para_lines.append(lines[i])
            i += 1
        return para_lines, i

