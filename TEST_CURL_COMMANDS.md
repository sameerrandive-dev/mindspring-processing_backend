# Complete curl Commands for Testing Source Upload

## Prerequisites
- FastAPI server running on `http://localhost:8000`
- A verified user account (or we'll create one)

---

## Step 1: Health Check

```bash
curl -X GET http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","service":"mindspring-fastapi-backend"}
```

---

## Step 2: Sign Up (if needed)

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'
```

**Note:** If user exists, you'll get an error. That's OK - proceed to login.

---

## Step 3: Verify Email (Get OTP from database or email)

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "code": "YOUR_OTP_CODE"
  }'
```

**Note:** Replace `YOUR_OTP_CODE` with the actual OTP from database or email.

---

## Step 4: Login and Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'
```

**Save the `access_token` from the response!**

Example response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## Step 5: Create a Notebook

```bash
# Replace YOUR_TOKEN with the access_token from Step 4
curl -X POST http://localhost:8000/api/v1/notebooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Test Notebook",
    "description": "Testing source upload"
  }'
```

**Save the `id` from the response as `NOTEBOOK_ID`!**

Example response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Test Notebook",
  ...
}
```

---

## Step 6: Upload PDF File

```bash
# Replace YOUR_TOKEN and NOTEBOOK_ID
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/your/file.pdf" \
  -F "title=My PDF Document"
```

**For Windows PowerShell:**
```powershell
curl.exe -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -F "file=@C:\path\to\your\file.pdf" `
  -F "title=My PDF Document"
```

**For Windows CMD:**
```cmd
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -F "file=@C:\path\to\your\file.pdf" ^
  -F "title=My PDF Document"
```

Expected response:
```json
{
  "success": true,
  "data": {
    "sourceId": "source-uuid-here",
    "sourceTitle": "My PDF Document",
    "status": "processing",
    "message": "Source uploaded successfully. Processing in background..."
  },
  "meta": {
    "version": "v1",
    "timestamp": "2024-01-01T00:00:00"
  }
}
```

---

## Step 7: Upload Text File (.txt or .md)

```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/your/file.txt" \
  -F "title=My Text File"
```

**Windows PowerShell:**
```powershell
curl.exe -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -F "file=@C:\path\to\your\file.txt" `
  -F "title=My Text File"
```

---

## Step 8: Add URL Source (NO FILE NEEDED!)

```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "url=https://en.wikipedia.org/wiki/Python_(programming_language)" \
  -F "title=Python Wikipedia Article"
```

**Windows PowerShell:**
```powershell
curl.exe -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -F "url=https://en.wikipedia.org/wiki/Python_(programming_language)" `
  -F "title=Python Wikipedia Article"
```

---

## Step 9: Add Text Source (NO FILE NEEDED!)

```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "text=This is my test content. Machine learning is fascinating!" \
  -F "title=Test Text Document"
```

**Windows PowerShell:**
```powershell
curl.exe -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -F "text=This is my test content. Machine learning is fascinating!" `
  -F "title=Test Text Document"
```

---

## Step 10: List All Sources

```bash
curl -X GET http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Windows PowerShell:**
```powershell
curl.exe -X GET http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources `
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
[
  {
    "id": "source-uuid-1",
    "notebook_id": "notebook-uuid",
    "type": "pdf",
    "title": "My PDF Document",
    "status": "processing",
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": "source-uuid-2",
    "notebook_id": "notebook-uuid",
    "type": "url",
    "title": "Python Wikipedia Article",
    "status": "completed",
    "created_at": "2024-01-01T00:01:00"
  }
]
```

---

## Complete Example Script (Bash)

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
API_BASE="$BASE_URL/api/v1"
EMAIL="test@example.com"
PASSWORD="TestPassword123!"

echo "1. Health check..."
curl -s "$BASE_URL/health" | jq .

echo -e "\n2. Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Token: ${TOKEN:0:20}..."

echo -e "\n3. Create notebook..."
NOTEBOOK_RESPONSE=$(curl -s -X POST "$API_BASE/notebooks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Notebook","description":"Testing"}')

NOTEBOOK_ID=$(echo $NOTEBOOK_RESPONSE | jq -r '.id')
echo "Notebook ID: $NOTEBOOK_ID"

echo -e "\n4. Upload PDF..."
curl -s -X POST "$API_BASE/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf" | jq .

echo -e "\n5. Add URL source..."
curl -s -X POST "$API_BASE/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -F "url=https://en.wikipedia.org/wiki/Python_(programming_language)" | jq .

echo -e "\n6. Add text source..."
curl -s -X POST "$API_BASE/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -F "text=This is test content" \
  -F "title=Test Document" | jq .

echo -e "\n7. List sources..."
curl -s -X GET "$API_BASE/notebooks/$NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## Complete Example Script (PowerShell)

```powershell
$BASE_URL = "http://localhost:8000"
$API_BASE = "$BASE_URL/api/v1"
$EMAIL = "test@example.com"
$PASSWORD = "TestPassword123!"

Write-Host "1. Health check..."
curl.exe -s "$BASE_URL/health" | ConvertFrom-Json

Write-Host "`n2. Login..."
$loginBody = @{
    email = $EMAIL
    password = $PASSWORD
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$API_BASE/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody

$TOKEN = $loginResponse.access_token
Write-Host "Token: $($TOKEN.Substring(0,20))..."

Write-Host "`n3. Create notebook..."
$notebookBody = @{
    title = "Test Notebook"
    description = "Testing"
} | ConvertTo-Json

$notebookResponse = Invoke-RestMethod -Uri "$API_BASE/notebooks" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{Authorization = "Bearer $TOKEN"} `
    -Body $notebookBody

$NOTEBOOK_ID = $notebookResponse.id
Write-Host "Notebook ID: $NOTEBOOK_ID"

Write-Host "`n4. Upload PDF..."
$formData = @{
    file = Get-Item ".\test.pdf"
    title = "My PDF"
}
Invoke-RestMethod -Uri "$API_BASE/notebooks/$NOTEBOOK_ID/sources" `
    -Method POST `
    -Headers @{Authorization = "Bearer $TOKEN"} `
    -Form $formData

Write-Host "`n5. Add URL source..."
$urlFormData = @{
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    title = "Python Article"
}
Invoke-RestMethod -Uri "$API_BASE/notebooks/$NOTEBOOK_ID/sources" `
    -Method POST `
    -Headers @{Authorization = "Bearer $TOKEN"} `
    -Form $urlFormData

Write-Host "`n6. Add text source..."
$textFormData = @{
    text = "This is test content"
    title = "Test Document"
}
Invoke-RestMethod -Uri "$API_BASE/notebooks/$NOTEBOOK_ID/sources" `
    -Method POST `
    -Headers @{Authorization = "Bearer $TOKEN"} `
    -Form $textFormData

Write-Host "`n7. List sources..."
Invoke-RestMethod -Uri "$API_BASE/notebooks/$NOTEBOOK_ID/sources" `
    -Method GET `
    -Headers @{Authorization = "Bearer $TOKEN"}
```

---

## Quick Reference

### Replace These Variables:
- `YOUR_TOKEN` - Access token from login
- `NOTEBOOK_ID` - Notebook ID from create notebook response
- `/path/to/your/file.pdf` - Path to your PDF file

### File Types Supported:
- **PDF**: `application/pdf`
- **Text**: `text/plain`
- **Markdown**: `text/markdown`

### Max File Size:
- 50MB maximum

### Response Format:
All responses follow Next.js format:
```json
{
  "success": true,
  "data": {
    "sourceId": "...",
    "sourceTitle": "...",
    "status": "processing|completed|failed",
    "message": "..."
  },
  "meta": {
    "version": "v1",
    "timestamp": "..."
  }
}
```
