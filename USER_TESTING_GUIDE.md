# 🧪 Multi-Source Notebook Testing Guide

This guide describes the end-to-end flow to test MindSpring's core product: **The Collective Learning Notebook**. Follow these steps to verify how multiple sources can be combined into a single intelligent workspace.

---

## 🏗️ 1. Setup & Authentication
Before starting, ensure your server is running (`uvicorn app.main:app`).

### A. Health Check
```bash
curl -X GET http://localhost:8000/health
```

### B. Login & Token
Obtain your `access_token` (see `TEST_CURL_COMMANDS.md` for signup/login details).
```bash
# Save this in your terminal environment
export TOKEN="your_jwt_token_here"
```

---

## 📓 2. Create Your Workspace
Create a notebook that will serve as the container for your multiple sources.

```bash
curl -X POST http://localhost:8000/api/v1/notebooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quantum Physics Research",
    "description": "Aggregating documents and articles about Quantum Mechanics"
  }'
```
*   **Save the `id` from the response as `NOTEBOOK_ID`.**

---

## 📥 3. Upload Multiple Sources
Add different types of content to your notebook to test multi-source indexing.

### Source A: A Research PDF
```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/quantum_primer.pdf" \
  -F "title=Quantum Primer PDF"
```

### Source B: A Wikipedia URL
```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer $TOKEN" \
  -F "url=https://en.wikipedia.org/wiki/Quantum_entanglement" \
  -F "title=Entanglement Wiki"
```

### Source C: Personal Notes (Raw Text)
```bash
curl -X POST http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer $TOKEN" \
  -F "text=Schrödinger's cat is a thought experiment that illustrates the paradox of superposition." \
  -F "title=Superposition Notes"
```

---

## 🔍 4. Verification
Check that all sources have been processed and indexed.

```bash
curl -X GET http://localhost:8000/api/v1/notebooks/NOTEBOOK_ID/sources \
  -H "Authorization: Bearer $TOKEN"
```
*   Ensure `status` for all sources is `"completed"`.

---

## 💬 5. Unified RAG Chat (Multi-Source Learning)
This is where you test the AI's ability to "connect the dots" across your entire notebook library.

### A. Create a Notebook-Wide Conversation
*   **Crucial**: Do NOT provide a `source_id` here. This makes it a "Notebook Conversation" which searches all sources.

```bash
curl -X POST http://localhost:8000/api/v1/chat/conversations?notebook_id=NOTEBOOK_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Holistic Quantum Q&A",
    "mode": "rag"
  }'
```
*   **Save the `id` from the response as `CONV_ID`.**

### B. Ask a Cross-Source Question
Ask something that requires info from the PDF, the Wiki, and your notes.
```bash
curl -X POST http://localhost:8000/api/v1/chat/conversations/CONV_ID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Summarize entanglement using the Wiki source and explain how it relates to the superposition paradox mentioned in my notes.",
    "use_rag": true
  }'
```
*   **Check the result**: The AI should synthesize info from multiple sources and list multiple `chunk_ids` in its metadata.

---

## 📝 6. Syntra Pulse (High-Volume Assessments)
Test MindSpring's ability to generate rigorous assessments with custom volumes.

### A. 20-Question Intermediate Pulse
```bash
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/generate/quiz \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Quantum Foundations",
    "num_questions": 20,
    "difficulty": "medium"
  }'
```

### B. 50-Question Master Class Pulse
```bash
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/generate/quiz \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Advanced Quantum Synthesis",
    "num_questions": 50,
    "difficulty": "hard"
  }'
```

---

## 🧠 7. Interactive Mindmap Nodes
Test the ability to pivot from a visual concept to a deep-dive conversation thread.

### A. Generate the Map
```bash
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/generate/mindmap \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format": "mermaid"}'
```

### B. Start a Node-Specific Conversation Thread
*Flow: Identify a node (e.g., "Quantum Superposition") and start a thread to explore it further.*
```bash
curl -X POST http://localhost:8000/api/v1/chat/conversations?notebook_id=NOTEBOOK_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Deep Dive: [Node Name]",
    "mode": "assistant"
  }'
```

---

## 🚀 Summary of the Flow
1.  **Notebook** = The Workspace.
2.  **Sources** = The Knowledge (Batch upload).
3.  **Conversation (No source_id)** = Unified brain searching all documents.
4.  **Artifacts** = Structured outputs (Pulse Quizzes, Mindmaps).
5.  **Threads** = Contextual follow-ups from Mindmap nodes.

*Happy Testing!*
