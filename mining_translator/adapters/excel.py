"""Excel adapter for .xlsx files using openpyxl."""

import os
from .base import BaseAdapter, TextBlock


class ExcelAdapter(BaseAdapter):
    supported_extensions = [".xlsx", ".xlsm"]

    def extract_texts(self, filepath: str) -> list[TextBlock]:
        from openpyxl import load_workbook

        wb = load_workbook(filepath)
        blocks = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str) and cell.value.strip():
                        blocks.append(TextBlock(
                            id=f"{sheet_name}|{cell.coordinate}",
                            text=cell.value,
                            context=f"Sheet '{sheet_name}', cell {cell.coordinate}",
                            meta={"sheet": sheet_name, "coordinate": cell.coordinate},
                        ))

        wb.close()
        return blocks

    def write_translated(self, filepath: str, blocks: list[TextBlock], output_path: str):
        from openpyxl import load_workbook

        wb = load_workbook(filepath)

        # Build lookup: coordinate -> translated text
        lookup = {b.id: b.translated for b in blocks}

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    block_id = f"{sheet_name}|{cell.coordinate}"
                    if block_id in lookup:
                        cell.value = lookup[block_id]

        wb.save(output_path)
        wb.close()
