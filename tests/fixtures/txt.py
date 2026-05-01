# Standard Library
from pathlib import Path


def create_sample_txt(dest: Path) -> None:
    """Create a minimal plain-text fixture at dest.

    Structure mirrors sample.md/docx/pdf where possible:
    same section topics (Introduction, Data Overview, Conclusion)
    as plain prose with no markup.

    Args:
        dest: Destination path where the .txt file will be written.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "Sample Document\n"
        "\n"
        "Introduction\n"
        "\n"
        "This is the introduction paragraph.\n"
        "\n"
        "Data Overview\n"
        "\n"
        "This section covers data. Name: Alpha, Value: 1. Name: Beta, Value: 2.\n"
        "\n"
        "Conclusion\n"
        "\n"
        "Final remarks go here.\n",
        encoding="utf-8",
    )
