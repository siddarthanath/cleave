# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Dict, List, Optional

# Third Party Library

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import (
    Chunk,
    ChunkParams,
    ChunkUnit,
    ChunkerType,
    ContentType,
    Document,
    Source,
    TreeNode,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class RecursiveChunker(BaseChunker):
    """Dual-path chunker that adapts to document structure.

    Tree path  (document.root is set):
      Walks the TreeNode hierarchy. Keeps semantically related nodes together.
      Tables and images are always emitted as a single atomic chunk.
      Falls back to string-based splitting only for oversized leaf nodes.

    Flat path  (document.pages is set):
      Applies a delimiter hierarchy over each page's text, grouping pieces
      greedily until chunk_size is reached. Falls back to a fixed-size sliding
      window only when a single piece cannot be split further.

    Pass custom_delimiters to override the default delimiter hierarchy, e.g. for
    code files use DELIMITER_PRESETS["python"] or supply your own list.
    """

    _CHUNKER_TYPE = ChunkerType.recursive
    _DEFAULT_DELIMITERS: List[str] = ["\n# ", "\n## ", "\n### ", "\n\n", "\n", " "]

    DELIMITER_PRESETS: Dict[str, List[str]] = {
        "default":  ["\n# ", "\n## ", "\n### ", "\n\n", "\n", " "],
        "python":   ["\nclass ", "\ndef ", "\n\n", "\n", " "],
        "js":       ["\nfunction ", "\nconst ", "\nclass ", "\n\n", "\n", " "],
        "markdown": ["\n# ", "\n## ", "\n### ", "\n\n", "\n", " "],
        "html":     ["</div>", "</section>", "</p>", "\n\n", "\n", " "],
        "latex":    ["\\chapter{", "\\section{", "\\subsection{", "\n\n", "\n", " "],
    }

    def __init__(
        self,
        chunk_params: ChunkParams,
        custom_delimiters: Optional[List[str]] = None,
    ) -> None:
        super().__init__(chunk_params)
        self._delimiters = custom_delimiters if custom_delimiters is not None else self._DEFAULT_DELIMITERS

    def chunk(self, document: Document) -> List[Chunk]:
        """Split a Document into chunks using tree-walk or string-recursive strategy.

        Args:
            document (Document): Parsed document (flat or tree).

        Returns:
            List[Chunk]: All chunks in document order (index 0, 1, 2 …).
        """
        chunks: List[Chunk] = []

        if document.root:
            self._recursive_walk_tree(
                node=document.root,
                chunks=chunks,
                source=document.source,
                char_offset=0,
            )
        else:
            for page in document.pages:
                page_text = page.text
                if not page_text.strip():
                    continue
                self._recursive_split_text(
                    text=page_text,
                    delimiters=self._delimiters,
                    chunks=chunks,
                    source=document.source,
                    page_number=page.page_number,
                    char_offset=0,
                )

        return chunks

    # ── Tree path ─────────────────────────────────────────────────────────── #

    def _recursive_walk_tree(
        self,
        node: TreeNode,
        chunks: List[Chunk],
        source: Source,
        char_offset: int,
    ) -> int:
        """Walk the TreeNode hierarchy and emit chunks.

        Atomicity rule: ContentType.table and ContentType.image nodes are always
        emitted as a single chunk regardless of size.

        If a node and all its descendants fit within chunk_size they are emitted
        together. If not, the chunker recurses into the node's children. A leaf
        node that still exceeds chunk_size is handed to _recursive_split_text.

        Args:
            node (TreeNode): Current node to process.
            chunks (List[Chunk]): Accumulator — chunks are appended in place.
            source (Source): Origin source for chunk metadata.
            char_offset (int): Running global character offset across the document.

        Returns:
            int: Updated char_offset after processing this node.
        """
        page_number = node.metadata.get("page_number")

        # Atomicity rule: tables and images are never split.
        if node.content_type in (ContentType.table, ContentType.image):
            if node.content:
                chunks.append(self.make_chunk(
                    text=node.content,
                    source=source,
                    page_number=page_number,
                    index=len(chunks),
                    char_start=char_offset,
                    content_type=node.content_type,
                ))
                char_offset += len(node.content)
            return char_offset

        full_text = node.get_full_text()

        # Empty structural node: recurse into children directly
        if not full_text.strip():
            for child in node.children:
                char_offset = self._recursive_walk_tree(child, chunks, source, char_offset)
            return char_offset

        # Fits within chunk_size: emit as one chunk only when the subtree is
        # purely text — otherwise fall through to child recursion so table/image
        # atoms are emitted with their correct content types.
        if self._measure(full_text) <= self.chunk_params.chunk_size:
            if not self._has_non_text_descendants(node):
                chunks.append(self.make_chunk(
                    text=full_text,
                    source=source,
                    page_number=page_number,
                    index=len(chunks),
                    char_start=char_offset,
                    content_type=ContentType.text,
                ))
                return char_offset + len(full_text)

        # Too large and has children: recurse into each child independently
        if node.children:
            for child in node.children:
                char_offset = self._recursive_walk_tree(child, chunks, source, char_offset)
            return char_offset

        # Leaf node still too large: fall back to string-based recursive split
        return self._recursive_split_text(
            text=full_text,
            delimiters=self._delimiters,
            chunks=chunks,
            source=source,
            page_number=page_number,
            char_offset=char_offset,
        )

    @staticmethod
    def _has_non_text_descendants(node: TreeNode) -> bool:
        """Return True if node or any descendant has a non-text content type.

        Args:
            node (TreeNode): Root of the subtree to inspect.

        Returns:
            bool: True if any table or image node exists in the subtree.
        """
        if node.content_type in (ContentType.table, ContentType.image):
            return True
        return any(RecursiveChunker._has_non_text_descendants(c) for c in node.children)

    # ── Flat / string path ────────────────────────────────────────────────── #

    def _recursive_split_text(
        self,
        text: str,
        delimiters: List[str],
        chunks: List[Chunk],
        source: Source,
        page_number: int | None,
        char_offset: int,
    ) -> int:
        """Recursively split text using a priority-ordered delimiter hierarchy.

        Tries delimiters from highest to lowest priority. Greedily accumulates
        pieces until the next piece would push the buffer over chunk_size, then
        commits the buffer (recursing with remaining delimiters). Falls back to
        _hard_split when no delimiters remain.

        Leading/trailing whitespace is stripped from emitted chunk text; the raw
        length (including whitespace) still advances char_offset so offsets remain
        consistent with the original text.

        Args:
            text (str): Text to split.
            delimiters (List[str]): Remaining delimiter candidates, highest priority first.
            chunks (List[Chunk]): Accumulator.
            source (Source): Origin source for chunk metadata.
            page_number (int | None): Page number for chunk metadata.
            char_offset (int): Running character offset.

        Returns:
            int: Updated char_offset.
        """
        # Base case: fits in one chunk
        if self._measure(text) <= self.chunk_params.chunk_size:
            stripped = text.strip()
            if stripped:
                leading = len(text) - len(text.lstrip())
                chunks.append(self.make_chunk(
                    text=stripped,
                    source=source,
                    page_number=page_number,
                    index=len(chunks),
                    char_start=char_offset + leading,
                ))
            return char_offset + len(text)

        # No delimiters left: hard fixed-size split
        if not delimiters:
            return self._hard_split(text, chunks, source, page_number, char_offset)

        sep = delimiters[0]
        rest = delimiters[1:]

        # Separator absent in text: skip to next delimiter.
        if sep not in text:
            return self._recursive_split_text(text, rest, chunks, source, page_number, char_offset)

        # Split on separator, keeping it attached to the start of each subsequent piece
        # so the original text can be reconstructed from pieces without information loss.
        raw_pieces = text.split(sep)
        pieces = [raw_pieces[0]] + [sep + p for p in raw_pieces[1:]]
        pieces = [p for p in pieces if p]

        buffer = ""
        for piece in pieces:
            candidate = buffer + piece
            if self._measure(candidate) <= self.chunk_params.chunk_size:
                buffer = candidate
            else:
                # Buffer is full: commit it
                if buffer:
                    char_offset = self._recursive_split_text(
                        buffer, rest, chunks, source, page_number, char_offset
                    )
                # Handle current piece
                if self._measure(piece) > self.chunk_params.chunk_size:
                    # Piece alone is too large: recurse further.
                    char_offset = self._recursive_split_text(
                        piece, rest, chunks, source, page_number, char_offset
                    )
                    buffer = ""
                else:
                    buffer = piece

        # Commit any remaining buffer
        if buffer:
            char_offset = self._recursive_split_text(
                buffer, rest, chunks, source, page_number, char_offset
            )

        return char_offset

    def _hard_split(
        self,
        text: str,
        chunks: List[Chunk],
        source: Source,
        page_number: int | None,
        char_offset: int,
    ) -> int:
        """Fixed-size sliding window split. Last resort when no delimiter can reduce the text further.

        Mirrors FixedChunker._chunk_text but appends to a shared accumulator and
        returns the updated char_offset so callers can continue tracking position.

        Args:
            text (str): Text to hard-split.
            chunks (List[Chunk]): Accumulator.
            source (Source): Origin source for chunk metadata.
            page_number (int | None): Page number for chunk metadata.
            char_offset (int): Running character offset into the original document text.

        Returns:
            int: Updated char_offset (char_offset + len(text)).
        """
        size = self.chunk_params.chunk_size
        overlap = self.chunk_params.chunk_overlap
        step = size - overlap

        if self.chunk_params.unit == ChunkUnit.tokens:
            tokens = self.token_enc.encode(text)
            total = len(tokens)
            local_char = 0
            for i in range(0, total, step):
                window = tokens[i:i + size]
                chunk_text = self.token_enc.decode(window)
                pos = text.find(chunk_text, local_char)
                if pos == -1:
                    pos = local_char
                chunks.append(self.make_chunk(
                    text=chunk_text,
                    source=source,
                    page_number=page_number,
                    index=len(chunks),
                    char_start=char_offset + pos,
                ))
                local_char = pos + 1
                if i + size >= total:
                    break
        else:
            total = len(text)
            for i in range(0, total, step):
                chunk_text = text[i:i + size]
                chunks.append(self.make_chunk(
                    text=chunk_text,
                    source=source,
                    page_number=page_number,
                    index=len(chunks),
                    char_start=char_offset + i,
                ))
                if i + size >= total:
                    break

        return char_offset + len(text)
