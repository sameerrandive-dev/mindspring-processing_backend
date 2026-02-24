# Complete User Flow: Notebook Creation → Source Upload → Conversations & Generation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Complete Flow Diagram](#complete-flow-diagram)
3. [Step-by-Step Flow](#step-by-step-flow)
4. [All Scenarios](#all-scenarios)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Example Requests](#example-requests)

---

## Overview

This document describes the complete user journey from creating a notebook to uploading sources, having conversations, and generating learning materials (summaries, study guides, mindmaps, and flashcards).

### Key Entities

- **Notebook**: Container for organizing learning materials
- **Source**: Document, URL, or text content added to a notebook
- **Chunk**: Text segments with embeddings for RAG (Retrieval-Augmented Generation)
- **Conversation**: Chat interface for interacting with content
- **Generation Tools**: Summary, Study Guide, Mindmap, Flashcards

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER JOURNEY FLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. CREATE NOTEBOOK
   │
   ├─→ POST /api/v1/notebooks/
   │   Returns: notebook_id
   │
   ▼
2. UPLOAD SOURCE(S)
   │
   ├─→ POST /api/v1/notebooks/{notebook_id}/sources
   │   Options:
   │   - File upload (PDF, TXT, MD)
   │   - URL submission
   │   - Text paste
   │   - Bulk file upload
   │
   │   Background Processing:
   │   ├─→ Extract text from source
   │   ├─→ Chunk text (512 chars, 100 overlap)
   │   ├─→ Generate embeddings for chunks
   │   └─→ Store chunks with embeddings
   │
   │   Status: "processing" → "completed"
   │
   ▼
3. CREATE CONVERSATION
   │
   ├─→ POST /api/v1/chat/conversations
   │   Options:
   │   - General conversation (no source)
   │   - RAG conversation (with source_id)
   │   - Mode: chat, tutor, fact-checker, brainstormer
   │
   │   Returns: conversation_id
   │
   ▼
4. SEND MESSAGES
   │
   ├─→ POST /api/v1/chat/conversations/{conversation_id}/messages
   │   If RAG enabled:
   │   ├─→ Generate query embedding
   │   ├─→ Search chunks using vector similarity
   │   ├─→ Retrieve top-k relevant chunks
   │   ├─→ Build context from chunks
   │   └─→ Generate response with context
   │
   ▼
5. GENERATE LEARNING MATERIALS
   │
   ├─→ From Conversation:
   │   ├─→ Summary
   │   ├─→ Study Guide
   │   ├─→ Mindmap
   │   └─→ Flashcards
   │
   └─→ From Source:
       ├─→ Summary
       ├─→ Study Guide
       ├─→ Mindmap
       └─→ Quiz
```

---

## Step-by-Step Flow

### Step 1: Create Notebook

**Purpose**: Create a workspace for organizing learning materials

**API Endpoint**: `POST /api/v1/notebooks/`

**Request**:
```json
{
  "title": "Machine Learning Fundamentals",
  "description": "Learning ML basics and concepts",
  "language": "en",
  "tone": "educational"
}
```

**Response**:
```json
{
  "id": "notebook-123",
  "title": "Machine Learning Fundamentals",
  "description": "Learning ML basics and concepts",
  "owner_id": "user-456",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**What Happens**:
1. Notebook record created in database
2. User assigned as owner
3. Notebook ready to receive sources

---

### Step 2: Upload Source(s)

**Purpose**: Add documents, URLs, or text to the notebook for processing

**API Endpoint**: `POST /api/v1/notebooks/{notebook_id}/sources`

**Options**:

#### Option A: Upload File(s)
```bash
# Single file
curl -X POST "http://localhost:8000/api/v1/notebooks/{notebook_id}/sources" \
  -F "file=@document.pdf" \
  -F "title=ML Guide"

# Multiple files (bulk upload)
curl -X POST "http://localhost:8000/api/v1/notebooks/{notebook_id}/sources" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.txt"
```

#### Option B: Add URL
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/{notebook_id}/sources" \
  -F "url=https://example.com/article" \
  -F "title=Article Title"
```

#### Option C: Add Text
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/{notebook_id}/sources" \
  -F "text=Your text content here..." \
  -F "title=My Notes"
```

**Response**:
```json
{
  "success": true,
  "data": {
    "sourceId": "source-789",
    "sourceTitle": "ML Guide",
    "status": "processing",
    "message": "Source uploaded successfully. Processing in background..."
  }
}
```

**Background Processing Flow**:

```
1. Source Created
   ├─→ Status: "processing"
   ├─→ File stored (if uploaded)
   └─→ Background task queued

2. Text Extraction
   ├─→ PDF: Extract text (with OCR if needed)
   ├─→ URL: Scrape and extract content
   └─→ Text: Use directly

3. Chunking
   ├─→ Split text into chunks (512 characters)
   ├─→ Overlap: 100 characters
   └─→ Create chunk records

4. Embedding Generation
   ├─→ Generate embeddings for each chunk
   ├─→ Store embeddings in vector column
   └─→ Log: "Saving chunk X with embedding"

5. Completion
   ├─→ Status: "completed"
   ├─→ Chunks ready for RAG search
   └─→ Log: "All chunks saved with embeddings"
```

**Logs You'll See**:
```
🔄 Starting document processing for source source-789
📄 Document size: 50000 characters
📏 Using chunk size: 512, overlap: 100
✅ Chunking completed: Created 98 chunks
🧠 Starting embedding generation for 98 chunks
✅ Embedding generation completed: Successfully generated 98 embeddings
💾 Storing 98 chunks with embeddings in database
📝 Saving chunk 1/98 with embedding: chunk_id=..., embedding_dimension=1536
...
✅ Successfully saved 98 chunks with embeddings
🎉 Document ingestion completed successfully!
```

---

### Step 3: Create Conversation

**Purpose**: Start a chat session to interact with your content

**API Endpoint**: `POST /api/v1/chat/conversations`

**Request**:
```json
{
  "notebook_id": "notebook-123",
  "title": "Questions about ML",
  "mode": "chat",
  "source_id": "source-789"  // Optional: for RAG conversations
}
```

**Modes Available**:
- `chat`: General conversation
- `tutor`: Step-by-step learning mode
- `fact-checker`: Verify claims rigorously
- `brainstormer`: Creative idea generation

**Response**:
```json
{
  "id": "conversation-456",
  "notebook_id": "notebook-123",
  "source_id": "source-789",
  "title": "Questions about ML",
  "mode": "chat",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### Step 4: Send Messages

**Purpose**: Ask questions and get AI responses (with RAG if enabled)

**API Endpoint**: `POST /api/v1/chat/conversations/{conversation_id}/messages`

**Request**:
```json
{
  "content": "What is machine learning?",
  "role": "user",
  "use_rag": true
}
```

**RAG Flow (when use_rag=true)**:

```
1. User Message Received
   │
   ├─→ Log: "🔍 RAG Retrieval: Searching for chunks using embeddings"
   │
   ▼
2. Query Embedding Generation
   ├─→ Generate embedding for user question
   └─→ Log: "🧠 Generating embedding for query text"
   │
   ▼
3. Vector Search
   ├─→ Search chunks using cosine similarity
   ├─→ Filter by notebook_id (and source_id if provided)
   ├─→ Get top-k most similar chunks
   └─→ Log: "✅ Retrieved chunk from embeddings: chunk_id=..., similarity_score=0.85"
   │
   ▼
4. Context Building
   ├─→ Format chunks as context
   └─→ Log: "📝 Built RAG context from X chunks (saved with embeddings)"
   │
   ▼
5. LLM Response Generation
   ├─→ Generate response using chunks + conversation history
   └─→ Log: "✅ AI response generated successfully using chunks from embeddings"
   │
   ▼
6. Save Messages
   ├─→ Save user message with chunk_ids
   └─→ Save assistant response with chunk_ids
```

**Response**:
```json
{
  "id": "message-999",
  "conversation_id": "conversation-456",
  "role": "assistant",
  "content": "Machine learning is a subset of artificial intelligence...",
  "chunk_ids": ["chunk-001", "chunk-005", "chunk-012"]
}
```

**Logs You'll See**:
```
🔍 RAG Retrieval: Searching for chunks using embeddings saved during ingestion
🔎 Starting semantic search: query='What is machine learning?...'
🧠 Generating embedding for query text to search saved chunk embeddings
✅ Query embedding generated: dimension=1536, now searching chunks saved with embeddings
🔍 Vector search: Found 15 candidate chunks, filtering by similarity threshold 0.7
✅ Retrieved chunk from embeddings: chunk_id=chunk-001, similarity_score=0.9234
✅ Retrieved chunk from embeddings: chunk_id=chunk-005, similarity_score=0.8912
✅ Retrieved chunk from embeddings: chunk_id=chunk-012, similarity_score=0.8756
📊 Vector search completed: Retrieved 3 chunks from embeddings (saved during ingestion)
✅ RAG Retrieval Success: Found 3 chunks from embeddings. Chunk IDs: [chunk-001, chunk-005, chunk-012]
📝 Built RAG context from 3 chunks (saved with embeddings): total_context_length=1536 characters
🤖 Generating AI response using 3 chunks retrieved from embeddings (saved during document ingestion)
✅ AI response generated successfully using chunks from embeddings. Response length: 450 characters. Chunks used: [chunk-001, chunk-005, chunk-012]
```

---

### Step 5: Generate Learning Materials

**Purpose**: Create summaries, study guides, mindmaps, and flashcards from conversations or sources

---

## All Scenarios

### Scenario 1: Generate Summary from Conversation

**Purpose**: Create a concise summary of the conversation

**API Endpoint**: `POST /api/v1/chat/conversations/{conversation_id}/generate/summary`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/{conversation_id}/generate/summary?max_length=500&style=concise" \
  -H "Authorization: Bearer {token}"
```

**Parameters**:
- `max_length`: Maximum length in characters (default: 500)
- `style`: `concise`, `detailed`, or `bullet_points` (default: `concise`)

**Response**:
```json
{
  "conversation_id": "conversation-456",
  "summary": "This conversation covered machine learning fundamentals including supervised and unsupervised learning...",
  "style": "concise",
  "max_length": 500
}
```

**What Happens**:
1. Retrieve all messages from conversation
2. Build content from message history
3. Generate summary using LLM
4. Record in generation history
5. Return summary text

---

### Scenario 2: Generate Study Guide from Conversation

**Purpose**: Create a structured study guide from conversation content

**API Endpoint**: `POST /api/v1/chat/conversations/{conversation_id}/generate/study-guide`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/{conversation_id}/generate/study-guide?topic=Machine%20Learning&format=structured" \
  -H "Authorization: Bearer {token}"
```

**Parameters**:
- `topic`: Optional topic for the study guide
- `format`: `structured`, `outline`, or `detailed` (default: `structured`)

**Response**:
```json
{
  "conversation_id": "conversation-456",
  "topic": "Machine Learning",
  "format": "structured",
  "study_guide": "# Machine Learning Study Guide\n\n## 1. Introduction\n..."
}
```

**What Happens**:
1. Retrieve conversation messages
2. Extract key concepts and topics
3. Generate structured study guide using LLM
4. Format according to requested format
5. Record in generation history

---

### Scenario 3: Generate Mindmap from Conversation

**Purpose**: Create a visual mindmap structure from conversation

**API Endpoint**: `POST /api/v1/chat/conversations/{conversation_id}/generate/mindmap`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/{conversation_id}/generate/mindmap?format=json" \
  -H "Authorization: Bearer {token}"
```

**Parameters**:
- `format`: `json`, `mermaid`, or `markdown` (default: `json`)

**Response**:
```json
{
  "conversation_id": "conversation-456",
  "format": "json",
  "mindmap": {
    "root": "Machine Learning",
    "nodes": [
      {
        "id": "node-1",
        "label": "Supervised Learning",
        "children": [
          {"id": "node-1-1", "label": "Classification"},
          {"id": "node-1-2", "label": "Regression"}
        ]
      },
      {
        "id": "node-2",
        "label": "Unsupervised Learning",
        "children": [
          {"id": "node-2-1", "label": "Clustering"},
          {"id": "node-2-2", "label": "Dimensionality Reduction"}
        ]
      }
    ]
  }
}
```

**What Happens**:
1. Analyze conversation content
2. Extract main topics and relationships
3. Generate hierarchical mindmap structure
4. Format according to requested format
5. Record in generation history

---

### Scenario 4: Generate Flashcards from Conversation

**Purpose**: Create flashcards for studying key concepts

**API Endpoint**: `POST /api/v1/chat/conversations/{conversation_id}/generate/flashcards`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/{conversation_id}/generate/flashcards" \
  -H "Authorization: Bearer {token}"
```

**Response**:
```json
{
  "conversation_id": "conversation-456",
  "flashcards": [
    {
      "front": "What is supervised learning?",
      "back": "Supervised learning is a type of machine learning where the algorithm learns from labeled training data..."
    },
    {
      "front": "What is the difference between classification and regression?",
      "back": "Classification predicts discrete categories, while regression predicts continuous values..."
    },
    {
      "front": "What is clustering?",
      "back": "Clustering is an unsupervised learning technique that groups similar data points together..."
    }
  ]
}
```

**What Happens**:
1. Extract key concepts from conversation
2. Generate question-answer pairs
3. Format as flashcards (front/back)
4. Return list of flashcards
5. Record in generation history

---

### Scenario 5: Generate Summary from Source

**Purpose**: Create a summary directly from a source document

**API Endpoint**: `POST /api/v1/sources/{source_id}/generate/summary`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/sources/{source_id}/generate/summary?max_length=500&style=concise" \
  -H "Authorization: Bearer {token}"
```

**Response**:
```json
{
  "summary": "This document covers machine learning fundamentals...",
  "source_id": "source-789",
  "source_title": "ML Guide",
  "history_id": "history-123",
  "style": "concise"
}
```

**What Happens**:
1. Retrieve source and all its chunks
2. Combine chunk text into full content
3. Generate summary using LLM
4. Record in generation history
5. Return summary

---

### Scenario 6: Generate Study Guide from Source

**Purpose**: Create a study guide directly from a source document

**API Endpoint**: `POST /api/v1/sources/{source_id}/generate/guide`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/sources/{source_id}/generate/guide" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "topic": "Machine Learning",
    "format": "structured"
  }'
```

**Response**:
```json
{
  "id": "guide-456",
  "notebook_id": "notebook-123",
  "topic": "Machine Learning",
  "content": "# Machine Learning Study Guide\n\n## Introduction\n...",
  "model": "gpt-4",
  "version": "1.0",
  "created_at": "2024-01-15T11:00:00Z"
}
```

---

### Scenario 7: Generate Mindmap from Source

**Purpose**: Create a mindmap directly from a source document

**API Endpoint**: `POST /api/v1/sources/{source_id}/generate/mindmap`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/sources/{source_id}/generate/mindmap?format=json" \
  -H "Authorization: Bearer {token}"
```

**Response**:
```json
{
  "mindmap": {
    "root": "Machine Learning",
    "nodes": [...]
  },
  "source_id": "source-789",
  "source_title": "ML Guide",
  "format": "json",
  "history_id": "history-456"
}
```

---

### Scenario 8: Generate Quiz from Source

**Purpose**: Create a quiz directly from a source document

**API Endpoint**: `POST /api/v1/sources/{source_id}/generate/quiz`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/sources/{source_id}/generate/quiz" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "topic": "Machine Learning",
    "num_questions": 10,
    "difficulty": "intermediate"
  }'
```

**Parameters**:
- `topic`: Quiz topic
- `num_questions`: 10, 20, 30, 40, or 50 (default: 10)
- `difficulty`: `novice`, `intermediate`, `master`, `easy`, `medium`, or `hard` (default: `intermediate`)

**Response**:
```json
{
  "id": "quiz-789",
  "notebook_id": "notebook-123",
  "topic": "Machine Learning",
  "questions": [
    {
      "question": "What is supervised learning?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "..."
    },
    ...
  ],
  "model": "gpt-4",
  "version": "1.0",
  "created_at": "2024-01-15T11:30:00Z"
}
```

---

## API Endpoints Reference

### Notebook Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/notebooks/` | Create notebook |
| GET | `/api/v1/notebooks/` | List notebooks |
| GET | `/api/v1/notebooks/{id}` | Get notebook details |
| PUT | `/api/v1/notebooks/{id}` | Update notebook |
| DELETE | `/api/v1/notebooks/{id}` | Delete notebook |

### Source Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/notebooks/{notebook_id}/sources` | Upload source (file/URL/text) |
| GET | `/api/v1/notebooks/{notebook_id}/sources` | List sources in notebook |
| POST | `/api/v1/sources/{source_id}/generate/summary` | Generate summary from source |
| POST | `/api/v1/sources/{source_id}/generate/quiz` | Generate quiz from source |
| POST | `/api/v1/sources/{source_id}/generate/guide` | Generate study guide from source |
| POST | `/api/v1/sources/{source_id}/generate/mindmap` | Generate mindmap from source |
| POST | `/api/v1/sources/{source_id}/conversations` | Create conversation from source |

### Conversation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/conversations` | Create conversation |
| GET | `/api/v1/chat/conversations/{id}` | Get conversation |
| GET | `/api/v1/chat/conversations/{id}/messages` | Get messages |
| POST | `/api/v1/chat/conversations/{id}/messages` | Send message |
| POST | `/api/v1/chat/conversations/{id}/generate/summary` | Generate summary from conversation |
| POST | `/api/v1/chat/conversations/{id}/generate/study-guide` | Generate study guide from conversation |
| POST | `/api/v1/chat/conversations/{id}/generate/mindmap` | Generate mindmap from conversation |
| POST | `/api/v1/chat/conversations/{id}/generate/flashcards` | Generate flashcards from conversation |

---

## Example Requests

### Complete Workflow Example

```bash
# 1. Create Notebook
NOTEBOOK_ID=$(curl -X POST "http://localhost:8000/api/v1/notebooks/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "title": "ML Course",
    "description": "Learning ML"
  }' | jq -r '.id')

# 2. Upload Source
SOURCE_ID=$(curl -X POST "http://localhost:8000/api/v1/notebooks/$NOTEBOOK_ID/sources" \
  -F "file=@ml-guide.pdf" \
  -F "title=ML Guide" \
  -H "Authorization: Bearer {token}" | jq -r '.data.sourceId')

# 3. Wait for processing (check status)
curl -X GET "http://localhost:8000/api/v1/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer {token}"

# 4. Create Conversation
CONV_ID=$(curl -X POST "http://localhost:8000/api/v1/chat/conversations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d "{
    \"notebook_id\": \"$NOTEBOOK_ID\",
    \"source_id\": \"$SOURCE_ID\",
    \"title\": \"ML Questions\",
    \"mode\": \"chat\"
  }" | jq -r '.id')

# 5. Send Message
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "content": "What is machine learning?",
    "use_rag": true
  }'

# 6. Generate Summary from Conversation
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/generate/summary?max_length=500" \
  -H "Authorization: Bearer {token}"

# 7. Generate Study Guide from Conversation
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/generate/study-guide?topic=ML&format=structured" \
  -H "Authorization: Bearer {token}"

# 8. Generate Mindmap from Conversation
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer {token}"

# 9. Generate Flashcards from Conversation
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/generate/flashcards" \
  -H "Authorization: Bearer {token}"

# 10. Generate Summary from Source
curl -X POST "http://localhost:8000/api/v1/sources/$SOURCE_ID/generate/summary?max_length=500" \
  -H "Authorization: Bearer {token}"
```

---

## Key Logging Points

Throughout the flow, you'll see detailed logs showing:

1. **Source Processing**:
   - Chunk creation with embeddings
   - Embedding generation progress
   - Chunk storage confirmation

2. **RAG Retrieval**:
   - Query embedding generation
   - Vector search execution
   - Chunk retrieval with similarity scores
   - Context building from chunks

3. **Response Generation**:
   - AI response generation using retrieved chunks
   - Chunk IDs used in response

4. **Generation Tools**:
   - Summary/Study Guide/Mindmap/Flashcard generation
   - Content extraction and processing

---

## Summary

This complete flow enables users to:

1. ✅ Create notebooks for organizing content
2. ✅ Upload multiple sources (files, URLs, text)
3. ✅ Have RAG-powered conversations using chunks with embeddings
4. ✅ Generate summaries from conversations or sources
5. ✅ Generate study guides from conversations or sources
6. ✅ Generate mindmaps from conversations or sources
7. ✅ Generate flashcards from conversations
8. ✅ Generate quizzes from sources

All scenarios are fully logged to show the complete flow from embedding storage to output generation using those embeddings.
