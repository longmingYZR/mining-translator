"""Base adapter class and TextBlock data structure."""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class TextBlock:
    """A unit of translatable text extracted from a document."""
    id: str
    text: str
    context: str = ""
    meta: dict = field(default_factory=dict)
    translated: str = ""


class BaseAdapter(ABC):
    """Abstract base for file format adapters.

    Each adapter handles one file format: extract text blocks -> translate -> write back.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this adapter handles (e.g., ['.txt', '.md'])."""
        ...

    @abstractmethod
    def extract_texts(self, filepath: str) -> list[TextBlock]:
        """Extract all translatable text blocks from a file."""
        ...

    @abstractmethod
    def write_translated(self, filepath: str, blocks: list[TextBlock], output_path: str):
        """Write translated text blocks back to a new file, preserving format."""
        ...

    def needs_translation(self, block: TextBlock) -> bool:
        """Check if a text block contains Chinese characters and needs translation."""
        return any('一' <= ch <= '鿿' for ch in block.text)
