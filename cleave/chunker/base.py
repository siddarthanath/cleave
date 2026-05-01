# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library
import tiktoken
from abc import ABC, abstractmethod

# Private Library
from cleave.schemas import Chunk, ChunkParams, ChunkUnit, ContentType, Document, DocumentPage, Source

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

class BaseChunker(ABC):

    def __init__(self, chunk_params: ChunkParams) -> None:
        self.chunk_params = chunk_params
        # TODO: Make chunk encoder in ChunkParams?
        self.token_enc = tiktoken.get_encoding('cl100k_base')

    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """This function applies the splitting strategy.
        Must return chunks in document order (index 0, 1, 2...).

        Args:
            document (Document): Document object.

        Returns:
            List[Chunk]: A list of structured chunks.
        """
        raise NotImplementedError("Subclasses must implement this method!")
    
    def make_chunk(
        self,
        text: str,
        source: Source,
        page_number: int | None,
        index: int,
        char_start: int,
        content_type: ContentType = ContentType.text,
    ) -> Chunk:
        """Build a Chunk for any content type.

        token_count is 0 for images (base64 data has no meaningful token count).

        Args:
            text (str): The chunk payload.
            source (Source): Origin document source.
            page_number (int | None): Page number within the document.
            index (int): Global chunk index across the document.
            char_start (int): Start character offset within the page text.
            content_type (ContentType): Content type. Defaults to text.

        Returns:
            Chunk: Fully populated Chunk.
        """
        return Chunk(
            text=text,
            source=source,
            page_number=page_number,
            content_type=content_type,
            index=index,
            token_count=0 if content_type == ContentType.image else self._count_tokens(text),
            char_start=char_start,
            char_end=char_start + len(text),
            metadata=self.chunk_params.metadata,
        )

    def _chunk_text(
        self,
        text: str,
        page_number: int | None,
        source: Source,
        start_index: int,
    ) -> List[Chunk]:
        """Split a plain text string into chunks using this chunker's strategy.

        Flat-page chunkers (FixedChunker, SentenceChunker) override this.
        RecursiveChunker bypasses _chunk_page entirely and does not use this method.

        Not marked @abstractmethod intentionally — RecursiveChunker is a valid
        subclass that never calls this method. Any subclass that does use _chunk_page
        must override this or it will raise at runtime.

        Args:
            text (str): Text to split.
            page_number (int | None): Page number for chunk metadata.
            source (Source): Origin source for chunk metadata.
            start_index (int): Global chunk index offset.

        Returns:
            List[Chunk]: Ordered chunks derived from text.
        """
        raise NotImplementedError("Subclasses must implement this method!")

    
    def _chunk_page(
        self,
        page: DocumentPage,
        source: Source,
        start_index: int,
    ) -> List[Chunk]:
        """Dispatch a page's blocks by content type.

        Text blocks are accumulated in position order and passed to _chunk_text.
        A table or image block flushes any pending text first, then is emitted as a
        single chunk. This preserves the natural block ordering in the output.

        Args:
            page (DocumentPage): Page whose blocks to process.
            source (Source): Origin document source.
            start_index (int): Global chunk index offset for this page.

        Returns:
            List[Chunk]: Ordered chunks for this page.
        """
        chunks: List[Chunk] = []
        pending: List[str] = []
        char_offset: int = 0

        for block in sorted(page.blocks, key=lambda b: b.position):
            if block.type == ContentType.text:
                if block.content.strip():
                    pending.append(block.content)
                char_offset += len(block.content)
            else:
                if pending:
                    text_chunks = self._chunk_text(
                        text="\n".join(pending),
                        page_number=page.page_number,
                        source=source,
                        start_index=start_index + len(chunks),
                    )
                    chunks.extend(text_chunks)
                    pending = []
                if block.content.strip():
                    chunks.append(
                        self.make_chunk(
                            text=block.content,
                            source=source,
                            page_number=page.page_number,
                            index=start_index + len(chunks),
                            char_start=char_offset,
                            content_type=block.type,
                        )
                    )
                char_offset += len(block.content)

        if pending:
            text_chunks = self._chunk_text(
                text="\n".join(pending),
                page_number=page.page_number,
                source=source,
                start_index=start_index + len(chunks),
            )
            chunks.extend(text_chunks)

        return chunks

    def _measure(self, text: str) -> int:
        """This functions returns the size of text in the unit defined by chunk_params.unit.
        Used by all chunkers to measure chunk size consistently.
 
        Args:
            text (str): Text to measure.
 
        Returns:
            int: Size in characters or tokens depending on chunk_params.unit.
        """
        if self.chunk_params.unit == ChunkUnit.tokens:
            return self._count_tokens(text)
        return len(text)

    def _count_tokens(self, text: str) -> int:
        """This function returns the token count for text using tiktoken cl100k_base.
        Used as metadata only — not used for splitting unless unit=tokens.
 
        Args:
            text (str): Text to count tokens on.
 
        Returns:
            int: Token count.
        """
        return len(self.token_enc.encode(text))