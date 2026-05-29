"""PDF adapter using pdfplumber for reading. Outputs translated text file."""

import os
from .base import BaseAdapter, TextBlock


class PDFAdapter(BaseAdapter):
    supported_extensions = [".pdf"]

    def extract_texts(self, filepath: str) -> list[TextBlock]:
        import pdfplumber

        blocks = []
        with pdfplumber.open(filepath) as pdf:
            for pi, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    blocks.append(TextBlock(
                        id=f"p{pi}",
                        text=text,
                        context=f"Page {pi+1}",
                        meta={"page": pi, "filename": os.path.basename(filepath)},
                    ))

        if not blocks:
            # Return empty block to avoid downstream issues
            return [TextBlock(id="p0", text="", meta={"filename": os.path.basename(filepath)})]

        return blocks

    def write_translated(self, filepath: str, blocks: list[TextBlock], output_path: str):
        """Write translated text as a .txt file (PDF write-back is impractical)."""
        filename = os.path.basename(filepath)
        parts = [f"# Translation of: {filename}\n"]

        for b in blocks:
            if b.meta.get("page") is not None:
                parts.append(f"\n--- Page {b.meta['page'] + 1} ---\n\n")
            parts.append(b.translated)
            parts.append("\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("".join(parts))
