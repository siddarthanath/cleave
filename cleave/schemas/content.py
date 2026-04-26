# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from enum import Enum

# Third Party Library
from pydantic import BaseModel, Field

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ContentType(str, Enum):
    text  = "text"
    image = "image"
    table = "table"


class ContentBlock(BaseModel):
    type: ContentType = Field(description="Type of content: text, image, or table.")
    content: str = Field(
        description=(
            "The content payload. "
            "text  → raw string. "
            "image → base64-encoded bytes as string. "
            "table → markdown-formatted table string."
        ),
        min_length=1,
    )
    position: int = Field(description="0-based position of this block within the page.", ge=0)
