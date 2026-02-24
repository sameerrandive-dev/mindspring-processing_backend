# Notebook and Source Flow Documentation

## Overview

This document explains how **Notebooks** and **Sources** work together in the MindSpring platform, including their relationships, lifecycle, and data flow.

## Entity Relationships

```
User
  └── Notebook (1:N)
       ├── Source (1:N)
       │    └── Chunk (1:N)
       ├── Conversation (1:N)
       ├── Quiz (1:N)
       └── StudyGuide (1:N)
```

### Key Relationships

- **User → Notebook**: One user can have many notebooks
- **Notebook → Source**: One notebook can contain many sources (documents, URLs, text)
- **Source → Chunk**: One source is split into many chunks for RAG
- **Notebook → Conversation**: Conversations are scoped to a notebook
- **Source → Conversation**: Conversations can reference a specific source (RAG mode)

---

## 📓 Notebook Flow

### What is a Notebook?

A **Notebook** is a container for organizing learning materials and conversations. Think of it as a workspace for a specific topic or course.

**Properties**:
- `id`: Unique identifier (UUID)
- `owner_id`: User who owns the notebook
- `title`: Notebook name
- `description`: Optional description
- `language`: Language setting (default: "en")
- `tone`: Writing tone (default: "educational")
- `max_context_tokens`: Maximum tokens for context (default: 8000)
- `created_at`, `updated_at`, `deleted_at`: Timestamps

### Notebook Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│ 1. CREATE NOTEBOOK                                      │
│    User creates a new notebook                          │
│    - Set title, description                             │
│    - Configure language, tone                           │
│    - Assign to user (owner_id)                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. ADD SOURCES                                          │
│    User adds documents/URLs/text to notebook            │
│    - Upload PDFs                                        │
│    - Add URLs                                           │
│    - Paste text content                                 │
│    - Sources are processed and chunked                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CREATE CONVERSATIONS                                 │
│    User starts conversations in notebook                │
│    - Normal chat: General conversation                 │
│    - RAG chat: Questions about sources                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. GENERATE NOTEBOOK-WIDE ARTIFACTS                     │
│    User creates artifacts from entire notebook          │
│    - Notebook Summary (detailed/bullets)                │
│    - Notebook Quiz (10-50 questions)                    │
│    - Notebook Study Guide (structured/outline)          │
│    - Notebook Mindmap (Mermaid/JSON)                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. DELETE NOTEBOOK (Soft Delete)                        │
│    Notebook is marked as deleted                        │
│    - Can be restored                                    │
│    - Cascades to sources, chunks, conversations         │
└─────────────────────────────────────────────────────────┘
```

### Notebook Operations

#### Create Notebook

```python
POST /api/v1/notebooks/
{
    "title": "Machine Learning Basics",
    "description": "Learning ML fundamentals",
    "language": "en",
    "tone": "educational"
}
```

**Flow**:
1. Validate input
2. Create notebook record
3. Set `owner_id` to current user
4. Return notebook with ID

#### List Notebooks

```python
GET /api/v1/notebooks/?skip=0&limit=20
```

**Returns**: List of user's notebooks with sources loaded

#### Get Notebook Details

```python
GET /api/v1/notebooks/{notebook_id}
```

**Returns**: Notebook with:
- All sources
- All conversations
- All chunks
- Metadata

#### Update Notebook

```python
PUT /api/v1/notebooks/{notebook_id}
{
    "title": "Updated Title",
    "description": "Updated description"
}
```

#### Notebook Generation (NotebookLM Features)

```python
# Generate notebook-wide summary
POST /api/v1/notebooks/{notebook_id}/generate/summary
{
    "max_length": 1000,
    "style": "detailed"
}

# Generate notebook-wide quiz
POST /api/v1/notebooks/{notebook_id}/generate/quiz
{
    "topic": "Python Fundamentals",
    "num_questions": 20,
    "difficulty": "intermediate"
}

# Generate notebook-wide study guide
POST /api/v1/notebooks/{notebook_id}/generate/guide
{
    "topic": "Exam 1 Prep",
    "format": "structured"
}

# Generate notebook-wide mindmap
POST /api/v1/notebooks/{notebook_id}/generate/mindmap
{
    "format": "mermaid"
}
```

**Flow**:
1. Aggregate all chunks from all sources in the notebook
2. Pass combined context to LLM with specific instructions
3. Save generated artifact in historical records/dedicated tables
4. Return the generated discovery/learning tool


#### Delete Notebook (Soft Delete)

```python
DELETE /api/v1/notebooks/{notebook_id}
```

**Cascade Behavior**:
- Sources are soft-deleted
- Chunks are soft-deleted
- Conversations are soft-deleted
- Can be restored later

---

## 📄 Source Flow

### What is a Source?

A **Source** is a document, URL, or text content added to a notebook. Sources are processed and split into chunks for RAG operations.

**Properties**:
- `id`: Unique identifier (UUID)
- `notebook_id`: Parent notebook
- `type`: Source type ("pdf", "url", "text", etc.)
- `title`: Source title
- `original_url`: URL if source is from web
- `file_path`: Path to file if uploaded
- `metadata_`: Additional metadata (JSONB)
- `status`: Processing status ("processing", "completed", "failed")
- `created_at`, `updated_at`, `deleted_at`: Timestamps

### Source Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│ 1. UPLOAD/ADD SOURCE                                    │
│    User uploads document or adds URL                    │
│    - PDF upload                                         │
│    - URL submission                                     │
│    - Text paste                                         │
│    - Status: "processing"                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. PROCESS SOURCE (Background Job)                      │
│    Celery worker processes source                       │
│    - Extract text (PDF parsing, OCR)                    │
│    - Validate content                                   │
│    - Status: "processing"                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CHUNK DOCUMENT                                       │
│    Text is split into chunks                            │
│    - Fixed-size chunks (512 chars)                      │
│    - Overlap (100 chars)                                │
│    - Create Chunk records                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. GENERATE EMBEDDINGS                                  │
│    Each chunk gets vector embedding                     │
│    - Call LLM embedding API                             │
│    - Store embeddings                                   │
│    - Status: "completed"                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. SOURCE READY FOR RAG                                │
│    Source can be used in RAG conversations              │
│    - Chunks searchable via vector similarity            │
│    - Can be referenced in conversations                 │
└─────────────────────────────────────────────────────────┘
```

### Source Processing Flow

#### Step 1: Upload Source

```python
POST /api/v1/documents/
Content-Type: multipart/form-data

file: <PDF file>
title: "Machine Learning Guide"
```

**What Happens**:
1. File is uploaded to storage (S3/CEPH)
2. Source record created with `status="processing"`
3. Background job created for processing
4. Return source ID immediately

#### Step 2: Background Processing

```python
# Celery worker picks up job
@celery_app.task
async def process_document(source_id: str):
    # 1. Download file from storage
    file_content = await storage.get(source.file_path)
    
    # 2. Extract text
    text = await pdf_service.extract_text(file_content)
    
    # 3. Chunk text
    chunks = rag_service.chunk_text(text)
    
    # 4. Generate embeddings
    embeddings = await llm_client.generate_embeddings(chunks)
    
    # 5. Store chunks with embeddings
    for chunk, embedding in zip(chunks, embeddings):
        await chunk_repo.create(
            source_id=source_id,
            notebook_id=source.notebook_id,
            plain_text=chunk,
            embedding=embedding
        )
    
    # 6. Update source status
    await source_repo.update(source_id, status="completed")
```

#### Step 3: Source Ready

Once processing completes:
- Source `status` changes to `"completed"`
- Chunks are available for RAG search
- Source can be used in RAG conversations

### Source Operations

#### Add Source to Notebook

```python
POST /api/v1/notebooks/{notebook_id}/sources
{
    "type": "pdf",
    "title": "ML Guide",
    "file_path": "documents/user-123/source-456/file.pdf"
}
```

**Flow**:
1. Verify user owns notebook
2. Create source record
3. Queue processing job
4. Return source with `status="processing"`

#### List Sources in Notebook

```python
GET /api/v1/notebooks/{notebook_id}/sources
```

**Returns**: All sources in notebook with:
- Processing status
- Chunk count
- Metadata

#### Get Source Details

```python
GET /api/v1/sources/{source_id}
```

**Returns**: Source with:
- All chunks
- Processing status
- Metadata

#### Delete Source

```python
DELETE /api/v1/sources/{source_id}
```

**Cascade Behavior**:
- Chunks are deleted (CASCADE)
- Conversations referencing source are updated
- File is deleted from storage

---

## 🔄 Complete Flow: Document Upload to RAG Chat

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: User Creates Notebook                         │
│                                                         │
│ POST /api/v1/notebooks/                                │
│ {                                                       │
│   "title": "ML Course",                                 │
│   "description": "Learning ML"                          │
│ }                                                       │
│                                                         │
│ → Notebook created with ID: notebook-123               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: User Uploads Document                          │
│                                                         │
│ POST /api/v1/documents/                                 │
│ file: ml-guide.pdf                                      │
│                                                         │
│ → Document uploaded                                     │
│ → Source created: source-456                           │
│ → Status: "processing"                                 │
│ → Job queued: job-789                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Background Worker Processes                    │
│                                                         │
│ Worker picks up job-789                                 │
│                                                         │
│ 1. Extract text from PDF                                │
│ 2. Chunk text (512 chars, 100 overlap)                  │
│ 3. Generate embeddings for chunks                       │
│ 4. Store chunks with embeddings                         │
│ 5. Update source status: "completed"                    │
│                                                         │
│ → 50 chunks created                                     │
│ → All chunks have embeddings                            │
│ → Source ready for RAG                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 4: User Creates RAG Conversation                  │
│                                                         │
│ POST /api/v1/chat/conversations                         │
│ {                                                       │
│   "notebook_id": "notebook-123",                        │
│   "mode": "rag",                                        │
│   "source_id": "source-456"                             │
│ }                                                       │
│                                                         │
│ → Conversation created: conv-999                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 5: User Asks Question                             │
│                                                         │
│ POST /api/v1/chat/conversations/conv-999/messages      │
│ {                                                       │
│   "content": "What is machine learning?"                │
│ }                                                       │
│                                                         │
│ Flow:                                                   │
│ 1. Generate query embedding                            │
│ 2. Search similar chunks (vector similarity)            │
│ 3. Filter by notebook_id and source_id                  │
│ 4. Get top 5 chunks                                     │
│ 5. Format chunks as context                            │
│ 6. Get conversation history                            │
│ 7. Generate LLM response with context                   │
│ 8. Save response with chunk_ids                         │
│                                                         │
│ → Response includes relevant document chunks            │
│ → Response cites sources                                │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Diagram

```
User Action
    │
    ├─→ Create Notebook
    │       │
    │       └─→ Notebook Record Created
    │
    ├─→ Upload Document
    │       │
    │       ├─→ Source Record Created (status: "processing")
    │       ├─→ File Stored (S3/CEPH)
    │       └─→ Job Queued (Celery)
    │               │
    │               └─→ Worker Processes
    │                       │
    │                       ├─→ Extract Text
    │                       ├─→ Chunk Text
    │                       ├─→ Generate Embeddings
    │                       └─→ Store Chunks
    │                               │
    │                               └─→ Source Status: "completed"
    │
    ├─→ Create RAG Conversation
    │       │
    │       └─→ Conversation Record Created
    │               │
    │               └─→ Linked to Notebook & Source
    │
    └─→ Send Message
            │
            ├─→ Retrieve Conversation History
            ├─→ Generate Query Embedding
            ├─→ Vector Search (find similar chunks)
            ├─→ Format Context (chunks + history)
            ├─→ Generate LLM Response
            └─→ Save Response with chunk_ids
```

---

## 🔍 Key Concepts

### Notebook Scope

- **All sources** in a notebook share the same context
- **All conversations** in a notebook can access all sources
- **Chunks** are scoped to both notebook and source
- **Quizzes and Study Guides** can be generated from the entire notebook context (all sources combined) or from a specific source.
- **Notebook Intelligence**: The system can synthesize a "big picture" view of the entire notebook contents.

### Source Types

1. **PDF Documents**
   - Uploaded files
   - Processed with OCR if needed
   - Extracted text is chunked

2. **URLs**
   - Web pages/articles
   - Content scraped and processed
   - Text is chunked

3. **Text**
   - Direct text input
   - Immediately chunked
   - No processing needed

### Chunk Organization

```
Notebook (notebook-123)
  └── Source (source-456)
       ├── Chunk 1 (chunk-001) - embedding vector
       ├── Chunk 2 (chunk-002) - embedding vector
       ├── Chunk 3 (chunk-003) - embedding vector
       └── ...
```

**Chunk Properties**:
- `source_id`: Parent source
- `notebook_id`: Parent notebook (for filtering)
- `plain_text`: Chunk text content
- `embedding`: Vector embedding (for similarity search)
- `chunk_index`: Order in source

### RAG Search Flow

When user asks a question in RAG conversation:

1. **Query Embedding**: Generate embedding for user question
2. **Vector Search**: Find similar chunks using cosine similarity
3. **Filtering**: Filter by `notebook_id` and optionally `source_id`
4. **Re-ranking**: Optional re-ranking by relevance
5. **Context Assembly**: Format top chunks as context
6. **LLM Generation**: Generate response using chunks + conversation history

---

## 🎯 Use Cases

### Use Case 1: Course Material Organization

```
1. User creates notebook: "Python Programming Course"
2. User uploads multiple PDFs:
   - "Python Basics.pdf"
   - "Data Structures.pdf"
   - "Algorithms.pdf"
3. All sources are processed and chunked
4. User creates RAG conversation
5. User asks: "Explain lists in Python"
6. System finds relevant chunks from "Python Basics.pdf"
7. System generates response using chunks
```

### Use Case 2: Research Notebook

```
1. User creates notebook: "ML Research"
2. User adds multiple sources:
   - Research paper PDFs
   - Article URLs
   - Notes (text)
3. User creates multiple conversations:
   - One for each research question
4. Each conversation can access all sources
5. User asks questions across sources
```

### Use Case 3: Study Session

```
1. User creates notebook: "Exam Prep"
2. User uploads study materials
3. User creates normal chat conversation
4. User asks general questions (not source-specific)
5. System uses conversation history only
```

---

## 🔧 Technical Implementation

### Database Schema

**Notebooks Table**:
```sql
CREATE TABLE notebooks (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    language VARCHAR(50) DEFAULT 'en',
    tone VARCHAR(50) DEFAULT 'educational',
    max_context_tokens INTEGER DEFAULT 8000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

**Sources Table**:
```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    original_url TEXT,
    file_path TEXT,
    metadata_ JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

**Chunks Table**:
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    notebook_id UUID REFERENCES notebooks(id) ON DELETE CASCADE,
    plain_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding JSONB,  -- Will be replaced with vector column
    embedding_vector vector(1536),  -- pgvector column (to be added)
    metadata_ JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes

```sql
-- Notebook queries
CREATE INDEX idx_notebooks_owner ON notebooks(owner_id);
CREATE INDEX idx_notebooks_active ON notebooks(owner_id) WHERE deleted_at IS NULL;

-- Source queries
CREATE INDEX idx_sources_notebook ON sources(notebook_id);
CREATE INDEX idx_sources_active ON sources(notebook_id) WHERE deleted_at IS NULL;

-- Chunk queries (RAG search)
CREATE INDEX idx_chunks_notebook ON chunks(notebook_id);
CREATE INDEX idx_chunks_source ON chunks(source_id);
CREATE INDEX idx_chunks_embedding_vector ON chunks USING hnsw (embedding_vector vector_cosine_ops);  -- To be added
```

---

## 📝 Summary

### Notebook Flow
1. **Create** → User creates notebook
2. **Add Sources** → Documents/URLs added
3. **Process** → Sources processed and chunked
4. **Use** → Sources used in conversations/quizzes

### Source Flow
1. **Upload** → File/URL added
2. **Process** → Background job extracts text
3. **Chunk** → Text split into chunks
4. **Embed** → Chunks get vector embeddings
5. **Ready** → Source available for RAG

### Key Relationships
- **Notebook** contains **Sources**
- **Sources** contain **Chunks**
- **Conversations** reference **Notebook** and optionally **Source**
- **Chunks** are searchable via vector similarity
- **RAG** uses chunks + conversation history

### Next Steps
- Implement pgvector for vector search
- Add semantic chunking
- Implement RAG retrieval service
- Add caching for frequently accessed chunks
