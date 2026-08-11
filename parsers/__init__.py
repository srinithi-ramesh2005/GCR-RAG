# parsers/__init__.py
"""
Parser module for various document formats.
"""

from .pdf_parser import extract_text_from_bytes as extract_pdf
from .docx_parser import extract_text_from_bytes as extract_docx
from .pptx_parser import extract_text_from_bytes as extract_pptx

# Try to import from ingestion
try:
    from ingestion.table_extractor import (
        extract_tables_from_pdf_bytes,
        extract_tables_from_docx_bytes,
        table_to_text
    )
except ImportError:
    # Fallback for when running from different directories
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingestion.table_extractor import (
        extract_tables_from_pdf_bytes,
        extract_tables_from_docx_bytes,
        table_to_text
    )

__all__ = [
    'extract_pdf',
    'extract_docx',
    'extract_pptx',
    'extract_tables_from_pdf_bytes',
    'extract_tables_from_docx_bytes',
    'table_to_text'
]