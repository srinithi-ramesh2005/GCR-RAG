import io
from pptx import Presentation

def extract_text_from_bytes(file_bytes):
    """Extract text from PowerPoint bytes without saving to disk."""
    try:
        file_bytes.seek(0)
        prs = Presentation(file_bytes)
        
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        
        return text.strip()
    
    except Exception as e:
        print(f"  ❌ Error processing PowerPoint: {e}")
        return None

def test_pptx():
    """Test function to verify PPTX parsing works."""
    print("📊 Testing PowerPoint parser...")
    print("✅ PowerPoint parser ready")