"""
Layout-aware document parsing with PyMuPDF.
Extracts headings, paragraphs, tables, images with positions.
"""

import io
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid

class LayoutParser:
    """
    Parse PDFs preserving layout, structure, and relationships.
    Uses PyMuPDF for fast, accurate parsing.
    """
    
    def __init__(self):
        self.element_counter = 0
    
    def parse_pdf(self, file_bytes: io.BytesIO, file_id: str) -> Dict:
        """
        Parse PDF with full layout preservation.
        
        Returns:
            Dict with:
            - elements: List of all parsed elements
            - relationships: List of relationship tuples
            - document_metadata: Document-level metadata
            - hierarchy: Hierarchical structure
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print("⚠️ PyMuPDF not installed. Install with: pip install pymupdf")
            return {'elements': [], 'relationships': [], 'document_metadata': {}}
        
        file_bytes.seek(0)
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        elements = []
        relationships = []
        
        doc_metadata = {
            'file_id': file_id,
            'page_count': len(doc),
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'creation_date': doc.metadata.get('creationDate', ''),
            'modification_date': doc.metadata.get('modDate', '')
        }
        
        current_section = "Introduction"
        current_subsection = ""
        heading_stack = []
        prev_element = None
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_blocks = page.get_text("dict")["blocks"]
            
            for block_idx, block in enumerate(text_blocks):
                if block["type"] == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span["text"].strip()
                            if not text:
                                continue
                            
                            heading_level = self._detect_heading_level(text, span)
                            is_heading = heading_level > 0
                            
                            if is_heading:
                                if heading_level == 1:
                                    current_section = text
                                    current_subsection = ""
                                    heading_stack = [text]
                                elif heading_level == 2:
                                    current_subsection = text
                                    heading_stack = [current_section, text]
                            
                            element_id = f"elem_{file_id}_{self.element_counter}"
                            self.element_counter += 1
                            
                            element = {
                                'element_id': element_id,
                                'file_id': file_id,
                                'element_type': 'heading' if is_heading else 'paragraph',
                                'content': text,
                                'page_number': page_num + 1,
                                'section': current_section,
                                'subsection': current_subsection if current_subsection else '',
                                'heading_level': heading_level if is_heading else 0,
                                'bbox': span.get("bbox", [0, 0, 0, 0]),
                                'position': block_idx,
                                'parent_element_id': None,
                                'doc_metadata': {
                                    'font_size': span.get("size", 0),
                                    'font_name': span.get("font", ""),
                                    'color': span.get("color", 0)
                                }
                            }
                            
                            if is_heading:
                                if heading_level == 1:
                                    element['parent_element_id'] = None
                                else:
                                    for e in reversed(elements):
                                        if e.get('heading_level', 0) == heading_level - 1:
                                            element['parent_element_id'] = e['element_id']
                                            break
                            else:
                                for e in reversed(elements):
                                    if e.get('heading_level', 0) > 0:
                                        element['parent_element_id'] = e['element_id']
                                        break
                            
                            elements.append(element)
                            
                            if element['parent_element_id']:
                                relationships.append({
                                    'source': element['parent_element_id'],
                                    'target': element_id,
                                    'type': 'PARENT_CHILD',
                                    'strength': 1.0
                                })
                            
                            if prev_element:
                                relationships.append({
                                    'source': prev_element['element_id'],
                                    'target': element_id,
                                    'type': 'NEIGHBOR',
                                    'strength': 0.8
                                })
                            
                            prev_element = element
        
        doc.close()
        
        return {
            'elements': elements,
            'relationships': relationships,
            'document_metadata': doc_metadata,
            'hierarchy': self._build_hierarchy(elements)
        }
    
    def _detect_heading_level(self, text: str, span: Dict) -> int:
        """Detect heading level based on text patterns and font size."""
        patterns = [
            (r'^[0-9]+\.[0-9]+\.[0-9]+', 3),
            (r'^[0-9]+\.[0-9]+', 2),
            (r'^[0-9]+\.', 1),
            (r'^Chapter [0-9]+', 1),
            (r'^Section [0-9]+', 1),
            (r'^[A-Z][A-Z\s]{2,}$', 1),
        ]
        
        for pattern, level in patterns:
            if re.match(pattern, text):
                return level
        
        font_size = span.get("size", 12)
        if font_size >= 18:
            return 1
        elif font_size >= 14:
            return 2
        elif font_size >= 12:
            return 3
        
        return 0
    
    def _build_hierarchy(self, elements: List[Dict]) -> Dict:
        """Build hierarchical structure from elements."""
        hierarchy = {'root': [], 'by_level': {}}
        for elem in elements:
            level = elem.get('heading_level', 0)
            if level not in hierarchy['by_level']:
                hierarchy['by_level'][level] = []
            hierarchy['by_level'][level].append(elem)
            if not elem.get('parent_element_id'):
                hierarchy['root'].append(elem)
        return hierarchy


def parse_docx_with_layout(file_bytes: io.BytesIO, file_id: str) -> Dict:
    """Parse DOCX with layout preservation."""
    try:
        from docx import Document
    except ImportError:
        print("⚠️ python-docx not installed")
        return {'elements': [], 'relationships': [], 'document_metadata': {}}
    
    file_bytes.seek(0)
    doc = Document(file_bytes)
    
    elements = []
    relationships = []
    current_section = "Introduction"
    element_counter = 0
    
    for idx, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
        
        style_name = paragraph.style.name.lower() if paragraph.style else ""
        heading_level = 0
        
        if 'heading' in style_name:
            try:
                heading_level = int(style_name.replace('heading', '').strip())
            except:
                heading_level = 1
        
        if heading_level == 0 and text.isupper() and len(text) < 100:
            heading_level = 1
        
        element_id = f"elem_{file_id}_{element_counter}"
        element_counter += 1
        
        element = {
            'element_id': element_id,
            'file_id': file_id,
            'element_type': 'heading' if heading_level > 0 else 'paragraph',
            'content': text,
            'page_number': 0,
            'section': current_section,
            'subsection': '',
            'heading_level': heading_level,
            'bbox': [0, 0, 0, 0],
            'position': idx,
            'parent_element_id': None,
            'doc_metadata': {
                'style': style_name,
                'is_bold': paragraph.runs[0].bold if paragraph.runs else False,
            }
        }
        
        if heading_level > 0 and heading_level == 1:
            current_section = text
        
        elements.append(element)
    
    prev_element = None
    for element in elements:
        if element['heading_level'] > 0:
            for e in reversed(elements[:elements.index(element)]):
                if e['heading_level'] == element['heading_level'] - 1:
                    element['parent_element_id'] = e['element_id']
                    relationships.append({
                        'source': e['element_id'],
                        'target': element['element_id'],
                        'type': 'PARENT_CHILD'
                    })
                    break
        else:
            for e in reversed(elements[:elements.index(element)]):
                if e['heading_level'] > 0:
                    element['parent_element_id'] = e['element_id']
                    relationships.append({
                        'source': e['element_id'],
                        'target': element['element_id'],
                        'type': 'PARENT_CHILD'
                    })
                    break
        
        if prev_element:
            relationships.append({
                'source': prev_element['element_id'],
                'target': element['element_id'],
                'type': 'NEIGHBOR'
            })
        prev_element = element
    
    return {
        'elements': elements,
        'relationships': relationships,
        'document_metadata': {
            'file_id': file_id,
            'paragraph_count': len(doc.paragraphs),
            'table_count': len(doc.tables)
        },
        'hierarchy': {'root': [e for e in elements if not e['parent_element_id']]}
    }