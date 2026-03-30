# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List

# Third Party Library
import tiktoken
from abc import ABC, abstractmethod

# Private Library
from cleave.schemas import Chunk, ChunkParams, ChunkUnit, ContentType, Document, Source

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
    
    def make_chunk(self,
                   text: str,
                   source: Source,
                   page_number: int | None,
                   index: int,
                   char_start: int,
                   content_type: ContentType = ContentType.text) -> Chunk:
        """This function builds a Chunk of any content type. Routes to the correct protected method.
        
        Args:
            text (str): The text that defines the Chunk.
            source (Source): The Source where the Chunk sits in.
            page_number (int | None): The page number where the Chunk exists in the Document.
            index (int): The index within the page.
            char_start (int): Start character offset within the page text.
            content_type (ContentType): The type of the content. Defaults to text.
            
        Returns:
            Chunk: Chunk object.
        """
        if content_type == ContentType.text:
            return self._make_text_chunk(text, source, page_number, index, char_start)
        elif content_type == ContentType.table:
            return self._make_table_chunk(text, source, page_number, index, char_start)
        elif content_type == ContentType.image:
            return self._make_image_chunk(text, source, page_number, index, char_start)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
  
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
  
    def _make_text_chunk(self,
                         text: str,
                         source: Source,
                         page_number: int | None,
                         index: int,
                         char_start: int) -> Chunk:
        """This function builds a text Chunk with char_end derived from text length.
 
        Args:
            text (str): The text content.
            source (Source): Origin document.
            page_number (int | None): Page number within the document.
            index (int): Global chunk index across the document.
            char_start (int): Start character offset within the page text.
 
        Returns:
            Chunk: Fully populated text Chunk.
        """
        return Chunk(
            text=text,
            source=source,
            page_number=page_number,
            content_type=ContentType.text,
            index=index,
            token_count=self._count_tokens(text),
            char_start=char_start,
            char_end=char_start + len(text),
        )
 
    def _make_table_chunk(self,
                          text: str,
                          source: Source,
                          page_number: int | None,
                          index: int,
                          char_start: int) -> Chunk:
        """This function builds a table Chunk. Tables are never split — the full table is always one chunk.
 
        Args:
            text (str): The markdown-formatted table string.
            source (Source): Origin document.
            page_number (int | None): Page number within the document.
            index (int): Global chunk index across the document.
            char_start (int): Start character offset within the page text.
 
        Returns:
            Chunk: Fully populated table Chunk.
        """
        return Chunk(
            text=text,
            source=source,
            page_number=page_number,
            content_type=ContentType.table,
            index=index,
            token_count=self._count_tokens(text),
            char_start=char_start,
            char_end=char_start + len(text),
        )
 
    def _make_image_chunk(self,
                          text: str,
                          source: Source,
                          page_number: int | None,
                          index: int,
                          char_start: int) -> Chunk:
        """This function builds an image Chunk. text is the base64-encoded image bytes as string.
        token_count is 0 as images have no meaningful token count.
 
        Args:
            text (str): Base64-encoded image bytes as string.
            source (Source): Origin document.
            page_number (int | None): Page number within the document.
            index (int): Global chunk index across the document.
            char_start (int): Start character offset within the page content sequence.
 
        Returns:
            Chunk: Fully populated image Chunk.
        """
        return Chunk(
            text=text,
            source=source,
            page_number=page_number,
            content_type=ContentType.image,
            index=index,
            token_count=0,
            char_start=char_start,
            char_end=char_start + len(text),
        )
 
    def _count_tokens(self, text: str) -> int:
        """This function returns the token count for text using tiktoken cl100k_base.
        Used as metadata only — not used for splitting unless unit=tokens.
 
        Args:
            text (str): Text to count tokens on.
 
        Returns:
            int: Token count.
        """
        return len(self.token_enc.encode(text))