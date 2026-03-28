# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Dict

# Third Party Library

# Private Library
from cleave.parsers.base import BaseParser
from cleave.utils.file import get_path_and_extension

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ParserFactory:
    
    _PARSER_REGISTRY : Dict[str, str] = {'.pdf': ...,
                                        '.docx': ...}

    @classmethod
    def create(cls, input_path: str) -> BaseParser:
        """This function dynamically creates a Parser object from the input path.

        Args:
            input_path (str): File path to local document or URL.
        Returns:
            BaseParser: Parser object.
        """        
        if input_path.startswith("http://") or input_path.startswith("https://"):
            # source = BaseParser._make_url_source(url=input_path)
            # return HtmlParser(source=source)
            raise NotImplementedError("Implemented once parsers are ready.")
        
        _, ext = get_path_and_extension(path=input_path)
        if ext not in cls._PARSER_REGISTRY:
            raise ValueError(f"Unsupported extension '{ext}'. Supported: {list(cls._PARSER_REGISTRY.keys())}")
        
        source = BaseParser._make_source(file_path=input_path)
        return cls._PARSER_REGISTRY[ext](source=source)
    