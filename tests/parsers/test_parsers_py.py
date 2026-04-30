# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# Third Party Library
import pytest

# Private Library
from cleave.parsers.code.py import PythonParser
from cleave.parsers.factory import ParserFactory
from cleave.schemas import ContentType, Document, SourceType

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class TestPythonParserFlat:

    def test_returns_document(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        assert isinstance(doc, Document)

    def test_has_one_page(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        assert doc.pages is not None
        assert len(doc.pages) == 1

    def test_page_number_is_none(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        assert doc.pages[0].page_number is None

    def test_docstring_block_is_text_definitions_are_code(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        blocks = doc.pages[0].blocks
        assert blocks[0].type == ContentType.text   # module docstring = prose
        for block in blocks[1:]:
            assert block.type == ContentType.code   # definitions = source code

    def test_module_docstring_is_first_block(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        first = doc.pages[0].blocks[0]
        assert "Sample Python module" in first.content

    def test_blocks_include_top_level_definitions(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        contents = [b.content for b in doc.pages[0].blocks]
        combined = "\n".join(contents)
        assert "def greet" in combined
        assert "class DataProcessor" in combined
        assert "async def fetch_data" in combined

    def test_block_positions_are_sequential(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        positions = [b.position for b in doc.pages[0].blocks]
        assert positions == list(range(len(positions)))

    def test_source_type_is_python(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        assert doc.source.source_type == SourceType.python

    def test_function_block_contains_body(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        contents = [b.content for b in doc.pages[0].blocks]
        greet_block = next(c for c in contents if "def greet" in c)
        assert 'return f"Hello' in greet_block

    def test_class_block_does_not_include_methods_separately(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="flat").parse()
        # In flat mode there should be exactly one block containing class DataProcessor
        class_blocks = [b for b in doc.pages[0].blocks if "class DataProcessor" in b.content]
        assert len(class_blocks) == 1

    def test_invalid_mode_raises(self, sample_py_path: Path) -> None:
        with pytest.raises(ValueError):
            PythonParser(str(sample_py_path), mode="bad")


class TestPythonParserTree:

    def test_returns_document(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        assert isinstance(doc, Document)

    def test_has_root_no_pages(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        assert doc.root is not None
        assert doc.pages is None

    def test_root_role_is_module(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        assert doc.root.metadata["role"] == "module"

    def test_root_name_matches_filename(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        assert doc.root.metadata["name"] == "sample.py"

    def test_root_content_is_module_docstring(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        assert "Sample Python module" in doc.root.content

    def test_root_children_include_class_and_functions(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        roles = {child.metadata["role"] for child in doc.root.children}
        assert "class" in roles
        assert "function" in roles

    def test_class_node_metadata(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        class_node = next(c for c in doc.root.children if c.metadata.get("role") == "class")
        assert class_node.metadata["name"] == "DataProcessor"
        assert "lineno" in class_node.metadata

    def test_class_node_has_method_children(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        class_node = next(c for c in doc.root.children if c.metadata.get("role") == "class")
        method_names = {m.metadata["name"] for m in class_node.children}
        assert "__init__" in method_names
        assert "total" in method_names
        assert "average" in method_names

    def test_method_role(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        class_node = next(c for c in doc.root.children if c.metadata.get("role") == "class")
        for method in class_node.children:
            assert method.metadata["role"] == "method"

    def test_function_node_role(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        func_nodes = [c for c in doc.root.children if c.metadata.get("role") == "function"]
        names = {n.metadata["name"] for n in func_nodes}
        assert "greet" in names
        assert "fetch_data" in names

    def test_function_node_content_is_source(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        greet = next(c for c in doc.root.children if c.metadata.get("name") == "greet")
        assert "def greet" in greet.content
        assert 'return f"Hello' in greet.content

    def test_class_node_docstring_in_metadata(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        class_node = next(c for c in doc.root.children if c.metadata.get("role") == "class")
        assert "Process and transform" in class_node.metadata["docstring"]

    def test_class_node_content_is_full_source(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        class_node = next(c for c in doc.root.children if c.metadata.get("role") == "class")
        assert "class DataProcessor" in class_node.content

    def test_get_full_text_traverses_hierarchy(self, sample_py_path: Path) -> None:
        doc = PythonParser(str(sample_py_path), mode="tree").parse()
        full = doc.root.get_full_text()
        assert "Sample Python module" in full
        assert "def greet" in full
        assert "class DataProcessor" in full or "DataProcessor" in full


class TestPythonParserFactory:

    def test_factory_creates_python_parser(self, sample_py_path: Path) -> None:
        parser = ParserFactory.create(str(sample_py_path), mode="flat")
        assert isinstance(parser, PythonParser)

    def test_factory_tree_mode(self, sample_py_path: Path) -> None:
        doc = ParserFactory.create(str(sample_py_path), mode="tree").parse()
        assert doc.root is not None
