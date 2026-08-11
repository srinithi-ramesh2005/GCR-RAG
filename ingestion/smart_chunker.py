import re
from typing import List, Dict

class SmartChunker:
    """
    Multi-strategy chunker for different file types.
    """
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_pdf(self, text: str, file_name: str) -> List[Dict]:
        """
        Semantic chunking for PDFs.
        - Splits by sections/headers
        - Keeps paragraphs together
        - Maintains context
        """
        if not text or len(text) < 10:
            return []
        
        chunks = []
        
        # Try to find sections
        sections = self._extract_sections(text)
        
        if sections:
            # Chunk by sections
            for section_title, section_text in sections:
                if section_text.strip():
                    # Further split long sections
                    sub_chunks = self._chunk_by_semantic(section_text)
                    for i, chunk_text in enumerate(sub_chunks):
                        chunks.append({
                            'text': chunk_text,
                            'file_name': file_name,
                            'source_type': 'pdf',
                            'section': section_title,
                            'chunk_index': len(chunks),
                            'chunk_length': len(chunk_text),
                            'strategy': 'semantic'
                        })
        else:
            # No clear sections - use semantic chunking
            sub_chunks = self._chunk_by_semantic(text)
            for i, chunk_text in enumerate(sub_chunks):
                chunks.append({
                    'text': chunk_text,
                    'file_name': file_name,
                    'source_type': 'pdf',
                    'section': 'general',
                    'chunk_index': len(chunks),
                    'chunk_length': len(chunk_text),
                    'strategy': 'semantic'
                })
        
        return chunks
    
    def chunk_pptx(self, slides: List[Dict], file_name: str) -> List[Dict]:
        """
        Slide-level chunking for PowerPoint.
        - Each slide is ONE chunk
        - Preserves slide title + content
        """
        chunks = []
        
        for slide in slides:
            slide_text = slide.get('text', '')
            if not slide_text.strip():
                continue
            
            # Keep each slide as a separate chunk
            chunks.append({
                'text': slide_text,
                'file_name': file_name,
                'source_type': 'pptx',
                'slide_number': slide.get('slide_number', 0),
                'slide_title': slide.get('title', 'Untitled'),
                'chunk_index': len(chunks),
                'chunk_length': len(slide_text),
                'strategy': 'slide_level'
            })
        
        return chunks
    
    def chunk_with_context(self, text: str, file_name: str) -> List[Dict]:
        """
        Context-aware chunking with overlap.
        - Adds surrounding context
        - Prevents information loss
        """
        if not text or len(text) < 10:
            return []
        
        # Use semantic chunking first
        chunks = self._chunk_by_semantic(text)
        
        result = []
        for i, chunk_text in enumerate(chunks):
            # Add context from neighboring chunks
            context_before = chunks[i-1][-100:] if i > 0 else ""
            context_after = chunks[i+1][:100] if i < len(chunks)-1 else ""
            
            result.append({
                'text': chunk_text,
                'file_name': file_name,
                'source_type': 'contextual',
                'context_before': context_before,
                'context_after': context_after,
                'chunk_index': len(result),
                'chunk_length': len(chunk_text),
                'strategy': 'contextual'
            })
        
        return result
    
    def _extract_sections(self, text: str) -> List[tuple]:
        """Extract section headers and their content."""
        sections = []
        current_section = "Introduction"
        current_text = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check if line is a section header
            if self._is_section_header(line):
                if current_text:
                    sections.append((current_section, '\n'.join(current_text)))
                    current_text = []
                current_section = line
            else:
                current_text.append(line)
        
        if current_text:
            sections.append((current_section, '\n'.join(current_text)))
        
        return sections
    
    def _is_section_header(self, line: str) -> bool:
        """Check if a line looks like a section header."""
        if len(line) < 100 and line.strip():
            patterns = [
                r'^[0-9]+\.[0-9]+',  # "1.1"
                r'^CHAPTER',         # "CHAPTER 1"
                r'^Section',         # "Section 1"
                r'^[A-Z][A-Z\s]+$',  # "INTRODUCTION"
                r'^[0-9]+\.\s*[A-Z]' # "1. INTRODUCTION"
            ]
            return any(re.match(pattern, line) for pattern in patterns)
        return False
    
    def _chunk_by_semantic(self, text: str) -> List[str]:
        """Chunk by semantic units (paragraphs, sentences)."""
        if len(text) < self.chunk_size:
            return [text]
        
        # Try to split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current = []
        current_len = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            para_len = len(para)
            
            if current_len + para_len > self.chunk_size and current:
                chunks.append('\n'.join(current))
                # Keep overlap
                overlap_text = []
                overlap_len = 0
                for p in reversed(current):
                    if overlap_len + len(p) <= self.overlap:
                        overlap_text.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break
                current = overlap_text
                current_len = overlap_len
            
            current.append(para)
            current_len += para_len
        
        if current:
            chunks.append('\n'.join(current))
        
        return chunks
    
    def get_strategy_stats(self, chunks: List[Dict]) -> Dict:
        """Get statistics about chunking strategies used."""
        if not chunks:
            return {'total': 0}
        
        strategies = {}
        total_length = 0
        
        for chunk in chunks:
            strategy = chunk.get('strategy', 'unknown')
            strategies[strategy] = strategies.get(strategy, 0) + 1
            total_length += chunk.get('chunk_length', 0)
        
        return {
            'total_chunks': len(chunks),
            'strategies': strategies,
            'avg_length': total_length // len(chunks) if chunks else 0
        }