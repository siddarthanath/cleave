# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import List, Optional

# Third Party Library
from pydantic import BaseModel, Field, model_validator

# Private Library
from cleave.schemas.content import ContentBlock, ContentType
from cleave.schemas.source import Source
from cleave.schemas.tree import TreeNode

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class DocumentPage(BaseModel):
    page_number: int | None = Field(
        description="1-based page number. None for sources with no page concept (txt, url, docx).",
        ge=1,
        default=None,
    )
    blocks: List[ContentBlock] = Field(
        description="Ordered content blocks that make up this page.",
        min_length=0,
    )

    @property
    def text(self) -> str:
        return "\n".join(
            b.content
            for b in sorted(self.blocks, key=lambda b: b.position)
            if b.type == ContentType.text
        )

    @property
    def images(self) -> List[ContentBlock]:
        return [b for b in self.blocks if b.type == ContentType.image]

    @property
    def tables(self) -> List[ContentBlock]:
        return [b for b in self.blocks if b.type == ContentType.table]


class Document(BaseModel):
    source: Source = Field(description="Origin of this document.")
    pages: Optional[List[DocumentPage]] = Field(
        description="Ordered list of pages. Populated for flat documents.",
        default=None,
    )
    total_pages: Optional[int] = Field(
        description="Total page count. Populated for flat documents.",
        ge=1,
        default=None,
    )
    root: Optional[TreeNode] = Field(
        description="Root of the semantic tree. Populated for tree documents.",
        default=None,
    )
    parser_version: Optional[str] = Field(
        description="Version string of the parser that produced this document. Used for cache invalidation.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_structure(self) -> "Document":
        has_pages = self.pages is not None
        has_root = self.root is not None
        if not has_pages and not has_root:
            raise ValueError("Document must have either pages or root, not neither.")
        if has_pages and has_root:
            raise ValueError("Document must have either pages or root, not both.")
        if has_pages and len(self.pages) == 0:
            raise ValueError("pages must not be empty.")
        return self

    @property
    def full_text(self) -> str:
        if self.root:
            return self.root.get_full_text()
        return "\n".join(page.text for page in self.pages)

    @property
    def all_images(self) -> List[ContentBlock]:
        if self.root:
            return [
                ContentBlock(type=ContentType.image, content=n.content, position=i)
                for i, n in enumerate(self.root.get_nodes_by_type(ContentType.image))
                if n.content
            ]
        return [block for page in self.pages for block in page.images]

    @property
    def all_tables(self) -> List[ContentBlock]:
        if self.root:
            return [
                ContentBlock(type=ContentType.table, content=n.content, position=i)
                for i, n in enumerate(self.root.get_nodes_by_type(ContentType.table))
                if n.content
            ]
        return [block for page in self.pages for block in page.tables]

    def to_markdown(self) -> str:
        """Convert document to a flat Markdown string — works on both flat and tree documents.

        Flat path: joins page text blocks with double newlines.
        Tree path: delegates to TreeNode.to_markdown() which preserves heading levels,
                   tables, and image references.

        Returns:
            Markdown-formatted string representation of the full document.
        """
        if self.root:
            return self.root.to_markdown()
        return "\n\n---\n\n".join(page.text for page in self.pages if page.text)
