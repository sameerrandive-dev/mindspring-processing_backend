# MindSpring FastAPI Backend - Complete cURL Commands Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** Bearer token (JWT) in `Authorization` header

---

## 🔐 Authentication Endpoints

### 1. Sign Up
Create a new user account and trigger an OTP email.
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### 2. Verify OTP
Activate the account using the code sent via email.
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "code": "123456"
  }'
```

### 3. Login
Authenticate and receive an access token. Sets a refresh token in an HTTP-only cookie.
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### 4. Password Reset
```bash
# Forgot Password (triggers OTP)
curl -X POST "http://localhost:8000/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Reset Password (with OTP)
curl -X POST "http://localhost:8000/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "code": "123456",
    "new_password": "NewSecurePassword123!"
  }'
```

---

## 📓 Notebook Endpoints

### 1. Create Notebook
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Machine Learning Research",
    "description": "Deep learning and neural networks",
    "language": "en",
    "tone": "educational",
    "max_context_tokens": 8000
  }'
```

### 2. List & Get Notebooks
```bash
# List all
curl -X GET "http://localhost:8000/api/v1/notebooks/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get specific
curl -X GET "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Update & Delete Notebook
```bash
# Update
curl -X PUT "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'

# Delete (Soft-delete)
curl -X DELETE "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Restore
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/restore" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. AI Generation (Notebook-Wide)
Apply AI tools across ALL sources in the notebook.
```bash
# Summary
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/summary" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Quiz
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/quiz" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Ethics", "num_questions": 5}'

# Study Guide
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/guide" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Course Overview"}'
```

---

## 📄 Source Endpoints

### 1. Upload Source (Single/Bulk/URL)
```bash
# Bulk File Upload
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.txt"

# URL/Web Scraping
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "url=https://example.com"
```

### 2. AI Generation (Source-Specific)
Apply AI tools to a specific source document.
```bash
# Summary
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/summary?style=concise" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Mindmap
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Mindmap Tools
```bash
# Standalone Mindmap (from text)
curl -X POST "http://localhost:8000/api/v1/mindmap/generate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Quantum Physics Concepts"}'

# Mindmap Node Conversation (Tutor Mode)
curl -X POST "http://localhost:8000/api/v1/mindmap-node/conversations?notebook_id=NB_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id": "n1", "node_label": "Entanglement", "history_id": "h1"}'
```

---

## 💬 Chat & Conversation Endpoints

### 1. Conversation Management
```bash
# Create
curl -X POST "http://localhost:8000/api/v1/chat/conversations?notebook_id=NB_ID&title=My%20Chat" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# List
curl -X GET "http://localhost:8000/api/v1/chat/conversations?notebook_id=NB_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 2. Messaging (RAG vs Contextual)
```bash
# RAG Search (Source-aware)
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages?content=Explain%20X&use_rag=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Contextual Chat (Syntra Memory)
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages?content=Summarize%20above&use_rag=false" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. AI Artifacts from Chat
```bash
# Summary from Chat
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/summary" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Flashcards from Chat
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/flashcards" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Export Chat
```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONV_ID/export?format=markdown" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📝 Quiz Management
```bash
# List all quizzes
curl -X GET "http://localhost:8000/api/v1/quiz/?notebook_id=NB_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Update Quiz
curl -X PUT "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Updated Topic"}'
```

---

## 📂 Document Management (Standalone)
These endpoints handle direct document uploads not necessarily tied to a notebook source.
```bash
# Upload
curl -X POST "http://localhost:8000/api/v1/documents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@doc.pdf"

# List
curl -X GET "http://localhost:8000/api/v1/documents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🏥 Health & System
```bash
# Health Check
curl -X GET "http://localhost:8000/api/v1/health/"

# Readiness
curl -X GET "http://localhost:8000/readiness"
```
