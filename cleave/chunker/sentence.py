# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import re
from typing import List, Optional, Tuple

# Third Party Library

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import Chunk, ChunkParams, ChunkerType, ChunkUnit, ContentType, Document, Source

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class SentenceChunker(BaseChunker):

    _CHUNKER_TYPE  = ChunkerType.sentence
    _SEPARATORS    = ['.', '!', '?']

    def __init__(self, chunk_params: ChunkParams) -> None:
        super().__init__(chunk_params)

    def chunk(self, document: Document) -> List[Chunk]:
        """Split every page in the document into sentence-boundary chunks.

        Text blocks are accumulated per page; sentence trimming is applied at page
        boundaries so cross-page sentences can carry over. Table and image blocks are
        each emitted as a single chunk in their natural position order, flushing any
        pending text first.

        Args:
            document (Document): Parsed document.

        Returns:
            List[Chunk]: All chunks across all pages in document order.
        """
        chunks: List[Chunk] = []
        global_index = 0
        spare_text: Optional[str] = None

        for page in document.pages:
            pending_text = ""
            first_text_seen = False

            for block in sorted(page.blocks, key=lambda b: b.position):
                if block.type == ContentType.text:
                    content = block.content
                    # Prepend cross-page carry-over to the first text block on this page
                    if not first_text_seen and spare_text is not None:
                        content = spare_text + content
                        spare_text = None
                    first_text_seen = True
                    if content:
                        pending_text += ("\n" if pending_text else "") + content
                else:
                    # Flush pending text (no sentence trimming — within-page flush)
                    if pending_text.strip():
                        text_chunks = self._chunk_text(
                            text=pending_text,
                            page_number=page.page_number,
                            source=document.source,
                            start_index=global_index,
                        )
                        chunks.extend(text_chunks)
                        global_index += len(text_chunks)
                        pending_text = ""
                    # Non-text block → single chunk
                    if block.content.strip():
                        chunks.append(
                            self.make_chunk(
                                text=block.content,
                                source=document.source,
                                page_number=page.page_number,
                                index=global_index,
                                char_start=0,
                                content_type=block.type,
                            )
                        )
                        global_index += 1

            # End of page: apply sentence trimming so mid-sentence text carries over
            if pending_text.strip():
                committed, leftover = self._trim_to_last_sentence(pending_text)
                spare_text = leftover
                if committed.strip():
                    text_chunks = self._chunk_text(
                        text=committed,
                        page_number=page.page_number,
                        source=document.source,
                        start_index=global_index,
                    )
                    chunks.extend(text_chunks)
                    global_index += len(text_chunks)

        # Flush any text that trailed the last sentence boundary on the last page
        if spare_text and spare_text.strip():
            text_chunks = self._chunk_text(
                text=spare_text,
                page_number=document.pages[-1].page_number,
                source=document.source,
                start_index=global_index,
            )
            chunks.extend(text_chunks)

        return chunks

    def _trim_to_last_sentence(self, text: str) -> Tuple[str, Optional[str]]:
        """Split text at its last sentence boundary.

        Args:
            text (str): Text to trim.

        Returns:
            Tuple of (committed_text, leftover) where leftover is None if no trailing text.
        """
        match = re.search(r"[.!?](?!.*[.!?])", text, re.DOTALL)
        if not match:
            return text, None
        punc_index = match.start()
        if punc_index < len(text) - 1:
            return text[:punc_index + 1], text[punc_index + 1:]
        return text, None

    def _overlap_text(self, text: str, overlap: int) -> str:
        """Return the trailing overlap text, respecting the configured unit.

        For characters: slices the last `overlap` characters directly.
        For tokens: encodes, takes the last `overlap` tokens, decodes back.

        Args:
            text (str): The committed chunk text.
            overlap (int): Overlap size in the configured unit.

        Returns:
            str: Trailing text to carry into the next chunk.
        """
        if overlap <= 0:
            return ""
        if self.chunk_params.unit == ChunkUnit.tokens:
            tokens = self.token_enc.encode(text)
            return self.token_enc.decode(tokens[-overlap:])
        return text[-overlap:]

    def _chunk_text(
        self,
        text: str,
        page_number: int | None,
        source: Source,
        start_index: int,
    ) -> List[Chunk]:
        """This function splits a single text string into sentence chunks .
 
        Operates on characters or tokens depending on chunk_params.unit:
          - characters: slides a window over the raw string directly.
          - tokens: encodes to token list, slides window, decodes each window back to string.
 
        Args:
            text (str): Page text to split.
            page_number (int | None): Page number for chunk metadata.
            source (Source): Origin source for chunk metadata.
            start_index (int): Global chunk index offset for this page.
 
        Returns:
            List[Chunk]: Chunks derived from this text in order.
        """
        size = self.chunk_params.chunk_size
        overlap = self.chunk_params.chunk_overlap
        chunks: List[Chunk] = []
        punctuation_matches = list(re.finditer(r"[.!?]", text))

        # No sentence boundaries — fall back to fixed-size splitting
        if not punctuation_matches:
            step = size - overlap
            if self.chunk_params.unit == ChunkUnit.tokens:
                tokens = self.token_enc.encode(text)
                for i in range(0, len(tokens), step):
                    window = tokens[i:i + size]
                    chunk_text = self.token_enc.decode(window)
                    chunks.append(self.make_chunk(
                        text=chunk_text,
                        source=source,
                        page_number=page_number,
                        index=start_index + len(chunks),
                        char_start=0,
                    ))
                    if i + size >= len(tokens):
                        break
            else:
                for i in range(0, len(text), step):
                    chunk_text = text[i:i + size]
                    chunks.append(self.make_chunk(
                        text=chunk_text,
                        source=source,
                        page_number=page_number,
                        index=start_index + len(chunks),
                        char_start=i,
                    ))
                    if i + size >= len(text):
                        break
            return chunks

        char_start = 0
        segment_start = 0
        current_text = ""

        for pm in punctuation_matches:
            end = pm.end()
            current_text += text[segment_start:end]
            segment_start = end
            if self._measure(current_text) >= size:
                chunks.append(self.make_chunk(
                    text=current_text,
                    source=source,
                    page_number=page_number,
                    index=start_index + len(chunks),
                    char_start=char_start,
                ))
                overlap_text = self._overlap_text(current_text, overlap)
                char_start = end - len(overlap_text)
                current_text = overlap_text

        if current_text.strip():
            chunks.append(self.make_chunk(
                text=current_text,
                source=source,
                page_number=page_number,
                index=start_index + len(chunks),
                char_start=char_start,
            ))

        return chunks