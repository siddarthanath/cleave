# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import re
from typing import List

# Third Party Library

# Private Library
from cleave.chunker.base import BaseChunker
from cleave.schemas import Chunk, ChunkParams, ChunkerType, Document, Source

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# TODO: Implement ContentType into the chunkers.

class SentenceChunker(BaseChunker):

    _CHUNKER_TYPE = ChunkerType.sentence

    def __init__(self, chunk_params: ChunkParams) -> None:
        super().__init__(chunk_params)
        self._separaters = ['.', '!', '?']

    def chunk(self, document: Document) -> List[Chunk]:
        """This function splits every page in the document into sentence chunks.
 
        Args:
            document (Document): Parsed document.
 
        Returns:
            List[Chunk]: All chunks across all pages in document order.
        """
        chunks: List[Chunk] = []
        global_index = 0
        spare_text = None

        for page in document.pages:
            page_text = page.text
            # Add remaining text onto the next page and treat as a full new page
            if spare_text is not None:
                page_text = spare_text + page_text
            # Reset spare text to avoid carry over old text
            spare_text = None
            # Check the most recent punctuation stopper
            match = re.search(r"[.!?](?!.*[.!?])", page_text)
            if match:
                # Hold the spare text to join onto next page if mid sentence
                punc_index = match.start()
                if punc_index < len(page_text) - 1:
                    spare_text = page_text[punc_index:]
                # Take the page text up to the index
                page_text = page_text[:punc_index]

            if not page_text.strip():
                continue

            page_chunks = self._chunk_text(text=page_text,
                                           page_number=page.page_number,
                                           source=document.source,
                                           start_index=global_index)
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
        # Find punctuation indexes to accumulate on
        punctuation_matches = list(re.finditer(r"[.!?]", text))
        
        char_start = 0
        segment_start = 0
        current_text = ""
        
        for pm in punctuation_matches:
            end = pm.end()
            # Accumulate characters until character length is larger than chunk size and commit
            current_text += text[segment_start:end]
            # To not double count the overlap
            segment_start = end
            if self._measure(current_text) >= size:
                chunks.append(self.make_chunk(text=current_text,
                                              source=source, 
                                              page_number=page_number,
                                              index=start_index + len(chunks),
                                              char_start=char_start)
                                              )
                # Update next character start with where punctuation ends and overlap
                char_start = end - overlap
                # Start again by including the overlap
                current_text = current_text[-overlap:]
        
        # Add final chunk if still available
        if current_text.strip():
            chunks.append(self.make_chunk(text=current_text,
                                          source=source, 
                                          page_number=page_number,
                                          index=start_index + len(chunks),
                                          char_start=char_start)
                                          )

        return chunks