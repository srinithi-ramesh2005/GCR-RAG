import sqlite3
import pickle
import create_faiss_index
import numpy as np
import os
import time

def create_faiss_index():
    """Create FAISS index from embeddings stored in database."""
    
    print("=" * 60)
    print("🗂️ Creating FAISS Index")
    print("=" * 60)
    
    # Connect to database
    print("\n📂 Connecting to database...")
    conn = sqlite3.connect('metadata.db')
    cursor = conn.cursor()
    
    # Get all embeddings
    print("📊 Loading embeddings from database...")
    cursor.execute('''
        SELECT chunk_id, file_id, text, embedding 
        FROM chunks 
        WHERE embedding IS NOT NULL
    ''')
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ No embeddings found! Please run generate_embeddings.py first.")
        conn.close()
        return
    
    print(f"   Found {len(rows)} chunks with embeddings")
    
    # Prepare data for FAISS
    embeddings = []
    chunk_ids = []
    file_ids = []
    texts = []
    
    for chunk_id, file_id, text, embedding_blob in rows:
        try:
            embedding = pickle.loads(embedding_blob)
            embeddings.append(embedding)
            chunk_ids.append(chunk_id)
            file_ids.append(file_id)
            texts.append(text)
        except Exception as e:
            print(f"   ⚠️ Error loading chunk {chunk_id}: {e}")
    
    conn.close()
    
    if not embeddings:
        print("❌ No valid embeddings found!")
        return
    
    # Convert to numpy array
    print("\n🔢 Converting embeddings to numpy array...")
    embeddings_np = np.array(embeddings).astype('float32')
    dimension = embeddings_np.shape[1]
    
    print(f"   Shape: {embeddings_np.shape}")
    print(f"   Dimension: {dimension}")
    
    # Create FAISS index
    print("\n🗂️ Creating FAISS index...")
    
    # Choose index type based on number of vectors
    num_vectors = len(embeddings_np)
    
    if num_vectors < 10000:
        # Small dataset - use flat index (exact search)
        print("   Using IndexFlatIP (exact search for small dataset)")
        index = create_faiss_index.IndexFlatIP(dimension)  # Inner product = cosine similarity
    else:
        # Larger dataset - use IVF index (approximate search)
        print("   Using IndexIVFFlat (approximate search for large dataset)")
        quantizer = create_faiss_index.IndexFlatIP(dimension)
        nlist = min(100, num_vectors // 100)  # Number of clusters
        index = create_faiss_index.IndexIVFFlat(quantizer, dimension, nlist, create_faiss_index.METRIC_INNER_PRODUCT)
        print(f"   Training with {nlist} clusters...")
        index.train(embeddings_np)
    
    # Add vectors to index
    print("   Adding vectors to index...")
    start_time = time.time()
    index.add(embeddings_np)
    add_time = time.time() - start_time
    
    # Create output directory
    os.makedirs('faiss_index', exist_ok=True)
    
    # Save FAISS index
    index_path = 'faiss_index/index.faiss'
    print(f"💾 Saving index to {index_path}...")
    create_faiss_index.write_index(index, index_path)
    
    # Save metadata (mapping from FAISS IDs to chunk IDs)
    metadata = {
        'chunk_ids': chunk_ids,
        'file_ids': file_ids,
        'texts': texts,
        'dimension': dimension,
        'num_vectors': len(embeddings_np)
    }
    
    metadata_path = 'faiss_index/index.pkl'
    print(f"💾 Saving metadata to {metadata_path}...")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ FAISS Index Created Successfully!")
    print("=" * 60)
    print(f"   Total vectors: {len(embeddings_np)}")
    print(f"   Dimension: {dimension}")
    print(f"   Index type: {index.__class__.__name__}")
    print(f"   Index size: {os.path.getsize(index_path):,} bytes")
    print(f"   Metadata size: {os.path.getsize(metadata_path):,} bytes")
    print(f"   Add time: {add_time:.2f} seconds")
    print(f"\n📁 Files created:")
    print(f"   - {index_path}")
    print(f"   - {metadata_path}")
    print("=" * 60)
    
    return index, metadata

def test_faiss_search():
    """Test FAISS search with a sample query."""
    
    import pickle
    
    print("\n" + "=" * 60)
    print("🧪 Testing FAISS Search")
    print("=" * 60)
    
    # Check if index exists
    index_path = 'faiss_index/index.faiss'
    metadata_path = 'faiss_index/index.pkl'
    
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print("❌ FAISS index not found! Run create_faiss_index.py first.")
        return
    
    # Load index and metadata
    print("📥 Loading FAISS index...")
    index = create_faiss_index.read_index(index_path)
    
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    
    # Load embedding model
    from sentence_transformers import SentenceTransformer
    print("📥 Loading embedding model for query...")
    model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    # Sample query
    query = input("\n💬 Enter your question: ").strip()
    if not query:
        query = "What is cloud computing?"
    
    print(f"\n🔍 Query: {query}")
    
    # Generate query embedding
    query_embedding = model.encode(query, normalize_embeddings=True)
    query_embedding = np.array([query_embedding]).astype('float32')
    
    # Search
    k = 5  # Number of results
    print(f"\n📊 Searching top {k} results...")
    distances, indices = index.search(query_embedding, k)
    
    # Display results
    print("\n" + "=" * 60)
    print("📋 Search Results")
    print("=" * 60)
    
    for i, (idx, distance) in enumerate(zip(indices[0], distances[0]), 1):
        if idx == -1:
            continue
        
        chunk_id = metadata['chunk_ids'][idx]
        file_id = metadata['file_ids'][idx]
        text = metadata['texts'][idx]
        
        print(f"\n{i}. Score: {distance:.4f}")
        print(f"   Chunk ID: {chunk_id}")
        print(f"   File ID: {file_id[:30]}...")
        print(f"   Text: {text[:300]}...")

if __name__ == "__main__":
    # Create FAISS index
    create_faiss_index()
    
    # Test search
    test_faiss_search()