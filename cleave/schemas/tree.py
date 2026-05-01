# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Any, Dict, List

# Third Party Library
from pydantic import BaseModel, Field

# Private Library
from cleave.schemas.content import ContentType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class TreeNode(BaseModel):
    """Recursive non-binary node representing a semantic unit of a document.

    metadata conventions:
      role        → "heading" | "paragraph" | "section" | "root"
      level       → int  (heading depth: 1=H1, 2=H2, …)
      page_number → int | None
      alt         → str  (image alt text)
    """

    content_type: ContentType = Field(description="Content type of this node.")
    content: str = Field(
        description=(
            "Node payload. "
            "text/heading → raw string. "
            "image → base64-encoded bytes as string. "
            "table → markdown-formatted table string."
        ),
        default="",
    )
    children: List["TreeNode"] = Field(
        description="Ordered child nodes (non-binary: 0…N children).",
        default_factory=list,
    )
    metadata: Dict[str, Any] = Field(
        description="Arbitrary node metadata (role, level, page_number, …).",
        default_factory=dict,
    )

    def get_full_text(self) -> str:
        """Recursively concatenate all text content — image nodes contribute nothing."""
        if self.content_type == ContentType.image:
            return ""
        parts = [self.content] if self.content else []
        for child in self.children:
            child_text = child.get_full_text()
            if child_text:
                parts.append(child_text)
        return "\n".join(parts)

    def get_nodes_by_type(self, content_type: "ContentType") -> List["TreeNode"]:
        """DFS collector returning all nodes (self + descendants) matching content_type.

        Args:
            content_type: The ContentType to filter by.

        Returns:
            List of matching TreeNode instances in DFS order.
        """
        results: List["TreeNode"] = []
        if self.content_type == content_type:
            results.append(self)
        for child in self.children:
            results.extend(child.get_nodes_by_type(content_type))
        return results

    def to_markdown(self, depth: int = 0) -> str:
        """Convert this node and all descendants to a Markdown string.

        Heading nodes use metadata['level'] (falling back to depth) for # prefix depth.
        Image nodes render as a Markdown image reference.
        Table nodes are emitted verbatim (already Markdown-formatted).

        Args:
            depth: Current recursion depth, used as fallback heading level.

        Returns:
            Markdown-formatted string representation of this subtree.
        """
        parts: List[str] = []

        if self.content_type == ContentType.image:
            alt = self.metadata.get("alt", "image")
            src = self.metadata.get("src", "")
            parts.append(f"![{alt}]({src})")
        elif self.content_type == ContentType.table:
            if self.content:
                parts.append(self.content)
        else:
            role = self.metadata.get("role", "paragraph")
            level = self.metadata.get("level", depth)
            if role == "heading" and self.content:
                prefix = "#" * max(1, min(int(level), 6))
                parts.append(f"{prefix} {self.content}")
            elif self.content:
                parts.append(self.content)

        for child in self.children:
            child_md = child.to_markdown(depth + 1)
            if child_md:
                parts.append(child_md)

        return "\n\n".join(p for p in parts if p)


TreeNode.model_rebuild()
