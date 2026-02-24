# Testing Strategy & Implementation Guide

## Overview

The testing architecture mirrors the service layer architecture: **tests ARE testable WITHOUT HTTP/FastAPI/databases**.

This guide covers:
1. **Test Organization** - Directory structure and file naming
2. **Test Types** - Unit tests, integration tests, and E2E tests
3. **Testing Patterns** - Fixtures, factories, assertions, error handling
4. **Infrastructure Mocking** - How mock providers enable fast, isolated tests
5. **Common Testing Patterns** - Authorization, pagination, state machines, cascading deletes
6. **Best Practices** - What to test, what not to test, avoiding common pitfalls

---

## Test Organization

```
tests/
├── _fixtures.py              # Shared fixtures and factories
├── unit/
│   ├── services/
│   │   ├── test_auth_service.py              # ✓ CREATED
│   │   ├── test_notebook_service.py          # ✓ CREATED
│   │   ├── test_document_service.py          # ✓ CREATED
│   │   ├── test_chat_service.py              # TODO
│   │   ├── test_quiz_service.py              # TODO
│   │   ├── test_job_service.py               # TODO
│   │   ├── test_history_service.py           # TODO
│   │   └── ...
│   ├── repositories/
│   │   ├── test_user_repository.py           # TODO
│   │   ├── test_notebook_repository.py       # TODO
│   │   └── ...
│   └── infrastructure/
│       ├── test_mock_storage.py              # TODO
│       ├── test_mock_queue.py                # TODO
│       └── ...
├── integration/
│   ├── test_auth_endpoints.py                # TODO
│   ├── test_notebook_endpoints.py            # TODO
│   ├── test_chat_endpoints.py                # TODO
│   ├── test_document_endpoints.py            # TODO
│   └── test_quiz_endpoints.py                # TODO
└── e2e/
    ├── test_user_signup_flow.py              # TODO
    ├── test_document_upload_flow.py          # TODO
    └── test_chat_conversation_flow.py        # TODO
```

---

## Test Types & Scope

### 1. Unit Tests (FAST - 100ms-1s per test)

**What**: Test a single service method in isolation

**How**: Inject mock repositories/infrastructure, verify business logic

**Example Pattern**:
```python
@pytest.mark.asyncio
async def test_register_user_success(async_db, auth_service):
    # SETUP
    email = "user@example.com"
    password = "SecurePass123!"
    
    # ACT
    user, otp = await auth_service.register_user(email, password)
    
    # ASSERT
    assert user.email == email
    assert otp is not None
    assert user.is_verified is False
```

**Benefits**:
- ✓ Fast (run all in ~2 seconds)
- ✓ Isolation (no external dependencies)
- ✓ Deterministic (always pass/fail same way)
- ✓ Easy to debug (clear failure point)

**Current Coverage**: 3 services tested (auth, notebook, document)

---

### 2. Integration Tests (MEDIUM - 500ms-2s per test)

**What**: Test endpoint-to-service communication

**How**: Use real FastAPI test client, real async database, mock infrastructure

**Example Pattern**:
```python
@pytest.mark.asyncio
async def test_signup_endpoint(client, async_db):
    # SETUP
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
    )
    
    # ASSERT
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
```

**Benefits**:
- ✓ Validates endpoint contracts
- ✓ Tests request/response transformation
- ✓ Tests error handling (DomainError → HTTPException)
- ✓ Tests authentication/authorization headers

**Current Coverage**: 0 endpoints (pattern established, ready to implement)

---

### 3. End-to-End Tests (SLOW - 1-5s per test)

**What**: Test complete user workflows

**How**: Start with signup, create notebook, add sources, generate quiz, etc.

**Example Pattern**:
```python
@pytest.mark.asyncio
async def test_user_can_create_notebook_and_add_sources(client, async_db):
    # 1. Sign up
    signup_resp = await client.post("/api/v1/auth/signup", ...)
    access_token = signup_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. Create notebook
    notebook_resp = await client.post(
        "/api/v1/notebooks",
        json={"title": "AI Learning"},
        headers=headers
    )
    notebook_id = notebook_resp.json()["id"]
    
    # 3. Add source
    source_resp = await client.post(
        f"/api/v1/notebooks/{notebook_id}/sources",
        json={"url": "https://example.com"},
        headers=headers
    )
    
    # 4. Verify workflow
    assert notebook_resp.status_code == 201
    assert source_resp.status_code == 201
```

**Benefits**:
- ✓ Validates complete workflows
- ✓ Catches integration issues
- ✓ Tests real user scenarios
- ✓ Foundation for regression testing

**Current Coverage**: 0 workflows (framework ready)

---

## Testing Patterns

### Pattern 1: Authorization Testing

**Problem**: Need to verify users can only access their own data

**Solution**: Create two users, have one try to access the other's data

```python
@pytest.mark.asyncio
async def test_user_cannot_access_other_users_notebook(
    async_db: AsyncSession,
    notebook_service: NotebookService,
):
    # Create two users
    user1 = await UserFactory.create(async_db)
    user2 = await UserFactory.create(async_db)
    
    # User1 creates notebook
    notebook = await NotebookFactory.create(async_db, owner_id=user1.id)
    
    # User2 tries to access it
    with pytest.raises(NotFoundError):
        await notebook_service.get_notebook(notebook.id, user2.id)
```

**Key Pattern**: Service returns NotFoundError for both "doesn't exist" AND "you don't have access"
- Prevents information leakage (attacker doesn't learn IDs exist)
- Tests verify this behavior

---

### Pattern 2: Business Rules Validation

**Problem**: Need to enforce business constraints (quotas, limits, state machines)

**Solution**: Create scenario that violates rule, assert proper error

```python
@pytest.mark.asyncio
async def test_cannot_exceed_notebook_limit(
    async_db: AsyncSession,
    notebook_service: NotebookService,
):
    user = await UserFactory.create(async_db)
    
    # Create maximum notebooks
    for i in range(50):
        await notebook_service.create_notebook(user.id, f"Notebook {i}")
    
    # Try to exceed limit
    with pytest.raises(ForbiddenError) as exc_info:
        await notebook_service.create_notebook(user.id, "Over Limit")
    
    assert "limit" in str(exc_info.value).lower()
```

**Key Pattern**: 
- Test both success case (within limit)
- Test failure case (exceeds limit)
- Verify specific error type
- Verify error message is informative

---

### Pattern 3: Data Integrity (Cascading Deletes)

**Problem**: When deleting parent entity, related entities must be cleaned up

**Solution**: Create related entities, delete parent, verify children are gone

```python
@pytest.mark.asyncio
async def test_deleting_notebook_cascades_to_sources(
    async_db: AsyncSession,
    notebook_service: NotebookService,
):
    user = await UserFactory.create(async_db)
    notebook = await NotebookFactory.create(async_db, owner_id=user.id)
    
    # Add source to notebook
    sources = await notebook_service.add_source_to_notebook(
        notebook.id,
        user.id,
        source_data={...}
    )
    source_id = sources[0].id
    
    # Delete notebook
    await notebook_service.delete_notebook(notebook.id, user.id)
    
    # Verify source is deleted
    with pytest.raises(NotFoundError):
        await DocumentService.get_source(source_id)
```

**Key Pattern**: 
- Verify related entities exist before delete
- Delete parent
- Verify related entities are cleaned up

---

### Pattern 4: Pagination

**Problem**: Services return large result sets; need to test pagination

**Solution**: Create N items, query with skip/limit, verify pages are correct

```python
@pytest.mark.asyncio
async def test_list_notebooks_pagination(
    async_db: AsyncSession,
    notebook_service: NotebookService,
):
    user = await UserFactory.create(async_db)
    
    # Create 25 notebooks
    for i in range(25):
        await NotebookFactory.create(async_db, owner_id=user.id)
    
    # Get page 1
    page1 = await notebook_service.list_user_notebooks(
        user.id, skip=0, limit=10
    )
    assert len(page1) == 10
    
    # Get page 2
    page2 = await notebook_service.list_user_notebooks(
        user.id, skip=10, limit=10
    )
    assert len(page2) == 10
    
    # Get page 3
    page3 = await notebook_service.list_user_notebooks(
        user.id, skip=20, limit=10
    )
    assert len(page3) == 5
    
    # Verify no overlap (different IDs)
    page1_ids = {n.id for n in page1}
    page2_ids = {n.id for n in page2}
    assert len(page1_ids & page2_ids) == 0
```

**Key Pattern**:
- Create sufficient items to test multiple pages
- Query each page with distinct skip/limit
- Verify page sizes
- Verify no overlap between pages

---

### Pattern 5: State Machine Validation

**Problem**: Jobs have state progression (PENDING → RUNNING → COMPLETED/FAILED)

**Solution**: Test invalid transitions, verify valid ones work

```python
@pytest.mark.asyncio
async def test_job_state_transitions(
    async_db: AsyncSession,
    job_service: JobService,
):
    user = await UserFactory.create(async_db)
    job = await JobFactory.create(async_db, status="PENDING")
    
    # Valid: PENDING → RUNNING
    await job_service.mark_job_running(job.id)
    updated = await job_repo.get_job(job.id)
    assert updated.status == "RUNNING"
    
    # Valid: RUNNING → COMPLETED
    await job_service.mark_job_completed(job.id)
    updated = await job_repo.get_job(job.id)
    assert updated.status == "COMPLETED"
    
    # Invalid: COMPLETED → PENDING (should fail)
    with pytest.raises(BusinessRuleViolationError):
        await job_service.mark_job_running(job.id)
```

**Key Pattern**:
- Test valid transitions work
- Test invalid transitions raise errors
- Verify final state is correct

---

### Pattern 6: Infrastructure Integration

**Problem**: Services use infrastructure providers; need to test integration

**Solution**: Providers are injected; test service behavior with mocks

```python
@pytest.mark.asyncio
async def test_upload_stores_file_and_creates_job(
    async_db: AsyncSession,
    document_service: DocumentService,
):
    user = await UserFactory.create(async_db)
    storage = document_service.storage_provider
    queue = document_service.queue_provider
    
    # Upload document
    document = await document_service.upload_document(
        user_id=user.id,
        filename="test.pdf",
        file_content=b"PDF content"
    )
    
    # Verify file stored
    assert storage.files.get(document.storage_key) is not None
    
    # Verify job queued
    jobs = queue.get_queue()
    assert any(j.document_id == document.id for j in jobs)
    
    # Verify job status is PENDING
    job = next(j for j in jobs if j.document_id == document.id)
    assert job.status == "PENDING"
```

**Key Pattern**:
- Get mock provider from service (it's injected)
- Verify service calls provider correctly
- Verify provider state is updated

---

## Fixtures & Factories

### Using Fixtures

Fixtures are reusable test setup. Defined in `tests/_fixtures.py`:

```python
@pytest_fixture
async def user_with_notebook(async_db):
    """Create user + notebook for testing."""
    user = await UserFactory.create(async_db)
    notebook = await NotebookFactory.create(async_db, owner_id=user.id)
    return {"user": user, "notebook": notebook}
```

Usage:
```python
@pytest.mark.asyncio
async def test_something(user_with_notebook):
    user = user_with_notebook["user"]
    notebook = user_with_notebook["notebook"]
    # ... test code
```

### Using Factories

Factories create test data with sensible defaults. Define in `tests/_fixtures.py`:

```python
class UserFactory:
    @staticmethod
    async def create(db: AsyncSession, **kwargs):
        defaults = {
            "email": f"user{random.randint(1000, 9999)}@example.com",
            "name": "Test User",
            "password_hash": hash_password("password123"),
            "is_verified": False,
        }
        defaults.update(kwargs)
        return await UserRepository(db).create(**defaults)
```

Usage:
```python
user1 = await UserFactory.create(async_db)
user2 = await UserFactory.create(async_db, email="custom@example.com")
user3 = await UserFactory.create(async_db, is_verified=True)
```

**Benefits**:
- ✓ Consistent test data
- ✓ Easy to override specific fields
- ✓ Reduces duplication across tests
- ✓ Fails fast if factory breaks

---

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Single Test File
```bash
pytest tests/unit/services/test_auth_service.py
```

### Run Single Test
```bash
pytest tests/unit/services/test_auth_service.py::TestAuthService::test_register_user_success
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run Tests in Parallel (faster)
```bash
pytest tests/ -n auto
```

---

## Common Testing Mistakes to Avoid

### ❌ MISTAKE 1: Testing HTTP Details in Service Tests

```python
# WRONG: Service tests shouldn't care about HTTP
async def test_auth_service():
    response = client.post("/auth/signup", json={...})
    assert response.status_code == 201
```

```python
# RIGHT: Service tests only test business logic
async def test_auth_service():
    user, otp = await auth_service.register_user(email, password)
    assert user.email == email
```

---

### ❌ MISTAKE 2: Creating Real Infrastructure in Tests

```python
# WRONG: Slow tests that require S3, Redis, etc.
async def test_upload():
    s3_client = boto3.client("s3")  # Requires real AWS credentials
    document = await service.upload(...)
```

```python
# RIGHT: Mock infrastructure is injected
async def test_upload(document_service):
    # storage_provider is MockStorageProvider
    document = await document_service.upload_document(...)
```

---

### ❌ MISTAKE 3: Testing Multiple Concerns in One Test

```python
# WRONG: This test tests 5 things at once
async def test_user_flow():
    # 1. Registration
    user = await auth_service.register_user(...)
    # 2. Email verification
    await auth_service.verify_email(...)
    # 3. Login
    token = await auth_service.login(...)
    # 4. Create notebook
    notebook = await notebook_service.create_notebook(...)
    # 5. Add source
    source = await notebook_service.add_source(...)
```

```python
# RIGHT: One test, one concern
async def test_register_user_success(async_db):
    # ONLY test registration
    user, otp = await auth_service.register_user(email, password)
    assert user.email == email
```

---

### ❌ MISTAKE 4: Asserting on String Representations

```python
# WRONG: Brittle test that breaks on message changes
with pytest.raises(ValidationError) as exc_info:
    await auth_service.register_user("invalid", "pass")
assert "Invalid email" in str(exc_info.value)
```

```python
# RIGHT: Assert on error type and code
with pytest.raises(ValidationError) as exc_info:
    await auth_service.register_user("invalid", "pass")
assert exc_info.value.code == ErrorCode.INVALID_EMAIL
```

---

### ❌ MISTAKE 5: Not Testing Error Cases

```python
# WRONG: Only test happy path
async def test_get_notebook(async_db):
    notebook = await NotebookFactory.create(async_db)
    result = await notebook_service.get_notebook(notebook.id, user.id)
    assert result is not None
```

```python
# RIGHT: Test both success AND failure cases
async def test_get_notebook_success(async_db):
    notebook = await NotebookFactory.create(async_db)
    result = await notebook_service.get_notebook(notebook.id, user.id)
    assert result is not None

async def test_get_notebook_not_found(async_db):
    with pytest.raises(NotFoundError):
        await notebook_service.get_notebook(999, user.id)

async def test_get_notebook_unauthorized(async_db):
    user2 = await UserFactory.create(async_db)
    notebook = await NotebookFactory.create(async_db, owner_id=user1.id)
    with pytest.raises(NotFoundError):
        await notebook_service.get_notebook(notebook.id, user2.id)
```

---

## Test Coverage Goals

### By Layer

| Layer | Target | Current | Status |
|-------|--------|---------|--------|
| Services | 95% | 0% | 🔴 Starting |
| Repositories | 90% | 0% | 🔴 Starting |
| Domain Logic | 100% | 0% | 🔴 Starting |
| Endpoints | 85% | 0% | 🔴 Starting |
| Infrastructure | 80% | 0% | 🔴 Starting |

### By Service

| Service | Unit Tests | Integration | E2E |
|---------|-----------|------------|-----|
| AuthService | ✓ CREATED | TODO | TODO |
| NotebookService | ✓ CREATED | TODO | TODO |
| DocumentService | ✓ CREATED | TODO | TODO |
| ChatService | TODO | TODO | TODO |
| QuizService | TODO | TODO | TODO |
| JobService | TODO | TODO | TODO |
| HistoryService | TODO | TODO | TODO |
| RAGIngestService | TODO | TODO | TODO |
| PDFService | TODO | TODO | TODO |
| CacheMonitoringService | TODO | TODO | TODO |
| ExternalProcessingService | TODO | TODO | TODO |

---

## Implementation Checklist

### Phase 1: Service Unit Tests (CURRENT)
- [x] AuthService unit tests
- [x] NotebookService unit tests  
- [x] DocumentService unit tests
- [ ] ChatService unit tests
- [ ] QuizService unit tests
- [ ] JobService unit tests
- [ ] HistoryService unit tests
- [ ] Remaining service tests

### Phase 2: Repository Unit Tests
- [ ] UserRepository tests
- [ ] NotebookRepository tests
- [ ] DocumentRepository tests
- [ ] All repository tests

### Phase 3: Integration Tests
- [ ] Auth endpoints integration tests
- [ ] Notebook endpoints integration tests
- [ ] Chat endpoints integration tests
- [ ] Document endpoints integration tests
- [ ] Quiz endpoints integration tests

### Phase 4: E2E Tests
- [ ] User signup → login flow
- [ ] Create notebook → add sources → generate quiz
- [ ] Upload document → create job → process

### Phase 5: Performance Tests
- [ ] Service response time benchmarks
- [ ] Database query performance
- [ ] Cache effectiveness

---

## Summary

This testing strategy enables:

✓ **Fast tests** - Unit tests run in seconds (no external dependencies)
✓ **Isolated tests** - Each test is independent, can run in any order
✓ **Complete coverage** - Unit (logic) + Integration (contracts) + E2E (workflows)
✓ **Maintainable tests** - Factories/fixtures reduce duplication
✓ **Documentable** - Tests show expected behavior to team
✓ **Production-safe** - Tests validate architecture patterns before code ships

As you build more tests, you'll notice:
- Services become easier to test (clear interfaces, injected dependencies)
- Repository interactions become evident (helps catch N+1 queries)
- Infrastructure providers reveal assumptions (makes swapping realizations clearer)
- Edge cases come to light (error scenarios, boundary conditions)

**Next Steps**: 
1. Run existing tests: `pytest tests/unit/services/ -v`
2. Create integration tests following [INTEGRATION_TEST_EXAMPLE.md](INTEGRATION_TEST_EXAMPLE.md)
3. Build E2E tests for critical user flows
