"""Auto-select adapter based on file extension. Uses lazy imports."""

import os
from .base import BaseAdapter
from .text import TextAdapter


_BUILDERS: dict[str, callable] = {
    ".txt": lambda: TextAdapter(),
    ".md": lambda: TextAdapter(),
    ".csv": lambda: TextAdapter(),
    ".json": lambda: TextAdapter(),
    ".xml": lambda: TextAdapter(),
    ".html": lambda: TextAdapter(),
    ".htm": lambda: TextAdapter(),
}


def _register_excel():
    from .excel import ExcelAdapter
    for ext in ExcelAdapter.supported_extensions:
        _BUILDERS[ext] = lambda: ExcelAdapter()


def _register_word():
    from .word import WordAdapter
    for ext in WordAdapter.supported_extensions:
        _BUILDERS[ext] = lambda: WordAdapter()


def _register_ppt():
    from .ppt import PPTAdapter
    for ext in PPTAdapter.supported_extensions:
        _BUILDERS[ext] = lambda: PPTAdapter()


def _register_pdf():
    from .pdf import PDFAdapter
    for ext in PDFAdapter.supported_extensions:
        _BUILDERS[ext] = lambda: PDFAdapter()


def _try_register(register_fn, ext_key: str):
    """Try to register additional adapters. Silently skip if deps not installed."""
    try:
        register_fn()
    except ImportError:
        pass


def get_adapter(filepath: str) -> BaseAdapter:
    """Return the appropriate adapter for a file based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _BUILDERS:
        _try_register(_register_excel, ext)
        _try_register(_register_word, ext)
        _try_register(_register_ppt, ext)
        _try_register(_register_pdf, ext)

    if ext not in _BUILDERS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {sorted(_BUILDERS.keys())}")
    return _BUILDERS[ext]()


def supported_formats() -> list[str]:
    """Return list of all supported file extensions."""
    for fn in [_register_excel, _register_word, _register_ppt, _register_pdf]:
        _try_register(fn, "")
    return sorted(_BUILDERS.keys())
