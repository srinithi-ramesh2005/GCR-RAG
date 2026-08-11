import sqlite3
import pickle
import faiss
import numpy as np
import os
from sentence_transformers import SentenceTransformer

try:
    from groq import Groq  # type: ignore[import]
except ImportError:
    Groq = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv  # type: ignore[import]
except ImportError:
    def load_dotenv(path: str = None, **kwargs):
        raise ImportError(
            "python-dotenv is required. Install it with 'pip install python-dotenv'"
        )

# Load environment file from the same folder
if os.path.exists('.env'):
    load_dotenv('.env')
elif os.path.exists('sri.env'):
    load_dotenv('sri.env')

class RAGQuerySystem:
    def __init__(self):
        """Initialize RAG system with Groq LLM."""
        
        # Get API key from .env file
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY not found in environment variables!")

        if Groq is None:
            raise ImportError(
                "groq package is not installed. Install it with 'pip install groq'"
            )
        self.client = Groq(api_key=self.api_key)
        self.model_name = "llama-3.3-70b-versatile"
        
        self._load_faiss_index()
        self._load_embedding_model()
        print("✅ RAG system initialized successfully!")
    
    def _load_faiss_index(self):
        """Load FAISS index and metadata."""
        print("📥 Loading FAISS index...")
        try:
            self.index = faiss.read_index('faiss_index/index.faiss')
            with open('faiss_index/index.pkl', 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"   ✅ Loaded {self.index.ntotal} vectors")
        except FileNotFoundError:
            print("   ❌ FAISS index not found! Please run create_faiss_index.py first.")
            raise
    
    def _load_embedding_model(self):
        """Load embedding model for queries."""
        print("📥 Loading embedding model...")
        self.embedder = SentenceTransformer('BAAI/bge-large-en-v1.5')
        print("   ✅ Model loaded")
    
    def search(self, query, top_k=5):
        """Search for relevant chunks."""
        query_embedding = self.embedder.encode(
            query,
            normalize_embeddings=True
        )
        query_embedding = np.array([query_embedding]).astype('float32')
        
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            results.append({
                'chunk_id': self.metadata['chunk_ids'][idx],
                'file_id': self.metadata['file_ids'][idx],
                'text': self.metadata['texts'][idx],
                'score': float(distance)
            })
        
        return results
    
    def build_context(self, results):
        """Build context from search results."""
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"--- Source {i} (Score: {result['score']:.3f}) ---\n{result['text']}"
            )
        return "\n\n".join(context_parts)
    
    def generate_answer(self, query, context):
        """Generate answer using Groq's Llama 3.3 API."""
        
        system_prompt = """You are a knowledgeable academic assistant. Answer questions based on the provided context.

        Rules:
        1. ONLY use information from the provided context
        2. If the context doesn't contain the answer, say "The provided context doesn't contain information about this topic."
        3. Use clear, well-structured responses with headings and bullet points
        4. Cite sources using [Source X] notation
        5. Be concise but comprehensive"""

        user_prompt = f"""
Context:
{context}

Question: {query}

Please provide a well-structured answer based ONLY on the context above."""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1024,
                top_p=0.9
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Groq API error: {e}")
            return None
    
    def ask(self, query):
        """Full RAG pipeline: search + generate answer."""
        
        print(f"\n🔍 Query: {query}")
        print("-" * 60)
        
        results = self.search(query, top_k=5)
        
        if not results:
            print("❌ No relevant chunks found!")
            return
        
        context = self.build_context(results)
        
        print("\n🤖 Generating structured answer with Groq Llama 3.3...")
        answer = self.generate_answer(query, context)
        
        print("\n" + "=" * 60)
        print("📝 ANSWER")
        print("=" * 60)
        print(answer)
        
        print("\n" + "=" * 60)
        print("📚 SOURCES")
        print("=" * 60)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"   Preview: {result['text'][:200]}...")


def main():
    print("=" * 60)
    print("🧠 RAG Query System with Groq Llama 3.3")
    print("=" * 60)
    
    # Check if environment configuration exists
    if not os.path.exists('.env') and not os.path.exists('sri.env'):
        print("\n⚠️ Environment file not found! Please create a .env file or sri.env in this folder.")
        print("\n📝 Example contents:")
        print("   GROQ_API_KEY=your-api-key-here")
        print("\nExample:")
        print("   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        return
    
    try:
        rag = RAGQuerySystem()
    except ValueError as e:
        print(f"\n❌ {e}")
        return
    
    print("\n✅ Ready! Ask questions about your documents.")
    print("   Type 'quit' or 'exit' to stop\n")
    
    while True:
        query = input("\n💬 Enter your question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not query:
            continue
        
        rag.ask(query)


if __name__ == "__main__":
    main()