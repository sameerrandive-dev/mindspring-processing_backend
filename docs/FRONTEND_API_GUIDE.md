# 🧠 MindSpring — Frontend Developer API Guide

> **Complete reference for building the MindSpring UI against the FastAPI backend.**  
> Every endpoint, request shape, response shape, and cURL example is documented here.

---

## 📌 Quick Reference

| Item | Value |
|------|-------|
| **Base URL** | `http://localhost:8000/api/v1` |
| **Auth Type** | Bearer JWT (in `Authorization` header) |
| **Token Expiry** | Access: **30 min** · Refresh: **7 days** (HTTP-only cookie) |
| **Interactive Docs** | `http://localhost:8000/docs` (Swagger UI) |
| **Alt Docs** | `http://localhost:8000/redoc` |
| **Content-Type** | `application/json` for JSON bodies; `multipart/form-data` for file uploads |

---

## 📐 Authentication Flow Overview

```
1. POST /auth/signup          → Create account, OTP sent to email
2. POST /auth/verify-otp      → Verify email with OTP code
3. POST /auth/login           → Get access_token + refresh_token (cookie)
4. Use access_token as Bearer in all protected requests
5. POST /auth/refresh         → Silently refresh when access_token expires
6. POST /auth/logout          → Revoke session
```

---

## 🔐 Authentication Endpoints

### 1. Sign Up
**`POST /auth/signup`** — Creates account, sends OTP email.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response `201`:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "is_active": false,
  "is_verified": false,
  "created_at": "2024-01-15T10:00:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
```

---

### 2. Verify OTP
**`POST /auth/verify-otp`** — Activates the account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response `200`:**
```json
{ "message": "Email verified successfully" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "code": "123456"}'
```

---

### 3. Resend OTP
**`POST /auth/resend-otp`** — Resends OTP to email.

**Request Body:**
```json
{ "email": "user@example.com" }
```

**Response `200`:**
```json
{ "message": "OTP resent successfully" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/resend-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

### 4. Login
**`POST /auth/login`** — Returns `access_token`; sets `refresh_token` as HTTP-only cookie.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> ⚠️ **Store `access_token` in memory** (not localStorage). The refresh token is set automatically as a secure HTTP-only cookie.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
```

---

### 5. Refresh Token
**`POST /auth/refresh`** — Issues new access token using the HTTP-only cookie.

> No request body needed — browser sends cookie automatically.

**Response `200`:** Same shape as Login response.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -b cookies.txt
```

---

### 6. Logout
**`POST /auth/logout`** — Revokes session, clears cookie. Requires auth.

**Response `200`:**
```json
{ "message": "Logged out successfully" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -b cookies.txt
```

---

### 7. Get Current User
**`GET /auth/me`** — Returns the authenticated user's profile.

**Response `200`:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "is_active": true,
  "is_verified": true,
  "created_at": "2024-01-15T10:00:00Z"
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 8. Forgot Password
**`POST /auth/forgot-password`** — Sends password reset OTP.

**Request Body:**
```json
{ "email": "user@example.com" }
```

**Response `200`:**
```json
{ "message": "If the email exists, a password reset code has been sent" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

### 9. Reset Password
**`POST /auth/reset-password`** — Resets password using OTP.

**Request Body:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "NewSecurePassword123!"
}
```

**Response `200`:**
```json
{ "message": "Password reset successfully" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "code": "123456", "new_password": "NewPass123!"}'
```

---

### 10. Google OAuth
**`GET /auth/google/login`** — Redirects browser to Google consent screen.

> Use this as a direct `<a href>` or `window.location.href`. Not a fetch call.

```
http://localhost:8000/api/v1/auth/google/login
```

**Callback** (`/auth/google/callback`) is handled server-side and returns:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "...", "email": "...", "is_active": true }
}
```

---

## 📓 Notebook Endpoints

> All notebook endpoints require `Authorization: Bearer TOKEN`.

### 1. Create Notebook
**`POST /notebooks/`**

**Request Body:**
```json
{
  "title": "Machine Learning Research",
  "description": "Deep learning and neural networks",
  "language": "en",
  "tone": "educational",
  "max_context_tokens": 8000
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | ✅ | |
| `description` | string | ❌ | |
| `language` | string | ❌ | Default: `"en"` |
| `tone` | string | ❌ | e.g. `"educational"`, `"casual"` |
| `max_context_tokens` | int | ❌ | Default: `8000` |

**Response `201`:**
```json
{
  "id": "notebook-uuid",
  "title": "Machine Learning Research",
  "description": "Deep learning and neural networks",
  "language": "en",
  "tone": "educational",
  "max_context_tokens": 8000,
  "owner_id": "user-uuid",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Machine Learning Research",
    "description": "Deep learning and neural networks",
    "language": "en",
    "tone": "educational"
  }'
```

---

### 2. List Notebooks
**`GET /notebooks/?skip=0&limit=100`**

**Response `200`:**
```json
{
  "notebooks": [
    {
      "id": "notebook-uuid",
      "title": "Machine Learning Research",
      "description": "...",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get Notebook by ID
**`GET /notebooks/{notebook_id}`**

**Response `200`:** Same shape as Create Notebook response.

```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Update Notebook
**`PUT /notebooks/{notebook_id}`** — All fields optional (partial update).

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "tone": "formal"
}
```

**Response `200`:** Updated notebook object.

```bash
curl -X PUT "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

---

### 5. Delete Notebook (Soft Delete)
**`DELETE /notebooks/{notebook_id}`**

**Response `200`:**
```json
{ "message": "Notebook deleted successfully" }
```

```bash
curl -X DELETE "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 6. Restore Notebook
**`POST /notebooks/{notebook_id}/restore`**

**Response `200`:**
```json
{ "message": "Notebook restored successfully" }
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/restore" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. Generate Summary (All Sources in Notebook)
**`POST /notebooks/{notebook_id}/generate/summary?max_length=1000&style=detailed`**

| Query Param | Default | Options |
|-------------|---------|---------|
| `max_length` | `1000` | any integer |
| `style` | `"detailed"` | `"concise"`, `"detailed"`, `"bullet_points"` |

**Response `200`:**
```json
{
  "summary": "This notebook covers...",
  "notebook_id": "notebook-uuid",
  "style": "detailed",
  "history_id": "history-uuid"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/summary?max_length=1000&style=detailed" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 8. Generate Quiz (All Sources in Notebook)
**`POST /notebooks/{notebook_id}/generate/quiz`**

**Request Body:**
```json
{
  "topic": "AI Ethics",
  "num_questions": 10,
  "difficulty": "intermediate"
}
```

| Field | Required | Allowed Values |
|-------|----------|----------------|
| `topic` | ✅ | any string |
| `num_questions` | ❌ | `10`, `20`, `30`, `40`, `50` |
| `difficulty` | ❌ | `"novice"`, `"intermediate"`, `"master"`, `"easy"`, `"medium"`, `"hard"` |

**Response `200`:**
```json
{
  "id": "quiz-uuid",
  "notebook_id": "notebook-uuid",
  "topic": "AI Ethics",
  "questions": [
    {
      "question": "What is...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Because..."
    }
  ],
  "model": "model-name",
  "version": 1,
  "created_at": "2024-01-15T11:00:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/quiz" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Ethics", "num_questions": 10, "difficulty": "intermediate"}'
```

---

### 9. Generate Study Guide (All Sources in Notebook)
**`POST /notebooks/{notebook_id}/generate/guide`**

**Request Body:**
```json
{
  "topic": "Course Overview",
  "format": "structured"
}
```

| Field | Required | Options |
|-------|----------|---------|
| `topic` | ❌ | any string |
| `format` | ❌ | `"structured"`, `"outline"`, `"detailed"` |

**Response `200`:**
```json
{
  "id": "guide-uuid",
  "notebook_id": "notebook-uuid",
  "topic": "Course Overview",
  "content": "# Study Guide\n\n## Introduction\n...",
  "model": "model-name",
  "version": 1,
  "created_at": "2024-01-15T11:30:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/guide" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Course Overview", "format": "structured"}'
```

---

### 10. Generate Mindmap (All Sources in Notebook)
**`POST /notebooks/{notebook_id}/generate/mindmap?format=json`**

| Query Param | Default | Options |
|-------------|---------|---------|
| `format` | `"json"` | `"json"`, `"mermaid"`, `"markdown"` |

**Response `200`:**
```json
{
  "mindmap": {
    "root": "Machine Learning",
    "nodes": [
      {
        "id": "node-1",
        "label": "Supervised Learning",
        "children": [
          { "id": "node-1-1", "label": "Classification" },
          { "id": "node-1-2", "label": "Regression" }
        ]
      }
    ]
  },
  "notebook_id": "notebook-uuid",
  "format": "json",
  "history_id": "history-uuid"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📄 Source Endpoints

### 1. Upload Source(s) to Notebook
**`POST /notebooks/{notebook_id}/sources`** — `multipart/form-data`

Accepts **one of**: files, URL, or text.

#### Option A: Single File Upload
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf"
```

#### Option B: Bulk File Upload (Multiple Files)
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.txt" \
  -F "files=@notes.md"
```

#### Option C: URL / Web Scraping
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "url=https://example.com/article"
```

#### Option D: Paste Text
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "text=Your text content here..." \
  -F "title=My Notes"
```

**Allowed file types:** `.pdf`, `.txt`, `.md` · **Max file size:** 50 MB

**Response for single/URL/text `201`:**
```json
{
  "success": true,
  "data": {
    "sourceId": "source-uuid",
    "sourceTitle": "document.pdf",
    "status": "processing",
    "message": "Source uploaded successfully. Processing in background..."
  },
  "meta": {
    "version": "v1",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

**Response for bulk upload `201`:**
```json
{
  "success": true,
  "data": [
    { "id": "source-uuid-1", "title": "doc1.pdf", "status": "processing" },
    { "id": "source-uuid-2", "title": "doc2.txt", "status": "processing" }
  ],
  "meta": { "count": 2, "timestamp": "2024-01-15T10:00:00Z" }
}
```

> ⚠️ **Source processing is asynchronous.** Poll `GET /notebooks/{id}/sources` to check `status` → `"processing"` → `"completed"` (or `"failed"`).

---

### 2. List Sources in Notebook
**`GET /notebooks/{notebook_id}/sources`**

**Response `200`:**
```json
[
  {
    "id": "source-uuid",
    "notebook_id": "notebook-uuid",
    "type": "pdf",
    "title": "document.pdf",
    "original_url": null,
    "file_path": "user-id/notebooks/nb-id/sources/...",
    "status": "completed",
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

| Status Value | Meaning |
|-------------|---------|
| `processing` | Background task running |
| `completed` | Ready for AI generation |
| `failed` | Processing error |

```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Generate Summary from Source
**`POST /sources/{source_id}/generate/summary?max_length=500&style=concise`**

| Query Param | Default | Options |
|-------------|---------|---------|
| `max_length` | `500` | any integer |
| `style` | `"concise"` | `"concise"`, `"detailed"`, `"bullet_points"` |

**Response `200`:**
```json
{
  "summary": "This document covers...",
  "source_id": "source-uuid",
  "source_title": "document.pdf",
  "history_id": "history-uuid",
  "style": "concise"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/summary?max_length=500&style=concise" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Generate Quiz from Source
**`POST /sources/{source_id}/generate/quiz`**

**Request Body:**
```json
{
  "topic": "Machine Learning",
  "num_questions": 10,
  "difficulty": "intermediate"
}
```

**Response `200`:** Same shape as notebook quiz response.

```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/quiz" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Machine Learning", "num_questions": 10, "difficulty": "intermediate"}'
```

---

### 5. Generate Study Guide from Source
**`POST /sources/{source_id}/generate/guide`**

**Request Body:**
```json
{
  "topic": "Machine Learning",
  "format": "structured"
}
```

**Response `200`:** Same shape as notebook study guide response.

```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/guide" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Machine Learning", "format": "structured"}'
```

---

### 6. Generate Mindmap from Source
**`POST /sources/{source_id}/generate/mindmap?format=json`**

**Response `200`:**
```json
{
  "mindmap": { "root": "...", "nodes": [...] },
  "source_id": "source-uuid",
  "source_title": "document.pdf",
  "format": "json",
  "history_id": "history-uuid"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. Create Conversation from Source
**`POST /sources/{source_id}/conversations`**

| Query Param | Default | Notes |
|-------------|---------|-------|
| `title` | `"Chat about {source.title}"` | optional |
| `mode` | `"chat"` | `"chat"`, `"tutor"`, `"fact-checker"`, `"brainstormer"` |

**Response `200`:**
```json
{
  "id": "conversation-uuid",
  "notebook_id": "notebook-uuid",
  "source_id": "source-uuid",
  "title": "Chat about document.pdf",
  "mode": "chat",
  "created_at": "2024-01-15T10:00:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/conversations?mode=tutor" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🗺️ Mindmap Tools

### 1. Generate Mindmap from Free Text (No Source Needed)
**`POST /mindmap/generate`**

**Request Body:**
```json
{
  "text": "Quantum Physics: wave-particle duality, superposition, entanglement",
  "format": "json"
}
```

| Field | Required | Options |
|-------|----------|---------|
| `text` | ✅ | any string |
| `format` | ❌ | `"json"`, `"mermaid"`, `"markdown"` |

**Response `200`:**
```json
{
  "mindmap": { "root": "Quantum Physics", "nodes": [...] },
  "source_id": null,
  "source_title": null,
  "format": "json",
  "history_id": "history-uuid"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/mindmap/generate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Quantum Physics concepts", "format": "json"}'
```

---

### 2. Create Conversation from Mindmap Node (Interactive Threading)
**`POST /mindmap-node/conversations?notebook_id=NB_ID&node_id=n1&node_label=Entanglement&history_id=h1`**

> Creates a `"tutor"` mode conversation anchored to a specific node.

| Query Param | Required | Notes |
|-------------|----------|-------|
| `notebook_id` | ✅ | parent notebook |
| `node_id` | ✅ | ID of the clicked node |
| `node_label` | ✅ | label text of the node |
| `history_id` | ✅ | the mindmap's `history_id` |
| `title` | ❌ | defaults to `"Exploring: {node_label}"` |

**Response `200`:**
```json
{
  "id": "conversation-uuid",
  "notebook_id": "notebook-uuid",
  "node_id": "n1",
  "node_label": "Entanglement",
  "mindmap_history_id": "h1",
  "mode": "tutor",
  "title": "Exploring: Entanglement",
  "created_at": "2024-01-15T10:00:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/mindmap-node/conversations?notebook_id=NB_ID&node_id=n1&node_label=Entanglement&history_id=h1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 💬 Chat & Conversation Endpoints

### 1. Create Conversation
**`POST /chat/conversations?notebook_id=NB_ID&title=My%20Chat&mode=chat`**

| Query Param | Required | Options |
|-------------|----------|---------|
| `notebook_id` | ✅ | |
| `title` | ❌ | defaults to timestamp |
| `mode` | ❌ | `"chat"`, `"tutor"`, `"fact-checker"`, `"brainstormer"` |
| `source_id` | ❌ | links conversation to a specific source for RAG |

**Response `200`:**
```json
{
  "id": "conversation-uuid",
  "notebook_id": "notebook-uuid",
  "title": "My Chat",
  "mode": "chat",
  "created_at": "2024-01-15T10:30:00Z"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations?notebook_id=NB_ID&title=My%20Chat&mode=chat" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 2. List Conversations
**`GET /chat/conversations?notebook_id=NB_ID&skip=0&limit=100`**

**Response `200`:**
```json
{
  "conversations": [
    {
      "id": "conversation-uuid",
      "title": "My Chat",
      "mode": "chat",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:00:00Z"
    }
  ],
  "total": 1
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations?notebook_id=NB_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get Conversation (with Messages)
**`GET /chat/conversations/{conversation_id}`**

**Response `200`:**
```json
{
  "id": "conversation-uuid",
  "notebook_id": "notebook-uuid",
  "title": "My Chat",
  "mode": "chat",
  "source_id": "source-uuid-or-null",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "What is machine learning?",
      "chunk_ids": [],
      "created_at": "2024-01-15T10:31:00Z"
    },
    {
      "id": "message-uuid-2",
      "role": "assistant",
      "content": "Machine learning is...",
      "chunk_ids": ["chunk-001", "chunk-005"],
      "created_at": "2024-01-15T10:31:05Z"
    }
  ]
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONV_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Send Message
**`POST /chat/conversations/{conversation_id}/messages`**

| Query Param | Default | Notes |
|-------------|---------|-------|
| `content` | required | the user's message text |
| `role` | `"user"` | `"user"` or `"assistant"` |
| `use_rag` | `true` | `true` = vector search + AI; `false` = contextual chat only |

> **`use_rag=true`**: Searches chunk embeddings, retrieves top-k relevant chunks, builds context, and generates AI response.  
> **`use_rag=false`**: Uses conversation history only (Syntra Memory mode).

**Response `200`:**
```json
{
  "id": "message-uuid",
  "conversation_id": "conversation-uuid",
  "role": "assistant",
  "content": "Machine learning is a subset of AI that...",
  "chunk_ids": ["chunk-001", "chunk-005", "chunk-012"],
  "created_at": "2024-01-15T10:31:05Z"
}
```

```bash
# RAG-powered message
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages?content=What%20is%20ML%3F&use_rag=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Contextual chat (no RAG)
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages?content=Summarize%20above&use_rag=false" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 5. Get Messages
**`GET /chat/conversations/{conversation_id}/messages?skip=0&limit=100`**

**Response `200`:**
```json
{
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "What is ML?",
      "chunk_ids": [],
      "created_at": "2024-01-15T10:31:00Z"
    }
  ],
  "total": 1
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 6. Generate Summary from Conversation
**`POST /chat/conversations/{conversation_id}/generate/summary?max_length=500&style=concise`**

**Response `200`:**
```json
{
  "conversation_id": "conversation-uuid",
  "summary": "This conversation covered...",
  "style": "concise",
  "max_length": 500
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/summary?max_length=500&style=concise" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. Generate Quiz from Conversation
**`POST /chat/conversations/{conversation_id}/generate/quiz?topic=ML&num_questions=5&difficulty=medium`**

**Response `200`:**
```json
{
  "conversation_id": "conversation-uuid",
  "topic": "ML",
  "quiz": [...],
  "num_questions": 5,
  "difficulty": "medium"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/quiz?topic=ML&num_questions=5&difficulty=medium" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 8. Generate Study Guide from Conversation
**`POST /chat/conversations/{conversation_id}/generate/study-guide?topic=ML&format=structured`**

**Response `200`:**
```json
{
  "conversation_id": "conversation-uuid",
  "topic": "ML",
  "format": "structured",
  "study_guide": "# ML Study Guide\n\n## Introduction\n..."
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/study-guide?topic=ML&format=structured" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 9. Generate Mindmap from Conversation
**`POST /chat/conversations/{conversation_id}/generate/mindmap?format=json`**

**Response `200`:**
```json
{
  "conversation_id": "conversation-uuid",
  "format": "json",
  "mindmap": { "root": "...", "nodes": [...] }
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 10. Generate Flashcards from Conversation
**`POST /chat/conversations/{conversation_id}/generate/flashcards`**

**Response `200`:**
```json
{
  "conversation_id": "conversation-uuid",
  "topic": null,
  "flashcards": [
    {
      "front": "What is supervised learning?",
      "back": "Supervised learning is a type of ML where the model trains on labeled data..."
    }
  ]
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONV_ID/generate/flashcards" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 11. Export Conversation
**`GET /chat/conversations/{conversation_id}/export?format=json`**

| Format | Returns |
|--------|---------|
| `json` | Full structured object |
| `text` | Plain text transcript |
| `markdown` | Markdown formatted transcript |

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONV_ID/export?format=markdown" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📝 Quiz Endpoints

### 1. Create Quiz (Manual)
**`POST /quiz/?notebook_id=NB_ID&topic=ML`**

> The AI-generated quiz via `/notebooks/.../generate/quiz` or `/sources/.../generate/quiz` is preferred. Use this endpoint only when manually inserting quiz data.

```bash
curl -X POST "http://localhost:8000/api/v1/quiz/?notebook_id=NB_ID&topic=ML" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"questions": {"q1": {"question": "...", "answer": "..."}}}'
```

---

### 2. List Quizzes
**`GET /quiz/?notebook_id=NB_ID&skip=0&limit=100`**

**Response `200`:**
```json
{
  "quizzes": [
    {
      "id": "quiz-uuid",
      "topic": "Machine Learning",
      "model": "model-name",
      "version": 1,
      "created_at": "2024-01-15T11:00:00Z"
    }
  ],
  "total": 1
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/quiz/?notebook_id=NB_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get Quiz by ID
**`GET /quiz/{quiz_id}`**

**Response `200`:** Full quiz with `questions` array.

```bash
curl -X GET "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Update Quiz
**`PUT /quiz/{quiz_id}`**

```bash
curl -X PUT "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Updated Topic"}'
```

---

### 5. Delete Quiz
**`DELETE /quiz/{quiz_id}`**

**Response `200`:**
```json
{ "message": "Quiz deleted successfully" }
```

```bash
curl -X DELETE "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📂 Document Endpoints (Standalone)

> These are standalone document records, **separate** from notebook sources. Used for direct file upload without notebook context.

### 1. Upload Document
**`POST /documents/`** — `multipart/form-data`

**Allowed types:** `application/pdf`, `application/msword`, `.docx`, `text/plain`, `text/markdown`

**Response `200`:**
```json
{
  "document_id": "doc-uuid",
  "filename": "document.pdf",
  "status": "pending",
  "job_id": "job-uuid",
  "message": "Document uploaded successfully and processing started"
}
```

```bash
curl -X POST "http://localhost:8000/api/v1/documents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf"
```

---

### 2. List Documents
**`GET /documents/?skip=0&limit=100`**

**Response `200`:**
```json
{
  "documents": [
    {
      "id": "doc-uuid",
      "filename": "document.pdf",
      "size": 1024000,
      "status": "pending",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:01:00Z"
    }
  ],
  "total": 1
}
```

```bash
curl -X GET "http://localhost:8000/api/v1/documents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get Document by ID
**`GET /documents/{document_id}`**

```bash
curl -X GET "http://localhost:8000/api/v1/documents/DOC_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Delete Document
**`DELETE /documents/{document_id}`**

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/DOC_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🏥 Health & System Endpoints

> No auth required.

```bash
# Liveness (is the server running?)
curl http://localhost:8000/health

# Readiness (is the server ready to serve traffic?)
curl http://localhost:8000/readiness

# v1 Health
curl http://localhost:8000/api/v1/health/

# v1 Readiness
curl http://localhost:8000/api/v1/health/ready

# v1 Liveness
curl http://localhost:8000/api/v1/health/live
```

**All return:**
```json
{ "status": "healthy", "service": "mindspring-fastapi-backend" }
```

---

## 🗺️ Complete Endpoint Map

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/signup` | ❌ | Register user |
| `POST` | `/auth/verify-otp` | ❌ | Verify email |
| `POST` | `/auth/resend-otp` | ❌ | Resend OTP |
| `POST` | `/auth/login` | ❌ | Login → access token |
| `POST` | `/auth/refresh` | Cookie | Refresh access token |
| `POST` | `/auth/logout` | ✅ | Logout |
| `GET` | `/auth/me` | ✅ | Get current user |
| `POST` | `/auth/forgot-password` | ❌ | Request reset OTP |
| `POST` | `/auth/reset-password` | ❌ | Reset password |
| `GET` | `/auth/google/login` | ❌ | Google OAuth redirect |
| `GET` | `/auth/google/callback` | ❌ | Google OAuth callback |
| | | | |
| `POST` | `/notebooks/` | ✅ | Create notebook |
| `GET` | `/notebooks/` | ✅ | List notebooks |
| `GET` | `/notebooks/{id}` | ✅ | Get notebook |
| `PUT` | `/notebooks/{id}` | ✅ | Update notebook |
| `DELETE` | `/notebooks/{id}` | ✅ | Soft delete notebook |
| `POST` | `/notebooks/{id}/restore` | ✅ | Restore notebook |
| `POST` | `/notebooks/{id}/generate/summary` | ✅ | Summary (all sources) |
| `POST` | `/notebooks/{id}/generate/quiz` | ✅ | Quiz (all sources) |
| `POST` | `/notebooks/{id}/generate/guide` | ✅ | Study guide (all sources) |
| `POST` | `/notebooks/{id}/generate/mindmap` | ✅ | Mindmap (all sources) |
| | | | |
| `POST` | `/notebooks/{id}/sources` | ✅ | Upload source(s) |
| `GET` | `/notebooks/{id}/sources` | ✅ | List sources |
| `POST` | `/sources/{id}/generate/summary` | ✅ | Summary (one source) |
| `POST` | `/sources/{id}/generate/quiz` | ✅ | Quiz (one source) |
| `POST` | `/sources/{id}/generate/guide` | ✅ | Study guide (one source) |
| `POST` | `/sources/{id}/generate/mindmap` | ✅ | Mindmap (one source) |
| `POST` | `/sources/{id}/conversations` | ✅ | Chat from source |
| | | | |
| `POST` | `/mindmap/generate` | ✅ | Mindmap from free text |
| `POST` | `/mindmap-node/conversations` | ✅ | Thread from mindmap node |
| | | | |
| `POST` | `/chat/conversations` | ✅ | Create conversation |
| `GET` | `/chat/conversations` | ✅ | List conversations |
| `GET` | `/chat/conversations/{id}` | ✅ | Get conversation + messages |
| `POST` | `/chat/conversations/{id}/messages` | ✅ | Send message (RAG or context) |
| `GET` | `/chat/conversations/{id}/messages` | ✅ | Get messages |
| `POST` | `/chat/conversations/{id}/generate/summary` | ✅ | Summary from chat |
| `POST` | `/chat/conversations/{id}/generate/quiz` | ✅ | Quiz from chat |
| `POST` | `/chat/conversations/{id}/generate/study-guide` | ✅ | Study guide from chat |
| `POST` | `/chat/conversations/{id}/generate/mindmap` | ✅ | Mindmap from chat |
| `POST` | `/chat/conversations/{id}/generate/flashcards` | ✅ | Flashcards from chat |
| `GET` | `/chat/conversations/{id}/export` | ✅ | Export conversation |
| | | | |
| `POST` | `/quiz/` | ✅ | Create quiz (manual) |
| `GET` | `/quiz/` | ✅ | List quizzes |
| `GET` | `/quiz/{id}` | ✅ | Get quiz |
| `PUT` | `/quiz/{id}` | ✅ | Update quiz |
| `DELETE` | `/quiz/{id}` | ✅ | Delete quiz |
| | | | |
| `POST` | `/documents/` | ✅ | Upload standalone document |
| `GET` | `/documents/` | ✅ | List documents |
| `GET` | `/documents/{id}` | ✅ | Get document |
| `DELETE` | `/documents/{id}` | ✅ | Delete document |
| | | | |
| `GET` | `/health/` | ❌ | Health check |
| `GET` | `/health/ready` | ❌ | Readiness check |
| `GET` | `/health/live` | ❌ | Liveness check |

---

## 🔁 Complete End-to-End Workflow (Shell Script)

```bash
BASE="http://localhost:8000/api/v1"

# 1. Sign up
curl -X POST "$BASE/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@test.com","password":"Test1234!"}'

# 2. Verify OTP (check email for code)
curl -X POST "$BASE/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@test.com","code":"123456"}'

# 3. Login → save token
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"dev@test.com","password":"Test1234!"}' | jq -r '.access_token')

AUTH="Authorization: Bearer $TOKEN"

# 4. Create notebook
NB=$(curl -s -X POST "$BASE/notebooks/" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"ML Research","language":"en"}' | jq -r '.id')

# 5. Upload source
curl -X POST "$BASE/notebooks/$NB/sources" \
  -H "$AUTH" -F "files=@notes.pdf"

# 6. Wait for source processing, then list sources
curl -s -X GET "$BASE/notebooks/$NB/sources" -H "$AUTH"

SRC="YOUR_SOURCE_ID_FROM_STEP_6"

# 7. Create conversation
CONV=$(curl -s -X POST "$BASE/chat/conversations?notebook_id=$NB&mode=chat" \
  -H "$AUTH" | jq -r '.id')

# 8. Send RAG message
curl -X POST "$BASE/chat/conversations/$CONV/messages?content=Explain+the+key+concepts&use_rag=true" \
  -H "$AUTH"

# 9. Generate mindmap from source
curl -X POST "$BASE/sources/$SRC/generate/mindmap?format=json" -H "$AUTH"

# 10. Generate quiz from source
curl -X POST "$BASE/sources/$SRC/generate/quiz" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"topic":"Key Concepts","num_questions":10,"difficulty":"intermediate"}'

# 11. Generate flashcards from conversation
curl -X POST "$BASE/chat/conversations/$CONV/generate/flashcards" -H "$AUTH"

# 12. Export conversation as markdown
curl -X GET "$BASE/chat/conversations/$CONV/export?format=markdown" -H "$AUTH"
```

---

## ⚠️ Error Reference

All errors follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Code | Meaning | Common Cause |
|-----------|---------|--------------|
| `400` | Bad Request | Invalid input, unsupported file type |
| `401` | Unauthorized | Missing or expired `access_token` |
| `403` | Forbidden | Accessing another user's resource |
| `404` | Not Found | Resource ID doesn't exist |
| `422` | Validation Error | Request body missing required fields |
| `429` | Too Many Requests | Rate limit exceeded |
| `503` | Service Unavailable | Google OAuth not configured |
| `500` | Internal Server Error | Unexpected backend error |

---

## 💡 Frontend Implementation Tips

### Token Management
```javascript
// After login — store in memory, NOT localStorage
let accessToken = response.access_token;

// Refresh silently before expiry (token expires in 30 min)
setInterval(async () => {
  const res = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' });
  const data = await res.json();
  accessToken = data.access_token;
}, 25 * 60 * 1000); // every 25 min
```

### Source Upload with Status Polling
```javascript
// After uploading source, poll until status === 'completed'
async function waitForSourceReady(notebookId, sourceId) {
  while (true) {
    const res = await fetch(`/api/v1/notebooks/${notebookId}/sources`, {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    const sources = await res.json();
    const source = sources.find(s => s.id === sourceId);
    if (source?.status === 'completed') return source;
    if (source?.status === 'failed') throw new Error('Source processing failed');
    await new Promise(r => setTimeout(r, 3000)); // poll every 3s
  }
}
```

### Sending a Chat Message
```javascript
const res = await fetch(
  `/api/v1/chat/conversations/${convId}/messages?content=${encodeURIComponent(text)}&use_rag=true`,
  { method: 'POST', headers: { Authorization: `Bearer ${accessToken}` } }
);
const message = await res.json(); // { role: 'assistant', content: '...', chunk_ids: [...] }
```

---

*Generated: February 2026 · MindSpring FastAPI Backend v1*
