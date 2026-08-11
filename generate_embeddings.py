import sqlite3
import pickle
import os
import time
from sentence_transformers import SentenceTransformer

def generate_embeddings():
    """Generate embeddings for all chunks using BAAI/bge-large-en-v1.5."""
    
    print("=" * 60)
    print("🧠 Generating Embeddings with BGE-large-en-v1.5")
    print("=" * 60)
    
    # Load BGE-large-en-v1.5 model
    print("\n📥 Loading BGE-large-en-v1.5 embedding model...")
    start_time = time.time()
    
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    load_time = time.time() - start_time
    
    print(f"✅ Model loaded in {load_time:.2f} seconds!")
    print(f"   Model dimension: {model.get_embedding_dimension()}")
    
    # Connect to database
    print("\n📂 Connecting to database...")
    conn = sqlite3.connect('metadata.db')
    cursor = conn.cursor()
    
    # Check if embedding column exists
    cursor.execute("PRAGMA table_info(chunks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'embedding' not in columns:
        print("⚠️ Adding 'embedding' column to chunks table...")
        cursor.execute('ALTER TABLE chunks ADD COLUMN embedding BLOB')
        conn.commit()
    
    # Get all chunks without embeddings
    cursor.execute('''
        SELECT chunk_id, file_id, text 
        FROM chunks 
        WHERE embedding IS NULL
    ''')
    chunks = cursor.fetchall()
    
    print(f"\n📊 Found {len(chunks)} chunks to embed")
    
    if not chunks:
        print("✅ All chunks already embedded!")
        conn.close()
        return
    
    # Generate embeddings in batches
    batch_size = 16  # Good for CPU
    total_embedded = 0
    
    print(f"\n🔢 Starting embedding generation...")
    print(f"   Batch size: {batch_size}")
    print(f"   Total batches: {(len(chunks)-1)//batch_size + 1}")
    print("-" * 40)
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [row[2] for row in batch]
        
        batch_num = i//batch_size + 1
        total_batches = (len(chunks)-1)//batch_size + 1
        print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} chunks)")
        
        try:
            embeddings = model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=batch_size,
                show_progress_bar=True
            )
            
            # Save embeddings back to database
            for j, (chunk_id, file_id, text) in enumerate(batch):
                embedding_blob = pickle.dumps(embeddings[j])
                cursor.execute('''
                    UPDATE chunks 
                    SET embedding = ? 
                    WHERE chunk_id = ?
                ''', (embedding_blob, chunk_id))
            
            conn.commit()
            total_embedded += len(batch)
            print(f"   ✅ Embedded {total_embedded}/{len(chunks)} chunks")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    cursor.execute('''
        UPDATE documents 
        SET embedding_status = 'embedded' 
        WHERE file_id IN (
            SELECT DISTINCT file_id FROM chunks WHERE embedding IS NOT NULL
        )
    ''')
    
    updated = cursor.rowcount
    conn.commit()
    print(f"   ✅ Updated {updated} documents to 'embedded'")
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ Complete! Embedded {total_embedded} chunks")
    print(f"   Model: BAAI/bge-large-en-v1.5")
    print(f"   Dimension: 1024")
    print(f"   Total time: {time.time() - start_time:.2f} seconds")
    print("=" * 60)
    # ===== AUTO-UPDATE DOCUMENT STATUS =====
    print("\n📊 Updating document embedding status...")
    
    

def embed_query(query: str):
    """Embed a single query for searching."""
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    # For better query results, add instruction
    instruction = "Represent this query for retrieving relevant passages: "
    query_with_instruction = instruction + query
    
    embedding = model.encode(
        query_with_instruction,
        normalize_embeddings=True
    )
    
    return embedding

def search_chunks(query: str, top_k: int = 5):
    """Search for similar chunks using BGE embeddings."""
    import numpy as np
    
    # Embed the query
    query_embedding = embed_query(query)
    
    # Connect to database
    conn = sqlite3.connect('metadata.db')
    cursor = conn.cursor()
    
    # Get all chunks with embeddings
    cursor.execute('''
        SELECT chunk_id, file_id, text, embedding 
        FROM chunks 
        WHERE embedding IS NOT NULL
    ''')
    chunks = cursor.fetchall()
    
    if not chunks:
        print("❌ No chunks with embeddings found!")
        return []
    
    # Calculate similarities
    results = []
    for chunk_id, file_id, text, embedding_blob in chunks:
        chunk_embedding = pickle.loads(embedding_blob)
        similarity = np.dot(query_embedding, chunk_embedding)
        results.append({
            'chunk_id': chunk_id,
            'file_id': file_id,
            'text': text,
            'similarity': float(similarity)
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return results[:top_k]

if __name__ == "__main__":
    generate_embeddings()