

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import Chunk, ChunkParams, ChunkUnit, ChunkerType, Document, Source

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class FixedChunker(BaseChunker):

    _CHUNKER_TYPE = ChunkerType.fixed

    def __init__(self, chunk_params: ChunkParams) -> None:
        super().__init__(chunk_params)

    def chunk(self, document: Document) -> List[Chunk]:
        """This function splits every page in the document into fixed-size chunks.
 
        Args:
            document (Document): Parsed document.
 
        Returns:
            List[Chunk]: All chunks across all pages in document order.
        """
        chunks: List[Chunk] = []
        global_index = 0

        for page in document.pages:
            page_chunks = self._chunk_page(page=page, source=document.source, start_index=global_index)
            chunks.extend(page_chunks)
            global_index += len(page_chunks)

        return chunks

    def _chunk_text(
        self,
        text: str,
        page_number: int | None,
        source: Source,
        start_index: int,
    ) -> List[Chunk]:
        """This function splits a single text string into fixed-size chunks.
 
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
        step = size - overlap
        chunks: List[Chunk] = []

        if self.chunk_params.unit == ChunkUnit.tokens:
            tokens = self.token_enc.encode(text)
            total_token_len = len(tokens)

            for i in range(0, total_token_len, step):
                window = tokens[i: i + size]
                chunk_text = self.token_enc.decode(window)
                # Derive char_start by decoding all tokens before this window —
                # avoids text.find() which fails when decode doesn't round-trip exactly.
                char_start = len(self.token_enc.decode(tokens[:i]))

                chunks.append(self.make_chunk(
                    text=chunk_text,
                    source=source,
                    page_number=page_number,
                    index=start_index + len(chunks),
                    char_start=char_start,
                ))
                if i + size >= total_token_len:
                    break

        else:
            # Character implementation requires no transformation
            total_text_len = len(text)

            for i in range(0, total_text_len, step):
                chunk_text = text[i: i + size]
                # Assumes only text for now
                chunks.append(self.make_chunk(text=chunk_text,
                                              source=source, 
                                              page_number=page_number,
                                              index=start_index + len(chunks),
                                              char_start=i)
                                              )
                # Prevent empty iteration
                if i + size >= total_text_len:
                    break

        return chunks