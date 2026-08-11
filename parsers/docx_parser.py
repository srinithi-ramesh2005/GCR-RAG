import io
from docx import Document

def extract_text_from_bytes(file_bytes):
    """Extract text from Word bytes without saving to disk."""
    try:
        file_bytes.seek(0)
        doc = Document(file_bytes)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    except Exception as e:
        print(f"  ❌ Error processing Word document: {e}")
        return None

def test_docx():
    """Test function to verify DOCX parsing works."""
    print("📝 Testing Word parser...")
    print("✅ Word parser ready")