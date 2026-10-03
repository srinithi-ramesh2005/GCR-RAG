# GCR-RAG — Intelligent Google Classroom Retrieval-Augmented Generation System

> A structure-aware Retrieval-Augmented Generation (RAG) system that connects to Google Classroom and Google Drive, processes course materials such as PDFs and PowerPoint presentations, retrieves relevant content using hybrid search, and generates context-grounded answers with page/slide-level references.

---

## 📌 Overview

**GCR-RAG** is a Retrieval-Augmented Generation system designed specifically for academic content distributed through **Google Classroom and Google Drive**.

Traditional document-based chatbots generally treat documents as plain text. This becomes a problem when academic materials contain:

- Text distributed across multiple pages
- Tables
- Headings and sections
- PowerPoint slide structures
- Diagrams and images
- Related concepts appearing in different documents
- Repeated information across multiple lecture materials

GCR-RAG addresses these problems by building a **structure-aware retrieval pipeline** rather than simply splitting documents into fixed-size text chunks.

The system connects to Google Classroom using **OAuth 2.0**, discovers course materials, downloads supported files, extracts their structure and content, creates meaningful chunks, generates embeddings, indexes them, and retrieves the most relevant context for a user's question.

The retrieved context is then passed to **Llama 3.3 through Groq** to generate a grounded answer.

### Core idea

```text
Google Classroom / Google Drive
              ↓
       OAuth 2.0 Authentication
              ↓
       Course & File Discovery
              ↓
      Document Download / Sync
              ↓
     Layout-Aware Document Parsing
              ↓
     Structure-Aware Chunking
              ↓
     Parent-Child Relationships
              ↓
        Hybrid Retrieval
       ↙               ↘
Semantic Search       Keyword Search
       ↘               ↙
          Re-ranking
              ↓
      Relevant Context
              ↓
       Llama 3.3 / Groq
              ↓
       Grounded Answer
```

---

# 🎯 Problem Statement

Students often have course materials spread across multiple Google Classroom posts, PDFs, PowerPoint presentations, and Drive files.

Finding the answer to a question manually can require:

1. Opening Google Classroom
2. Finding the correct course
3. Locating the relevant announcement/material
4. Opening one or more files
5. Searching through multiple pages or slides
6. Understanding tables or diagrams
7. Combining information from different documents

A conventional keyword search is also insufficient for questions such as:

> "Why does the system use a distributed architecture?"

The exact words **"distributed architecture"** may not appear in the relevant section. The document may instead discuss scalability, independent services, horizontal expansion, or distributed processing.

GCR-RAG therefore combines:

- Semantic retrieval
- Keyword retrieval
- Document structure
- Metadata
- Parent-child relationships
- Context-aware chunking
- LLM-based generation

to improve the relevance and grounding of retrieved academic information.

---

# 🚀 Key Features

## 1. Google Classroom Integration

The system connects to Google Classroom and Google Drive through Google's APIs.

Instead of requiring users to manually upload every document, the system can work with course materials available through the authenticated Google account.

### Flow

```text
User
 ↓
Google OAuth 2.0
 ↓
Google Classroom API
 ↓
Course Discovery
 ↓
Course Materials
 ↓
Google Drive
 ↓
Documents
```

This allows the RAG system to operate over actual course material rather than a manually created static document collection.

---

## 2. Dynamic Course and File Synchronization

The system maintains awareness of the documents available through the connected Classroom/Drive environment.

Instead of rebuilding the entire index whenever a new document appears, the indexing pipeline can identify newly available or changed files and process the required content incrementally.

### Incremental indexing

```text
Existing Index
      ↓
Check Classroom / Drive
      ↓
Compare File Metadata
      ↓
 ┌───────────────┐
 │               │
New File     Modified File
 │               │
 ↓               ↓
Process        Re-process
 │               │
 └───────┬───────┘
         ↓
      Update
        Index
```

This reduces unnecessary document processing and makes synchronization more practical for continuously changing course materials.

---

# 📄 3. Layout-Aware Document Parsing

A major design goal of GCR-RAG is to avoid treating a document as a simple sequence of characters.

Academic documents often contain meaningful structure:

```text
Title
 ├── Section
 │    ├── Paragraph
 │    ├── Table
 │    └── Explanation
 └── Section
      ├── Paragraph
      └── Diagram
```

The parsing pipeline therefore attempts to preserve document-level information such as:

- Page number
- Section
- Heading
- Paragraph
- Tables
- Slide number
- Document name
- Course
- File metadata

This information is attached to retrieved content as metadata.

### Example metadata

```json
{
  "course": "Data Engineering",
  "file_name": "Kafka_Introduction.pdf",
  "page": 12,
  "section": "Consumer Groups",
  "chunk_type": "section",
  "source": "Google Drive"
}
```

This allows the system to retain the relationship between the retrieved text and its original location.

---

# 📊 4. Table Extraction

Tables contain structured information that can lose meaning if extracted as plain text.

For example:

| Component | Responsibility |
|---|---|
| Producer | Publishes messages |
| Broker | Stores messages |
| Consumer | Reads messages |

A naïve parser may produce an unstructured sequence of words.

GCR-RAG preserves table information as structured content wherever possible so that questions involving comparisons, mappings, and tabular information can be answered more accurately.

---

# 🧩 5. Structure-Aware Multi-Strategy Chunking

One of the major design decisions in this project is **not relying only on fixed-size chunking**.

A fixed-size strategy might simply divide a document into:

```text
Chunk 1 → characters 0–1000
Chunk 2 → characters 1000–2000
Chunk 3 → characters 2000–3000
```

This can split related information between different chunks.

Instead, GCR-RAG uses the structure of the document to create more meaningful retrieval units.

### Different chunking strategies

#### Semantic chunks

Content is grouped according to its meaning.

```text
Concept
   ↓
Explanation
   ↓
Example
```

#### Contextual chunks

The chunk retains surrounding context so that an isolated paragraph does not lose its meaning.

#### Section-level chunks

Headings and their associated content are grouped together.

```text
Heading
   +
Paragraphs
   +
Examples
```

#### Slide-level chunks

For PowerPoint presentations, the slide acts as an important structural boundary.

```text
Slide 7
 ├── Title
 ├── Text
 ├── Notes / extracted content
 └── Related visual information
```

This makes retrieval more meaningful for lecture presentations.

---

# 🌳 6. Parent-Child Relationships

A document can naturally be represented as a hierarchy.

For example:

```text
Document
│
├── Chapter 1
│   ├── Section 1.1
│   │   ├── Paragraph A
│   │   └── Paragraph B
│   │
│   └── Section 1.2
│       └── Paragraph C
│
└── Chapter 2
    └── Section 2.1
        └── Paragraph D
```

Instead of considering every chunk as completely independent, GCR-RAG maintains relationships between larger and smaller pieces of content.

For example:

```text
Parent:
"Kafka Consumer Groups"

        ↓

Child:
"A consumer group consists of multiple consumers..."

        ↓

Related child:
"Partitions are distributed among consumers..."
```

This provides additional context during retrieval.

---

# 🕸️ 7. Relationship Graph

The project also uses **NetworkX** to represent relationships between documents, sections, chunks, and related content.

Conceptually:

```text
Course
  │
  ├── Document A
  │      │
  │      ├── Section A1
  │      │      ├── Chunk A1.1
  │      │      └── Chunk A1.2
  │      │
  │      └── Section A2
  │
  └── Document B
         │
         └── Section B1
```

These relationships provide structural information that pure vector similarity does not capture.

The graph can help preserve:

- Parent-child relationships
- Section relationships
- Document relationships
- Related chunks
- Course-document associations

---

# 🔎 8. Hybrid Search

A major component of GCR-RAG is **hybrid retrieval**.

Pure semantic search and pure keyword search each have weaknesses.

### Semantic search

Semantic search can understand that:

```text
"horizontal scaling"
```

and

```text
"adding more machines to handle increased load"
```

are conceptually related.

However, exact terms such as:

```text
Kafka
HTTP 404
ACID
B+ Tree
```

may be important even when semantic similarity is not sufficient.

### Keyword search

Keyword-based retrieval is strong at exact terminology but may fail when the question uses different wording from the document.

### Hybrid retrieval

GCR-RAG combines both approaches.

```text
                 User Query
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
   Semantic Retrieval      Keyword Retrieval
          │                     │
          ↓                     ↓
    Vector Similarity       Term Matching
          │                     │
          └──────────┬──────────┘
                     ↓
               Combined Results
                     ↓
                 Re-ranking
                     ↓
             Final Context
```

This improves retrieval robustness for both conceptual and terminology-heavy questions.

---

# 🧠 9. Embedding-Based Retrieval

The project uses:

**BGE-large-en-v1.5**

to convert chunks into dense vector representations.

For example:

```text
"Kafka is a distributed event streaming platform."
                         ↓
                  Embedding Model
                         ↓
                 [0.021, -0.183, ...]
```

A user's question is embedded using the same model.

The system then searches for chunks whose vector representations are similar to the query.

---

# 🗃️ 10. FAISS Vector Index

The generated embeddings are stored and searched using **FAISS**.

Conceptually:

```text
Document
   ↓
Chunk
   ↓
Embedding
   ↓
FAISS Index
```

When the user submits a question:

```text
Question
   ↓
Query Embedding
   ↓
FAISS Similarity Search
   ↓
Top Relevant Chunks
```

FAISS provides efficient similarity search over the document embeddings.

---

# 🤖 11. LLM-Based Answer Generation

After retrieval, the most relevant context is passed to:

**Llama 3.3 through Groq**

The LLM is not expected to answer purely from its internal knowledge.

Instead, the system follows:

```text
Question
   ↓
Retrieve relevant academic content
   ↓
Build context
   ↓
Send context + question to LLM
   ↓
Generate grounded response
```

This is the core RAG principle:

> **Retrieve first, generate second.**

---

# 📚 12. Source and Page-Level References

Retrieved chunks retain metadata about their original location.

For example:

```text
Answer:
Kafka partitions allow a topic to be distributed across brokers.

Source:
Kafka_Architecture.pdf
Page: 14
Section: Topic Partitions
```

For PowerPoint content:

```text
Source:
Kafka_Introduction.pptx
Slide: 18
```

This makes the generated answer more traceable to the original course material.

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │       Frontend       │
                         │       React UI       │
                         └──────────┬───────────┘
                                    │
                                    │ HTTP
                                    ↓
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │    Backend / API     │
                         └──────────┬───────────┘
                                    │
                     ┌──────────────┼───────────────┐
                     │              │               │
                     ↓              ↓               ↓
              Google OAuth    Query Handling    File Upload
                     │              │
                     ↓              │
             Google Classroom       │
             Google Drive           │
                     │              │
                     ↓              │
              File Discovery        │
                     │              │
                     ↓              │
             Document Parser        │
                     │              │
                     ↓              │
             Structure-Aware        │
                Chunking            │
                     │              │
                     ↓              │
              Metadata + Graph      │
                     │              │
                     ↓              │
              BGE-large-en-v1.5     │
                     │              │
                     ↓              │
                  FAISS             │
                     │              │
                     └──────┬───────┘
                            ↓
                    Hybrid Retrieval
                            ↓
                       Re-ranking
                            ↓
                    Context Builder
                            ↓
                    Groq / Llama 3.3
                            ↓
                       Final Answer
```

---

# 🔄 End-to-End Data Flow

## Phase 1 — Authentication

```text
User
 ↓
Login
 ↓
Google OAuth 2.0
 ↓
Authorization
 ↓
Access Token
```

The backend uses the authenticated Google account to access the required Classroom/Drive resources.

---

## Phase 2 — Course Discovery

```text
Google Classroom API
        ↓
Available Courses
        ↓
Selected Course
        ↓
Course Materials
```

The system identifies the files associated with the course.

---

## Phase 3 — File Synchronization

```text
Course Materials
       ↓
Google Drive
       ↓
File Metadata
       ↓
New / Modified / Existing
       ↓
Incremental Processing
```

Only the required documents are processed or updated.

---

## Phase 4 — Document Processing

```text
PDF / PPTX / DOCX
        ↓
Document Parser
        ↓
Text + Structure
        ↓
Pages / Slides / Tables
        ↓
Metadata Extraction
```

---

## Phase 5 — Chunking

```text
Parsed Document
       ↓
Structure Detection
       ↓
Heading / Section / Slide
       ↓
Semantic + Contextual Chunking
       ↓
Parent-Child Relationships
```

---

## Phase 6 — Indexing

```text
Chunks
  ↓
BGE-large-en-v1.5
  ↓
Embeddings
  ↓
FAISS
```

Additional metadata and relationships are maintained separately for filtering and contextual retrieval.

---

# 🔍 Query Processing Pipeline

When the user asks:

> "Explain how Kafka distributes messages among consumers."

the query goes through:

```text
User Query
    ↓
Query Processing
    ↓
Semantic Embedding
    ↓
Semantic Search
    │
    ├───────────────┐
    ↓               ↓
FAISS          Keyword Search
    │               │
    └───────┬───────┘
            ↓
      Hybrid Results
            ↓
        Re-ranking
            ↓
 Context Expansion
            ↓
 Relevant Chunks
            ↓
 Prompt Construction
            ↓
 Llama 3.3
            ↓
 Grounded Answer
```

---

# 🧪 Example

### User Query

```text
Why are consumer groups used in Kafka?
```

### Retrieval

The system may retrieve:

```text
Document: Kafka_Consumer_Groups.pdf
Page: 12
Section: Consumer Groups

"Consumers belonging to the same consumer group divide
partitions among themselves..."
```

Additional related chunks may be retrieved from:

```text
Page 13
Section: Partition Assignment
```

### Context Assembly

```text
Question
+
Relevant section
+
Related child chunks
+
Document metadata
+
Source information
```

### LLM

The retrieved context is passed to Llama 3.3.

### Final Response

The generated response explains the concept while retaining the source information.

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python |
| API Framework | FastAPI |
| Frontend | React |
| Authentication | Google OAuth 2.0 |
| Data Source | Google Classroom API |
| File Source | Google Drive API |
| PDF Processing | PyMuPDF |
| Embedding Model | BGE-large-en-v1.5 |
| Vector Search | FAISS |
| Graph Processing | NetworkX |
| Metadata / Persistence | SQLite |
| LLM | Llama 3.3 |
| LLM Provider | Groq |

---

# 📁 Project Architecture

A representative structure is:

```text
gcr-rag/
│
├── backend/
│   │
│   ├── main.py
│   │
│   ├── routes/
│   │   ├── query.py
│   │   ├── upload.py
│   │   └── courses.py
│   │
│   ├── services/
│   │   ├── classroom.py
│   │   ├── drive.py
│   │   ├── parser.py
│   │   ├── chunker.py
│   │   ├── retriever.py
│   │   ├── embeddings.py
│   │   └── llm.py
│   │
│   ├── indexing/
│   │   ├── vector_store.py
│   │   └── graph.py
│   │
│   └── database/
│       └── sqlite/
│
├── frontend/
│   └── ...
│
├── data/
│   ├── documents/
│   ├── index/
│   └── metadata/
│
├── requirements.txt
├── .env.example
└── README.md
```

> The exact directory structure can be adapted to the implementation in the repository.

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd gcr-rag
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Configuration

Create a `.env` file containing the required configuration.

Example:

```env
GROQ_API_KEY=your_groq_api_key

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

DATABASE_URL=sqlite:///gcr_rag.db

FAISS_INDEX_PATH=./data/index
DOCUMENT_PATH=./data/documents
```

Do **not** commit API keys, OAuth credentials, or tokens to GitHub.

Add them to `.gitignore`:

```gitignore
.env
credentials.json
token.json
venv/
__pycache__/
data/
*.db
```

---

# 🔑 Google OAuth Setup

The Google integration uses OAuth 2.0.

High-level setup:

```text
Google Cloud Project
       ↓
Enable APIs
       ↓
Create OAuth Credentials
       ↓
Configure Redirect URI
       ↓
Backend OAuth Flow
       ↓
User Authorization
       ↓
Access Token
```

The required Google APIs depend on the exact resources accessed by the application, primarily:

- Google Classroom API
- Google Drive API

The OAuth credentials should be stored securely and never committed to the repository.

---

# ▶️ Running the Application

Start the FastAPI backend using:

```bash
uvicorn backend.main:app --reload
```

The backend becomes available through the configured local server.

FastAPI also provides interactive API documentation through its Swagger/OpenAPI interface.

---

# 🔌 API Endpoints

The backend exposes API functionality for the major application operations.

## Query

```http
POST /query
```

Used to submit a natural-language question to the RAG system.

Conceptual request:

```json
{
  "query": "What is a Kafka consumer group?"
}
```

---

## Upload

```http
POST /upload
```

Used to provide documents for processing/indexing when manual upload is required.

---

## Courses

```http
GET /courses
```

Used to retrieve available Google Classroom courses.

---

# 🧠 Why RAG Instead of Sending Documents Directly to an LLM?

Sending an entire collection of course documents directly to an LLM has several problems:

### 1. Context limitations

Large collections can exceed the model's context window.

### 2. Higher cost

Sending unnecessary documents increases token usage.

### 3. Irrelevant information

The model receives information unrelated to the question.

### 4. Poor source traceability

It becomes harder to identify exactly where an answer came from.

### 5. Retrieval quality

Relevant information may be buried inside a large context.

RAG solves this by retrieving only the most relevant information.

```text
100 Documents
     ↓
Retriever
     ↓
Top Relevant Chunks
     ↓
LLM
```

---

# 🆚 Why Structure-Aware RAG?

A simple RAG pipeline is often:

```text
Document
 ↓
Fixed-size chunks
 ↓
Embeddings
 ↓
Vector DB
 ↓
Top-K
 ↓
LLM
```

GCR-RAG extends this:

```text
Document
 ↓
Layout-aware parsing
 ↓
Structure extraction
 ↓
Multiple chunking strategies
 ↓
Metadata
 ↓
Parent-child relationships
 ↓
Graph
 ↓
Semantic retrieval
 +
Keyword retrieval
 ↓
Hybrid retrieval
 ↓
Re-ranking
 ↓
Context expansion
 ↓
LLM
```

The additional structure is particularly useful for academic documents because meaning is frequently dependent on headings, sections, slides, tables, and surrounding context.

---

# 📈 Retrieval Strategy

The retrieval system considers multiple signals instead of relying exclusively on vector similarity.

### Semantic similarity

Answers:

> "Is this content conceptually similar to the question?"

### Keyword relevance

Answers:

> "Does this content contain important terms from the question?"

### Metadata

Answers:

> "Which course, document, page, or section does this content belong to?"

### Structural relationships

Answers:

> "What parent section or related chunk does this retrieved content belong to?"

Combining these signals creates a more context-aware retrieval pipeline.

---

# 🗄️ Role of SQLite

SQLite is used for lightweight persistence and metadata management.

It can maintain information such as:

```text
File ID
File Name
Course ID
Document Type
Last Modified Time
Processing Status
Chunk ID
Page / Slide
Metadata
```

This information is particularly useful for incremental synchronization.

For example:

```text
Google Drive File
       ↓
Has file ID + modified timestamp
       ↓
Compare with local metadata
       ↓
No change → Skip
Changed → Re-index
New → Index
```

---

# 🕸️ Role of NetworkX

NetworkX is used to model relationships between pieces of content.

Example:

```text
Document
   │
   ├── Section
   │      │
   │      ├── Chunk
   │      └── Chunk
   │
   └── Section
          │
          └── Chunk
```

This allows the retrieval system to reason about relationships beyond simple vector similarity.

---

# ⚡ Performance Considerations

The system is designed to avoid unnecessary processing.

### Incremental indexing

Only new or modified files need to be processed.

### Metadata filtering

Documents can be narrowed using metadata before or during retrieval.

### Vector similarity search

FAISS enables efficient nearest-neighbor search over embeddings.

### Hybrid retrieval

Combining retrieval methods reduces dependence on a single retrieval strategy.

### Context control

Only relevant chunks are sent to the LLM instead of entire documents.

---

# 🛡️ Security Considerations

The system handles authenticated Google Classroom/Drive data, so security is important.

Important practices include:

- Never commit OAuth credentials
- Never commit API keys
- Store secrets in environment variables
- Use appropriate Google OAuth scopes
- Restrict access to authenticated users
- Avoid exposing access tokens to the frontend
- Validate uploaded files
- Avoid logging sensitive document content unnecessarily

The backend acts as the API layer between the frontend, Google APIs, retrieval system, and LLM.

```text
Frontend
   ↓
FastAPI
   ↓
Authenticated services
   ↓
Google APIs / RAG Pipeline
```

---

# ❗ Limitations

Although GCR-RAG improves retrieval over conventional document search, several challenges remain.

### 1. Complex visual understanding

Diagrams and images can contain information that cannot always be represented accurately through extracted text alone.

### 2. OCR dependency

Scanned documents may require OCR before their content becomes searchable.

### 3. Retrieval errors

If the correct chunk is not retrieved, the LLM may not have enough evidence to generate the correct answer.

### 4. Ambiguous questions

Questions with insufficient context can produce multiple plausible retrieval results.

### 5. LLM
