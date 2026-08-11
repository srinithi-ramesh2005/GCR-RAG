"""
Extract tables from PDF and DOCX files.
"""

import io
from typing import List, Dict

def extract_tables_from_pdf_bytes(file_bytes: io.BytesIO) -> List[Dict]:
    """Extract tables from PDF bytes."""
    try:
        import pandas as pd
        import tabula
    except ImportError:
        print("⚠️ tabula-py not installed. Install with: pip install tabula-py")
        return []
    
    file_bytes.seek(0)
    try:
        tables = tabula.read_pdf(file_bytes, pages='all', multiple_tables=True)
        result = []
        for i, table in enumerate(tables):
            if not table.empty:
                result.append({
                    'page': 0,
                    'rows': len(table),
                    'columns': len(table.columns),
                    'html': table.to_html(),
                    'data': table.to_dict()
                })
        return result
    except Exception as e:
        print(f"  ⚠️ Table extraction error: {e}")
        return []

def extract_tables_from_docx_bytes(file_bytes: io.BytesIO) -> List[Dict]:
    """Extract tables from DOCX bytes."""
    try:
        from docx import Document
    except ImportError:
        return []
    
    file_bytes.seek(0)
    doc = Document(file_bytes)
    
    tables = []
    for table in doc.tables:
        data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            data.append(row_data)
        
        tables.append({
            'rows': len(data),
            'columns': len(data[0]) if data else 0,
            'html': _table_to_html(data),
            'data': data
        })
    
    return tables

def _table_to_html(data: List[List[str]]) -> str:
    """Convert table data to HTML."""
    html = "<table>"
    for row in data:
        html += "<tr>"
        for cell in row:
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def table_to_text(table: Dict) -> str:
    """Convert table to readable text."""
    data = table.get('data', [])
    if not data:
        return ""
    
    lines = []
    for row in data:
        if isinstance(row, dict):
            row_values = list(row.values())
        else:
            row_values = row
        lines.append(" | ".join(str(v) for v in row_values))
    
    return "\n".join(lines)