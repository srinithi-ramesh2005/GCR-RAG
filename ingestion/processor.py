"""
Process files with full layout awareness and relationship preservation.
"""

import os
import io
import sqlite3
from datetime import datetime
from typing import Dict, List
from googleapiclient.http import MediaIoBaseDownload

from .metadata_db import get_relationship_db
from .layout_parser import LayoutParser, parse_docx_with_layout
from .relationship_graph import RelationshipGraph
from .smart_chunker import SmartChunker

# Import from parsers folder
from parsers import (
    extract_pdf,
    extract_pptx,
    extract_docx,
    extract_tables_from_pdf_bytes,
    extract_tables_from_docx_bytes,
    table_to_text
)

# Initialize components
layout_parser = LayoutParser()
relationship_graph = RelationshipGraph()
relationship_db = get_relationship_db()
chunker = SmartChunker(chunk_size=500, overlap=50)

def get_course_files(classroom_service, course_id: str) -> list:
    """Get all file metadata from a Google Classroom course."""
    files = []
    try:
        materials = classroom_service.courses().courseWorkMaterials().list(
            courseId=course_id
        ).execute()
        
        items = materials.get('courseWorkMaterial', [])
        
        for item in items:
            for material in item.get('materials', []):
                if 'driveFile' in material:
                    file_info = material['driveFile']['driveFile']
                    files.append({
                        'id': file_info.get('id'),
                        'name': file_info.get('title', 'unknown'),
                        'modifiedTime': file_info.get('modifiedTime', ''),
                        'mimeType': file_info.get('mimeType', '')
                    })
        
        return files
    
    except Exception as e:
        print(f"  ❌ Error fetching files: {e}")
        return []

def process_file_with_layout(drive_service, file, course_id, course_name, save_to_disk=False):
    """
    Process a file with FULL layout awareness and relationship preservation.
    """
    file_id = file['id']
    file_name = file['name']
    
    print(f"\n  📄 Processing: {file_name}")
    print(f"     🔗 Building relationship graph...")
    
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        done = False
        
        print(f"    📥 Downloading...", end='')
        while done is False:
            status, done = downloader.next_chunk()
        print(f" ✅ Downloaded ({file_bytes.tell()} bytes)")
        
        file_path = None
        if save_to_disk:
            course_folder = f"downloads/{course_name.replace(' ', '_')}"
            os.makedirs(course_folder, exist_ok=True)
            file_path = os.path.join(course_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(file_bytes.getvalue())
            print(f"    💾 Saved to: {file_path}")
            file_bytes.seek(0)

        file_ext = file_name.split('.')[-1].lower()
        elements = []
        relationships = []
        document_metadata = {}
        hierarchy = {}
        
        if file_ext == 'pdf':
            print(f"    📄 Parsing PDF with layout awareness...")
            result = layout_parser.parse_pdf(file_bytes, file_id)
            elements = result['elements']
            relationships = result['relationships']
            document_metadata = result['document_metadata']
            hierarchy = result['hierarchy']
            
            print(f"    📊 Extracting tables...")
            file_bytes.seek(0)
            tables = extract_tables_from_pdf_bytes(file_bytes)
            for i, table in enumerate(tables):
                table_element = {
                    'element_id': f"elem_{file_id}_table_{i}",
                    'file_id': file_id,
                    'element_type': 'table',
                    'content': table_to_text(table),
                    'page_number': table.get('page', 0),
                    'section': 'Tables',
                    'subsection': '',
                    'heading_level': 0,
                    'bbox': [0, 0, 0, 0],
                    'position': 0,
                    'parent_element_id': None,
                    'doc_metadata': {
                        'table_data': table.get('html', ''),
                        'rows': table.get('rows', 0),
                        'columns': table.get('columns', 0)
                    }
                }
                elements.append(table_element)
                relationships.append({
                    'source': file_id,
                    'target': table_element['element_id'],
                    'type': 'PARENT_CHILD',
                    'strength': 1.0
                })
            file_bytes.seek(0)
            
        elif file_ext in ['docx', 'doc']:
            print(f"    📝 Parsing DOCX with layout awareness...")
            result = parse_docx_with_layout(file_bytes, file_id)
            elements = result['elements']
            relationships = result['relationships']
            document_metadata = result['document_metadata']
            hierarchy = result['hierarchy']
            
            print(f"    📊 Extracting tables...")
            file_bytes.seek(0)
            tables = extract_tables_from_docx_bytes(file_bytes)
            for i, table in enumerate(tables):
                table_element = {
                    'element_id': f"elem_{file_id}_table_{i}",
                    'file_id': file_id,
                    'element_type': 'table',
                    'content': table_to_text(table),
                    'page_number': 0,
                    'section': 'Tables',
                    'subsection': '',
                    'heading_level': 0,
                    'bbox': [0, 0, 0, 0],
                    'position': 0,
                    'parent_element_id': None,
                    'doc_metadata': {
                        'table_data': table.get('html', ''),
                        'rows': table.get('rows', 0),
                        'columns': table.get('columns', 0)
                    }
                }
                elements.append(table_element)
                relationships.append({
                    'source': file_id,
                    'target': table_element['element_id'],
                    'type': 'PARENT_CHILD',
                    'strength': 1.0
                })
            file_bytes.seek(0)
        elif file_ext in ['pptx', 'ppt']:
            print(f"    📊 Parsing PowerPoint...")
            text = extract_pptx(file_bytes)
            if text:
                elements.append({
                    'element_id': f"elem_{file_id}_0",
                    'file_id': file_id,
                    'element_type': 'document',
                    'content': text,
                    'page_number': 0,
                    'section': 'Presentation',
                    'subsection': '',
                    'heading_level': 0,
                    'bbox': [0, 0, 0, 0],
                    'position': 0,
                    'parent_element_id': None,
                    'doc_metadata': {}
                })
        
        else:
            print(f"    ⚠️ Skipping unsupported: {file_ext}")
            return None
        
        print(f"    💾 Saving {len(elements)} elements to database...")
        db = get_relationship_db()
        
        doc_metadata = {
            'file_id': file_id,
            'file_name': file_name,
            'course_id': course_id,
            'course_name': course_name,
            'file_type': file_ext,
            'modified_time': file.get('modifiedTime', ''),
            'indexed_time': datetime.now().isoformat(),
            'text_length': sum(len(e.get('content', '')) for e in elements),
            'status': 'processed',
            'element_count': len(elements),
            'relationship_count': len(relationships),
            'local_path': file_path if save_to_disk else None,
            'doc_metadata': document_metadata
        }
        db.add_document(file_id, doc_metadata)
        
        for elem in elements:
            db.add_element(elem)
        
        for rel in relationships:
            db.add_relationship(
                rel['source'],
                rel['target'],
                rel['type'],
                rel.get('strength', 1.0),
                rel.get('metadata', {})
            )
        
        print(f"    🔗 Building relationship graph...")
        relationship_graph.build_from_elements(elements, relationships)
        
        graph_path = f"graphs/{file_id}_graph.pkl"
        os.makedirs("graphs", exist_ok=True)
        relationship_graph.save(graph_path)
        print(f"    💾 Graph saved to: {graph_path}")
        
        # Step 8: Create chunks from elements
        print(f"    🔪 Creating chunks with relationships...")
        chunks = create_chunks_from_elements(elements, relationships, file_id, file_name)

        # ========== SAVE CHUNKS TO DATABASE ==========
        if chunks:
            print(f"    💾 Saving {len(chunks)} chunks to database...")
            db = get_relationship_db()
            saved_count = 0
            
            for chunk in chunks:
                try:
                    # Prepare chunk data for database
                    chunk_data = {
                        'file_id': file_id,
                        'text': chunk.get('text', ''),
                        'chunk_index': chunk.get('chunk_index', 0),
                        'chunk_length': chunk.get('chunk_length', 0),
                        'strategy': chunk.get('strategy', 'semantic'),
                        'section': chunk.get('section', ''),
                        'element_ids': chunk.get('element_ids', []),
                        'parent_chunk_id': chunk.get('parent_chunk_id', None),
                        'next_chunk_id': chunk.get('next_chunk_id', None),
                        'prev_chunk_id': chunk.get('prev_chunk_id', None)
                    }
                    
                    chunk_id = db.add_chunk(chunk_data)
                    if chunk_id > 0:
                        saved_count += 1
                except Exception as e:
                    print(f"      ❌ Error saving chunk: {e}")
    
            print(f"    ✅ Saved {saved_count}/{len(chunks)} chunks to database!")
    
            # Update document with chunk count
            conn = sqlite3.connect('metadata.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE documents 
                SET chunks_created = ? 
                WHERE file_id = ?
            ''', (saved_count, file_id))
            conn.commit()
            conn.close()
        else:
            print(f"    ⚠️ No chunks created!")
    except Exception as e:
        print(f"  ❌ Error processing {file_name}: {e}")
        return None

def create_chunks_from_elements(elements: List[Dict], relationships: List[Dict], 
                                file_id: str, file_name: str) -> List[Dict]:
    """
    Create chunks with FULL relationship preservation.
    """
    from .smart_chunker import SmartChunker
    chunker = SmartChunker(chunk_size=500, overlap=50)
    
    if not elements:
        print("    ⚠️ No elements to chunk!")
        return []
    
    # Get all text content from elements in order
    full_text = ""
    
    for elem in sorted(elements, key=lambda x: x.get('position', 0)):
        content = elem.get('content', '')
        if content:
            full_text += content + "\n\n"
    
    if not full_text.strip():
        print("    ⚠️ No text content found!")
        return []
    
    # Use SmartChunker to split text
    raw_chunks = chunker._chunk_by_semantic(full_text)
    
    chunks = []
    for idx, chunk_text in enumerate(raw_chunks):
        if not chunk_text.strip():
            continue
            
        chunk = {
            'file_id': file_id,
            'text': chunk_text.strip(),
            'chunk_index': idx,
            'chunk_length': len(chunk_text),
            'strategy': 'semantic',
            'section': elements[0].get('section', '') if elements else '',
            'element_ids': [],
            'parent_chunk_id': None,
            'next_chunk_id': idx + 1 if idx < len(raw_chunks) - 1 else None,
            'prev_chunk_id': idx - 1 if idx > 0 else None
        }
        chunks.append(chunk)
    
    print(f"    ✅ Created {len(chunks)} chunks")
    return chunks


def process_course(course_id, course_name, drive_service, classroom_service, save_to_disk=False):
    """Process all files in a course with full relationship preservation."""
    db = get_relationship_db()
    
    print(f"\n📁 Processing: {course_name}")
    print("-" * 50)
    
    drive_files = get_course_files(classroom_service, course_id)
    
    if not drive_files:
        print("  ⚠️ No files found")
        return {'new': 0, 'modified': 0, 'deleted': 0}
    
    print(f"  📄 Found {len(drive_files)} files in Drive")
    
    changes = db.get_changes(course_id, drive_files)
    
    print(f"\n  📊 Changes:")
    print(f"     🆕 New: {len(changes.get('new', []))}")
    print(f"     📝 Modified: {len(changes.get('modified', []))}")
    print(f"     📂 Unchanged: {len(changes.get('unchanged', []))}")
    print(f"     🗑️ Deleted: {len(changes.get('deleted', []))}")
    print("-" * 50)
    
    for file in changes.get('new', []):
        process_file_with_layout(drive_service, file, course_id, course_name, save_to_disk)
    
    for file in changes.get('modified', []):
        process_file_with_layout(drive_service, file, course_id, course_name, save_to_disk)
    
    return {
        'new': len(changes.get('new', [])),
        'modified': len(changes.get('modified', [])),
        'deleted': len(changes.get('deleted', []))
    }