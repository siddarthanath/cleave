# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import textwrap
from pathlib import Path
from typing import List

# Third Party Library
import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

# Private Library
from cleave.parsers.base import BaseModeParser
from cleave.schemas import ContentBlock, ContentType, Document, DocumentPage, TreeNode

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_DEF_TYPES = {"function_definition", "class_definition"}
_DECORATED = "decorated_definition"


class PythonParser(BaseModeParser):
    """Parser for Python source files (.py) using TreeSitter.

    Flat mode: one DocumentPage, one ContentBlock per top-level definition
    (function or class), preceded by a module-docstring block when present.

    Tree mode: TreeNode hierarchy mirroring the module structure —
    module root → class/function nodes → method nodes.
    """

    def __init__(self, file_path: str, mode: str = "flat") -> None:
        super().__init__(file_path=file_path, mode=mode)
        raw = Path(self._source.location).read_bytes()
        self._source_bytes = raw
        self._source_text = raw.decode("utf-8")
        self._ts_tree = _PARSER.parse(raw)

    # ╔════════════════════════════════════════════════════════════════════════════════════╗
    # ║                                    FLAT PATH                                       ║
    # ║                        (Sequential Definition Extraction)                          ║
    # ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_flat(self) -> Document:
        """Extract top-level definitions as sequential ContentBlocks.

        Returns:
            Document with one DocumentPage containing one ContentBlock per
            top-level class or function, preceded by a module-docstring block
            if the module has one.
        """
        blocks = self._collect_blocks()
        page = DocumentPage(page_number=None, blocks=blocks)
        return Document(source=self._source, pages=[page], total_pages=1)

    def _collect_blocks(self) -> List[ContentBlock]:
        """Build ordered ContentBlocks from top-level AST nodes.

        Returns:
            List of ContentBlock in source order.
        """
        blocks: List[ContentBlock] = []
        position = 0

        docstring = self._get_module_docstring()
        if docstring:
            # Module docstring is prose, not executable code
            blocks.append(ContentBlock(type=ContentType.text, content=docstring, position=position))
            position += 1

        root = self._ts_tree.root_node
        for child in root.named_children:
            node = self._unwrap_decorated(child)
            if node.type in _DEF_TYPES:
                text = self._node_text(node)
                # Source code blocks are tagged `code` so stores/retrievers can
                # distinguish them from prose text blocks
                blocks.append(ContentBlock(type=ContentType.code, content=text, position=position))
                position += 1

        return blocks

    # ╔════════════════════════════════════════════════════════════════════════════════════╗
    # ║                                    TREE PATH                                       ║
    # ║                        (Hierarchical Module/Class/Function)                        ║
    # ╚════════════════════════════════════════════════════════════════════════════════════╝

    def _parse_tree(self) -> Document:
        """Build a TreeNode hierarchy reflecting module → class → method nesting.

        Returns:
            Document with root TreeNode representing the module.
        """
        root = self._build_module_node()
        return Document(source=self._source, root=root)

    def _build_module_node(self) -> TreeNode:
        """Create the root module TreeNode with class/function children.

        Returns:
            Root TreeNode for the module.
        """
        # Module root holds the docstring as prose, not source code
        root = TreeNode(
            content_type=ContentType.text,
            content=self._get_module_docstring(),
            metadata={"role": "module", "name": self._source.name},
        )

        for child in self._ts_tree.root_node.named_children:
            node = self._unwrap_decorated(child)
            if node.type == "class_definition":
                root.children.append(self._build_class_node(node))
            elif node.type == "function_definition":
                root.children.append(self._build_function_node(node, role="function"))

        return root

    def _build_class_node(self, node: Node) -> TreeNode:
        """Create a TreeNode for a class with method children.

        Args:
            node: TreeSitter ClassDef node.

        Returns:
            TreeNode for the class.
        """
        name = self._field_text(node, "name")
        # content = full source (consistent with function nodes — what gets embedded);
        # docstring preserved separately in metadata for display/filtering use
        class_node = TreeNode(
            content_type=ContentType.code,
            content=self._node_text(node),
            metadata={
                "role": "class",
                "name": name,
                "lineno": node.start_point[0] + 1,
                "docstring": self._get_docstring(node),
            },
        )

        body = node.child_by_field_name("body")
        if body:
            for child in body.named_children:
                inner = self._unwrap_decorated(child)
                if inner.type == "function_definition":
                    class_node.children.append(self._build_function_node(inner, role="method"))

        return class_node

    def _build_function_node(self, node: Node, role: str) -> TreeNode:
        """Create a TreeNode for a function or method.

        Args:
            node: TreeSitter FunctionDef node.
            role: "function" for module-level definitions, "method" for class members.

        Returns:
            TreeNode for the function.
        """
        name = self._field_text(node, "name")
        return TreeNode(
            content_type=ContentType.code,
            content=self._node_text(node),
            metadata={
                "role": role,
                "name": name,
                "lineno": node.start_point[0] + 1,
            },
        )

    # Helpers

    def _node_text(self, node: Node) -> str:
        """Extract and dedent source text for a TreeSitter node.

        Args:
            node: Any TreeSitter node with start/end byte offsets.

        Returns:
            Dedented source code string.
        """
        raw = self._source_bytes[node.start_byte:node.end_byte].decode("utf-8")
        return textwrap.dedent(raw)

    def _field_text(self, node: Node, field: str) -> str:
        """Return source text for a named field of a node.

        Args:
            node: Parent TreeSitter node.
            field: Field name (e.g. "name").

        Returns:
            Text of the field node, or empty string if not found.
        """
        field_node = node.child_by_field_name(field)
        return self._node_text(field_node) if field_node else ""

    def _get_module_docstring(self) -> str:
        """Extract the module-level docstring from the root node.

        Returns:
            Docstring text stripped of surrounding quotes, or empty string.
        """
        for child in self._ts_tree.root_node.named_children:
            if child.type == "expression_statement":
                for subchild in child.named_children:
                    if subchild.type == "string":
                        return self._strip_quotes(self._node_text(subchild))
            break
        return ""

    def _get_docstring(self, node: Node) -> str:
        """Extract the docstring from a function or class body.

        Args:
            node: TreeSitter function_definition or class_definition node.

        Returns:
            Docstring text stripped of surrounding quotes, or empty string.
        """
        body = node.child_by_field_name("body")
        if body is None:
            return ""
        for child in body.named_children:
            if child.type == "expression_statement":
                for subchild in child.named_children:
                    if subchild.type == "string":
                        return self._strip_quotes(self._node_text(subchild))
            break
        return ""

    def _strip_quotes(self, raw: str) -> str:
        """Remove surrounding quotes from a string literal node's text.

        Args:
            raw: Raw string literal including quote delimiters.

        Returns:
            Unquoted, stripped content.
        """
        for delim in ('"""', "'''", '"', "'"):
            if raw.startswith(delim) and raw.endswith(delim) and len(raw) >= 2 * len(delim):
                return raw[len(delim):-len(delim)].strip()
        return raw

    def _unwrap_decorated(self, node: Node) -> Node:
        """Return the inner definition node, unwrapping decorated_definition if needed.

        Args:
            node: Any TreeSitter node.

        Returns:
            Inner function_definition or class_definition, or the node itself.
        """
        if node.type == _DECORATED:
            inner = node.child_by_field_name("definition")
            return inner if inner else node
        return node
