# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from pathlib import Path

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_SAMPLE_CODE = '''\
"""Sample Python module for testing the PythonParser."""

import os
from typing import List


def greet(name: str) -> str:
    """Return a personalised greeting string.

    Args:
        name: The name to greet.

    Returns:
        Formatted greeting.
    """
    return f"Hello, {name}!"


class DataProcessor:
    """Process and transform collections of integers."""

    def __init__(self, data: List[int]) -> None:
        """Initialise with a list of integers.

        Args:
            data: Input data to process.
        """
        self.data = data

    def total(self) -> int:
        """Return the sum of all data values.

        Returns:
            Sum of all integers.
        """
        return sum(self.data)

    def average(self) -> float:
        """Return the mean value of the data.

        Returns:
            Mean as a float.
        """
        return sum(self.data) / len(self.data)


async def fetch_data(url: str) -> str:
    """Simulate async data fetching.

    Args:
        url: The endpoint URL.

    Returns:
        Placeholder response string.
    """
    return f"data from {url}"
'''


def create_sample_py(dest: Path) -> None:
    """Write a Python source fixture to *dest*.

    Args:
        dest: Destination path for the generated .py file.
    """
    dest.write_text(_SAMPLE_CODE, encoding="utf-8")
