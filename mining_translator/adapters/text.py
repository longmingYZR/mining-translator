"""Plain text adapter for .txt, .md, .csv, .json files."""

import os
from .base import BaseAdapter, TextBlock


class TextAdapter(BaseAdapter):
    supported_extensions = [".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm"]

    def extract_texts(self, filepath: str) -> list[TextBlock]:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return []

        return [TextBlock(id="1", text=content, context=os.path.basename(filepath))]

    def write_translated(self, filepath: str, blocks: list[TextBlock], output_path: str):
        translated = blocks[0].translated if blocks else ""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated)
