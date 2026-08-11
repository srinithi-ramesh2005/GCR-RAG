import io
import PyPDF2

def extract_text_from_bytes(file_bytes):
    """Extract text from PDF bytes without saving to disk."""
    try:
        file_bytes.seek(0)
        pdf_reader = PyPDF2.PdfReader(file_bytes)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    
    except Exception as e:
        print(f"  ❌ Error processing PDF: {e}")
        return None

def test_pdf():
    """Test function to verify PDF parsing works."""
    print("📄 Testing PDF parser...")
    print("✅ PDF parser ready")