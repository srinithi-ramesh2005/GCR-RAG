"""
Metadata database with full relationship support.
Now tracks parent-child, neighbor, and hierarchical relationships.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class RelationshipDB:
    """Enhanced database with relationship tracking."""
    
    def __init__(self, db_path="metadata.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """Initialize all tables with relationship support."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Documents table (existing, enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                file_id TEXT PRIMARY KEY,
                file_name TEXT,
                course_id TEXT,
                course_name TEXT,
                file_type TEXT,
                modified_time TEXT,
                indexed_time TEXT,
                text_length INTEGER,
                status TEXT,
                local_path TEXT,
                embedding_status TEXT DEFAULT 'pending',
                parent_file_id TEXT,
                hierarchy_level INTEGER DEFAULT 0,
                chunks_created INTEGER DEFAULT 0,
                doc_metadata TEXT
            )
        ''')
        
        # 2. Elements table (NEW - for paragraphs, headings, tables, images)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elements (
                element_id TEXT PRIMARY KEY,
                file_id TEXT,
                element_type TEXT,
                content TEXT,
                page_number INTEGER,
                section TEXT,
                subsection TEXT,
                heading_level INTEGER,
                bbox TEXT,
                position INTEGER,
                parent_element_id TEXT,
                doc_metadata TEXT,
                FOREIGN KEY (file_id) REFERENCES documents(file_id),
                FOREIGN KEY (parent_element_id) REFERENCES elements(element_id)
            )
        ''')
        
        # 3. Relationships table (NEW - explicit relationship tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                target_id TEXT,
                relationship_type TEXT,
                strength REAL DEFAULT 1.0,
                metadata TEXT,
                FOREIGN KEY (source_id) REFERENCES elements(element_id),
                FOREIGN KEY (target_id) REFERENCES elements(element_id)
            )
        ''')
        
        # 4. Chunks table (enhanced with relationships)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                text TEXT,
                chunk_index INTEGER,
                chunk_length INTEGER,
                strategy TEXT,
                section TEXT,
                element_ids TEXT,
                parent_chunk_id INTEGER,
                next_chunk_id INTEGER,
                prev_chunk_id INTEGER,
                embedding BLOB,
                FOREIGN KEY (file_id) REFERENCES documents(file_id),
                FOREIGN KEY (parent_chunk_id) REFERENCES chunks(chunk_id)
            )
        ''')
        
        # 5. Create indexes for fast relationship queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_elements_file ON elements(file_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_elements_parent ON elements(parent_element_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_parent ON chunks(parent_chunk_id)')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized with relationship support")
    
    def add_document(self, file_id: str, metadata: Dict):
        """Add or update document metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO documents (
                file_id, file_name, course_id, course_name, file_type,
                modified_time, indexed_time, text_length, status, local_path,
                parent_file_id, hierarchy_level, doc_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_id,
            metadata.get('file_name', ''),
            metadata.get('course_id', ''),
            metadata.get('course_name', ''),
            metadata.get('file_type', ''),
            metadata.get('modified_time', ''),
            metadata.get('indexed_time', datetime.now().isoformat()),
            metadata.get('text_length', 0),
            metadata.get('status', 'processed'),
            metadata.get('local_path', ''),
            metadata.get('parent_file_id', ''),
            metadata.get('hierarchy_level', 0),
            json.dumps(metadata.get('doc_metadata', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def add_element(self, element_data: Dict) -> str:
        """Add a document element (heading, paragraph, table, image)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        element_id = element_data.get('element_id')
        if not element_id:
            element_id = f"elem_{element_data.get('file_id', '')}_{int(datetime.now().timestamp() * 1000)}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO elements (
                element_id, file_id, element_type, content, page_number,
                section, subsection, heading_level, bbox, position,
                parent_element_id, doc_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            element_id,
            element_data.get('file_id', ''),
            element_data.get('element_type', 'text'),
            element_data.get('content', ''),
            element_data.get('page_number', 0),
            element_data.get('section', ''),
            element_data.get('subsection', ''),
            element_data.get('heading_level', 0),
            json.dumps(element_data.get('bbox', [0,0,0,0])),
            element_data.get('position', 0),
            element_data.get('parent_element_id', ''),
            json.dumps(element_data.get('doc_metadata', {}))
        ))
        
        conn.commit()
        conn.close()
        return element_id
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relationship_type: str, strength: float = 1.0,
                        metadata: Dict = None):
        """Add a relationship between two elements."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO relationships (
                source_id, target_id, relationship_type, strength, metadata
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            source_id, target_id, relationship_type, strength,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def add_chunk(self, chunk_data: Dict) -> int:
        """Add a chunk with relationship references."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chunks (
                file_id, text, chunk_index, chunk_length, strategy,
                section, element_ids, parent_chunk_id, next_chunk_id, prev_chunk_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chunk_data.get('file_id', ''),
            chunk_data.get('text', ''),
            chunk_data.get('chunk_index', 0),
            chunk_data.get('chunk_length', 0),
            chunk_data.get('strategy', 'semantic'),
            chunk_data.get('section', ''),
            json.dumps(chunk_data.get('element_ids', [])),
            chunk_data.get('parent_chunk_id', None),
            chunk_data.get('next_chunk_id', None),
            chunk_data.get('prev_chunk_id', None)
        ))
        
        chunk_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chunk_id
    
    def get_document_elements(self, file_id: str) -> List[Dict]:
        """Get all elements for a document with relationships."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM elements WHERE file_id = ? ORDER BY page_number, position
        ''', (file_id,))
        elements = [dict(row) for row in cursor.fetchall()]
        
        for elem in elements:
            elem_id = elem['element_id']
            cursor.execute('''
                SELECT relationship_type, source_id, target_id, strength, metadata
                FROM relationships
                WHERE source_id = ? OR target_id = ?
            ''', (elem_id, elem_id))
            elem['relationships'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return elements
    
    def get_element_context(self, element_id: str, depth: int = 2) -> Dict:
        """Get full context for an element including parent, children, neighbors."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM elements WHERE element_id = ?', (element_id,))
        element = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
        
        if not element:
            conn.close()
            return {'element': None}
        
        context = {
            'self': element,
            'parent': None,
            'children': [],
            'siblings': [],
            'neighbors': [],
            'ancestors': [],
            'descendants': []
        }
        
        if element['parent_element_id']:
            cursor.execute('SELECT * FROM elements WHERE element_id = ?', 
                          (element['parent_element_id'],))
            context['parent'] = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
        
        cursor.execute('''
            SELECT * FROM elements WHERE parent_element_id = ? 
            ORDER BY page_number, position
        ''', (element_id,))
        context['children'] = [dict(row) for row in cursor.fetchall()]
        
        if element['parent_element_id']:
            cursor.execute('''
                SELECT * FROM elements 
                WHERE parent_element_id = ? AND element_id != ?
                ORDER BY page_number, position
            ''', (element['parent_element_id'], element_id))
            context['siblings'] = [dict(row) for row in cursor.fetchall()]
        
        page = element['page_number']
        position = element['position']
        
        cursor.execute('''
            SELECT * FROM elements 
            WHERE page_number = ? AND element_id != ?
            AND ABS(position - ?) <= 3
            ORDER BY ABS(position - ?), position
            LIMIT 6
        ''', (page, element_id, position, position))
        context['neighbors'] = [dict(row) for row in cursor.fetchall()]
        
        current_parent_id = element['parent_element_id']
        ancestors = []
        for _ in range(depth):
            if not current_parent_id:
                break
            cursor.execute('SELECT * FROM elements WHERE element_id = ?', 
                          (current_parent_id,))
            parent = cursor.fetchone()
            if parent:
                parent_dict = dict(parent)
                ancestors.append(parent_dict)
                current_parent_id = parent_dict.get('parent_element_id')
            else:
                break
        context['ancestors'] = ancestors
        
        conn.close()
        return context
    
    def get_chunk_with_context(self, chunk_id: int, expand_by: int = 2) -> Dict:
        """Get a chunk with its surrounding context."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM chunks WHERE chunk_id = ?', (chunk_id,))
        chunk = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
        
        if not chunk:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT * FROM chunks 
            WHERE file_id = ? AND chunk_index < ? 
            ORDER BY chunk_index DESC LIMIT ?
        ''', (chunk['file_id'], chunk['chunk_index'], expand_by))
        prev_chunks = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT * FROM chunks 
            WHERE file_id = ? AND chunk_index > ? 
            ORDER BY chunk_index ASC LIMIT ?
        ''', (chunk['file_id'], chunk['chunk_index'], expand_by))
        next_chunks = [dict(row) for row in cursor.fetchall()]
        
        element_ids = json.loads(chunk.get('element_ids', '[]'))
        elements = []
        for elem_id in element_ids:
            cursor.execute('SELECT * FROM elements WHERE element_id = ?', (elem_id,))
            elem = cursor.fetchone()
            if elem:
                elements.append(dict(elem))
        
        result = {
            'chunk': chunk,
            'prev_chunks': prev_chunks,
            'next_chunks': next_chunks,
            'elements': elements
        }
        
        conn.close()
        return result

    # ========== METHODS FOR BACKWARD COMPATIBILITY ==========

    def get_changes(self, course_id: str, drive_files: list) -> Dict:
        """Compare Drive files with database to find new/modified/deleted files."""
        # Get existing files from database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT file_id, file_name, modified_time, text_length, indexed_time, status
            FROM documents 
            WHERE course_id = ?
        ''', (course_id,))

        existing_files = {row['file_id']: dict(row) for row in cursor.fetchall()}
        conn.close()

        changes = {
            'new': [],
            'modified': [],
            'unchanged': [],
            'deleted': []
        }

        drive_map = {f['id']: f for f in drive_files}

        for file_id, drive_file in drive_map.items():
            if file_id not in existing_files:
                changes['new'].append(drive_file)
            else:
                db_file = existing_files[file_id]
                is_processed = (
                    db_file.get('text_length', 0) > 0 and 
                    db_file.get('indexed_time') is not None
                )

                if not is_processed:
                    changes['new'].append(drive_file)
                else:
                    drive_modified = drive_file.get('modifiedTime', '')
                    db_modified = db_file.get('modified_time', '')
                    if drive_modified > db_modified:
                        changes['modified'].append(drive_file)
                    else:
                        changes['unchanged'].append(drive_file)

        for file_id in existing_files:
            if file_id not in drive_map:
                changes['deleted'].append(existing_files[file_id])

        return changes

    def _get_existing_files(self, course_id: str) -> Dict:
        """Get all existing files for a course from the documents table."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT file_id, file_name, modified_time, text_length, indexed_time, status
            FROM documents 
            WHERE course_id = ?
        ''', (course_id,))

        rows = cursor.fetchall()
        conn.close()

        return {row['file_id']: dict(row) for row in rows}

    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM documents')
        total_files = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT course_id) FROM documents')
        total_courses = cursor.fetchone()[0]

        conn.close()

        return {
            'total_files': total_files,
            'total_courses': total_courses
        }

    def reset(self):
        """Reset the database (delete all data)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM documents')
        cursor.execute('DELETE FROM elements')
        cursor.execute('DELETE FROM relationships')
        cursor.execute('DELETE FROM chunks')

        conn.commit()
        conn.close()
        print("✅ Database reset")


_db_instance = None

def get_relationship_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = RelationshipDB()
    return _db_instance