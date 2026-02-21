# MindSpring FastAPI Backend - Complete cURL Commands Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** Bearer token (JWT) in `Authorization` header

---

## 🔐 Authentication Endpoints

### 1. Sign Up
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### 2. Verify OTP
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "code": "123456"
  }'
```

### 3. Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:** Returns `access_token` - save this for subsequent requests.

### 4. Refresh Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -c cookies.txt
```

### 5. Logout
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -b cookies.txt \
  -c cookies.txt
```

### 6. Resend OTP
```bash
curl -X POST "http://localhost:8000/api/v1/auth/resend-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### 7. Forgot Password
```bash
curl -X POST "http://localhost:8000/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### 8. Reset Password
```bash
curl -X POST "http://localhost:8000/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "code": "123456",
    "new_password": "NewSecurePassword123!"
  }'
```

### 9. Google OAuth Login (Redirect)
```bash
# This redirects to Google OAuth
curl -X GET "http://localhost:8000/api/v1/auth/google/login" \
  -L
```

### 10. Google OAuth Callback
```bash
curl -X GET "http://localhost:8000/api/v1/auth/google/callback?code=GOOGLE_OAUTH_CODE" \
  -H "Content-Type: application/json" \
  -c cookies.txt
```

### 11. Get Current User Info
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📓 Notebook Endpoints

### 1. Create Notebook
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Study Notebook",
    "description": "Notes for machine learning course",
    "language": "en",
    "tone": "professional",
    "max_context_tokens": 4096
  }'
```

### 2. List Notebooks
```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Get Notebook by ID
```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Update Notebook
```bash
curl -X PUT "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Notebook Title",
    "description": "Updated description",
    "language": "en",
    "tone": "casual"
  }'
```

### 5. Delete Notebook (Soft Delete)
```bash
curl -X DELETE "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Restore Notebook
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/restore" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📄 Source Endpoints

### 1. Upload Source File
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=My Document"
```

### 2. Add Source from URL
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "url=https://example.com/article" \
  -F "title=Article Title"
```

### 3. Add Source from Text
```bash
curl -X POST "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "text=This is my text content to add as a source." \
  -F "title=Text Document"
```

### 4. List Sources in Notebook
```bash
curl -X GET "http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Generate Summary from Source
```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/summary?max_length=500&style=concise" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `max_length`: Maximum length of summary (default: 500)
- `style`: Summary style - `concise`, `detailed`, or `bullet_points` (default: `concise`)

### 6. Generate Quiz from Source
```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/quiz" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Machine Learning Basics",
    "num_questions": 5,
    "difficulty": "medium"
  }'
```

**Request Body:**
- `topic`: Quiz topic/title (required)
- `num_questions`: Number of questions (default: 5)
- `difficulty`: `easy`, `medium`, or `hard` (default: `medium`)

### 7. Generate Study Guide from Source
```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/guide" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Machine Learning Fundamentals",
    "format": "structured"
  }'
```

**Request Body:**
- `topic`: Optional topic/title (defaults to source title)
- `format`: `structured`, `outline`, or `detailed` (default: `structured`)

### 8. Generate Mindmap from Source
```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/generate/mindmap?format=json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `format`: `json`, `markdown`, or `mermaid` (default: `json`)

### 9. Create Conversation from Source
```bash
curl -X POST "http://localhost:8000/api/v1/sources/SOURCE_ID/conversations" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Chat about Machine Learning",
    "mode": "chat"
  }'
```

**Request Body:**
- `title`: Optional conversation title
- `mode`: Conversation mode (default: `chat`)

---

## 💬 Chat/Conversation Endpoints

### 1. Create Conversation
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations?notebook_id=NOTEBOOK_ID&title=My%20Conversation&mode=chat&source_id=SOURCE_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `notebook_id`: Notebook ID (required)
- `title`: Optional conversation title
- `mode`: `chat` or `rag` (default: `chat`)
- `source_id`: Optional source ID for RAG mode

### 2. List Conversations
```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations?notebook_id=NOTEBOOK_ID&skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `notebook_id`: Notebook ID (required)
- `skip`: Pagination offset (default: 0)
- `limit`: Number of results (default: 100)

### 3. Get Conversation by ID
```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Send Message (with RAG)
```bash
curl -X POST "http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID/messages?content=What%20is%20machine%20learning?&role=user&use_rag=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `content`: Message content (required)
- `role`: `user` or `assistant` (default: `user`)
- `use_rag`: Enable RAG if conversation has source_id (default: `true`)

### 5. Get Messages
```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversations/CONVERSATION_ID/messages?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Number of results (default: 100)

---

## 📝 Quiz Endpoints

### 1. Create Quiz
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/?notebook_id=NOTEBOOK_ID&topic=Machine%20Learning&model=gpt-4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {
      "question1": {
        "question": "What is machine learning?",
        "options": ["A", "B", "C", "D"],
        "correct": "A"
      }
    }
  }'
```

**Query Parameters:**
- `notebook_id`: Notebook ID (required)
- `topic`: Quiz topic (required)
- `model`: Optional model name

### 2. List Quizzes
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/?notebook_id=NOTEBOOK_ID&skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `notebook_id`: Notebook ID (required)
- `skip`: Pagination offset (default: 0)
- `limit`: Number of results (default: 100)

### 3. Get Quiz by ID
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Update Quiz
```bash
curl -X PUT "http://localhost:8000/api/v1/quiz/QUIZ_ID?topic=Updated%20Topic&model=gpt-4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "questions": {
      "question1": {
        "question": "Updated question?",
        "options": ["A", "B", "C", "D"],
        "correct": "B"
      }
    }
  }'
```

**Query Parameters:**
- `topic`: Optional topic
- `model`: Optional model name

### 5. Delete Quiz
```bash
curl -X DELETE "http://localhost:8000/api/v1/quiz/QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📚 Document Endpoints

### 1. Upload Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

### 2. List Documents
```bash
curl -X GET "http://localhost:8000/api/v1/documents/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Number of results (default: 100)

### 3. Get Document by ID
```bash
curl -X GET "http://localhost:8000/api/v1/documents/DOCUMENT_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Delete Document
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/DOCUMENT_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🏥 Health Check Endpoints

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/health/"
```

### 2. Readiness Check
```bash
curl -X GET "http://localhost:8000/api/v1/health/ready"
```

### 3. Liveness Check
```bash
curl -X GET "http://localhost:8000/api/v1/health/live"
```

### 4. Root Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

---

## 📋 Usage Examples

### Complete Workflow Example

```bash
# 1. Sign up
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Password123!"}'

# 2. Verify OTP (check email for code)
curl -X POST "http://localhost:8000/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "code": "123456"}'

# 3. Login and save token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Password123!"}' \
  | jq -r '.access_token')

# 4. Create notebook
NOTEBOOK_ID=$(curl -X POST "http://localhost:8000/api/v1/notebooks/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Notebook", "description": "Test notebook"}' \
  | jq -r '.id')

# 5. Upload source file
SOURCE_ID=$(curl -X POST "http://localhost:8000/api/v1/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "title=My Document" \
  | jq -r '.data.sourceId')

# 6. Wait for processing, then generate summary
curl -X POST "http://localhost:8000/api/v1/sources/$SOURCE_ID/generate/summary?max_length=500" \
  -H "Authorization: Bearer $TOKEN"

# 7. Create conversation
CONV_ID=$(curl -X POST "http://localhost:8000/api/v1/chat/conversations?notebook_id=$NOTEBOOK_ID&title=Chat" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.id')

# 8. Send message with RAG
curl -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV_ID/messages?content=What%20is%20this%20about?&use_rag=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔑 Authentication Notes

1. **Access Token**: Valid for 30 minutes (1800 seconds)
2. **Refresh Token**: Stored in HTTP-only cookie, valid for 7 days
3. **Token Format**: `Bearer YOUR_ACCESS_TOKEN` in `Authorization` header
4. **Cookie-based Refresh**: Use `-b cookies.txt -c cookies.txt` flags for refresh token operations

---

## 📝 Notes

- Replace `YOUR_ACCESS_TOKEN` with the actual JWT token from login
- Replace `NOTEBOOK_ID`, `SOURCE_ID`, `CONVERSATION_ID`, etc. with actual IDs
- For file uploads, use `-F` flag with `@/path/to/file`
- For JSON data, use `-d` flag with JSON string
- URL-encode query parameters (spaces become `%20`, etc.)
- Use `jq` for parsing JSON responses in bash scripts

---

## 🚀 Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
EMAIL="test@example.com"
PASSWORD="TestPassword123!"

echo "1. Signing up..."
curl -X POST "$BASE_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}"

echo -e "\n\n2. Login (check email for OTP first)..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" \
  | jq -r '.access_token')

echo "Token: $TOKEN"

echo -e "\n\n3. Get current user..."
curl -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN"

echo -e "\n\n4. Health check..."
curl -X GET "$BASE_URL/health/"
```

Make it executable: `chmod +x test_api.sh`
