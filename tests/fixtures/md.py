# Standard Library
from pathlib import Path

# Private Library
from tests.fixtures._image import minimal_png


def create_sample_md(dest: Path) -> None:
    """Create a minimal structured Markdown file at *dest*.

    Structure mirrors sample.pdf and sample.docx:
      H1 "Sample Document", H2 "Introduction" / "Data Overview" / "Conclusion",
      one standalone image and one GFM table under Data Overview.

    Also writes sample_image.png alongside dest so the MarkdownParser can
    resolve the relative path and base64-encode the image content.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    image_name = "sample_image.png"
    (dest.parent / image_name).write_bytes(minimal_png())

    dest.write_text(f"""\
# Sample Document

## Introduction

This is the introduction paragraph.

## Data Overview

This section covers data.

![Sample Image]({image_name})

| Name | Value |
| --- | --- |
| Alpha | 1 |
| Beta | 2 |

## Conclusion

Final remarks go here.
""", encoding="utf-8")
