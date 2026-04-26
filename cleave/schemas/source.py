# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from enum import Enum
from typing import Optional

# Third Party Library
from pydantic import BaseModel, Field

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class SourceType(str, Enum):
    pdf      = "pdf"
    docx     = "docx"
    pptx     = "pptx"
    html     = "html"
    markdown = "markdown"
    txt      = "txt"
    url      = "url"


class Source(BaseModel):
    source_type: SourceType = Field(description="File format or source type.")
    name: str = Field(description="Human-readable label e.g. filename or domain.", min_length=1)
    location: str = Field(description="Absolute filepath or full URL.", min_length=1)
    file_hash: Optional[str] = Field(
        description="SHA-256 hex digest of the raw file bytes. Used to detect re-uploads of identical files.",
        default=None,
    )
