# Enterprise Architecture Quick Reference

**One-page guide for developers working on this codebase**

---

## 🏗️ Architecture in 30 Seconds

```
HTTP Request
    ↓
[Endpoint] ← Validates input, checks auth
    ↓
[Service] ← Business logic, authorization, validation
    ↓
[Repository] ← Database queries
    ↓
[Mock Infrastructure] ← File storage, queues, caching, email, LLM
```

**Key Rule**: Each layer knows only about the layer below it.

---

## 📁 Where is Everything?

| What | Where |
|-----|-------|
| Business Logic | `app/domain/services/*.py` |
| Database Access | `app/domain/repositories/*.py` |
| Error Types | `app/domain/errors/exceptions.py` |
| HTTP Handlers | `app/api/v1/endpoints/*.py` |
| Storage/Queue/Cache | `app/infrastructure/` |
| Service Creation | `app/infrastructure/container.py` |
| Tests | `tests/` |
| Patterns | `*_GUIDE.md` files |

---

## 🚀 Adding a New Feature

### Step 1: Add to Service
```python
# app/domain/services/my_service.py
from app.domain.errors import NotFoundError

class MyService:
    def __init__(self, repo: MyRepository):
        self.repo = repo
    
    async def do_something(self, user_id: str):
        item = await self.repo.get(user_id)
        if not item:
            raise NotFoundError("Not found")
        return item
```

### Step 2: Update Container
```python
# app/infrastructure/container.py
def get_my_service(self) -> MyService:
    return MyService(repo=self.get_my_repository())
```

### Step 3: Create Endpoint
```python
# app/api/v1/endpoints/my.py
@router.get("/items/{id}")
async def get_item(id: str, service=Depends(get_my_service)):
    try:
        return await service.do_something(id)
    except DomainError as e:
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
```

### Step 4: Write Tests
```python
# tests/unit/services/test_my_service.py
@pytest.mark.asyncio
async def test_do_something_success(my_service):
    result = await my_service.do_something(user_id)
    assert result is not None
```

---

## 🛠️ Common Tasks

### Find where something is handled
```bash
# Search for service method
grep -r "my_method" app/domain/services/

# Find endpoint that uses it
grep -r "my_method" app/api/

# Find tests for it
grep -r "my_method" tests/
```

### Test a service without HTTP
```python
# No FastAPI imports needed!
service = MyService(repo=mock_repo, infrastructure=mock_provider)
result = await service.do_something(params)
```

### Handle an error in endpoint
```python
try:
    result = await service.method()
except ConflictError as e:
    raise HTTPException(status_code=409, detail=e.message)
except NotFoundError as e:
    raise HTTPException(status_code=404, detail=e.message)
```

### Inject a dependency
```python
# In endpoint
async def handler(
    request: RequestSchema,
    service=Depends(get_auth_service),  # ← Injected
    container=Depends(get_service_container),  # ← Container access
):
    result = await service.method()
```

---

## ⚠️ Common Mistakes

### ❌ DON'T Put Business Logic in Endpoint
```python
# WRONG
@router.post("/items")
async def create_item(item_in: ItemCreate):
    existing = await db.query(Item).filter_by(name=item_in.name).first()
    if existing:
        raise HTTPException(status_code=409)
    item = Item(**item_in.dict())
    db.add(item)
    await db.commit()
```

### ✅ DO Put Business Logic in Service
```python
# Service
async def create_item(self, name: str):
    existing = await self.repo.get_by_name(name)
    if existing:
        raise ConflictError("Already exists")
    return await self.repo.create(name)

# Endpoint
@router.post("/items")
async def create_item(item_in: ItemCreate, service=Depends(get_item_service)):
    try:
        return await service.create_item(item_in.name)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.message)
```

### ❌ DON'T Import FastAPI in Services
```python
# WRONG - Services never import FastAPI!
from fastapi import HTTPException

class MyService:
    def validate(self):
        raise HTTPException(status_code=400)  # ❌ NO!
```

### ✅ DO Use DomainErrors in Services
```python
# RIGHT - Services use business errors
from app.domain.errors import ValidationError

class MyService:
    def validate(self):
        raise ValidationError("Invalid input")  # ✅ YES
```

---

## 📊 Error Mapping

| Error | HTTP Status | Use For |
|-------|-----------|---------|
| ValidationError | 422 | Input validation failed |
| NotFoundError | 404 | Resource not found |
| ConflictError | 409 | Duplicate/conflict |
| AuthError | 401 | Bad credentials |
| ForbiddenError | 403 | Not authorized/quota exceeded |
| BusinessRuleViolationError | 400 | Invalid operation |
| RateLimitError | 429 | Rate limited |
| ExternalServiceError | 503 | External service down |

---

## 🧪 Testing Quick Start

### Run Tests
```bash
# All tests
pytest tests/

# Just services
pytest tests/unit/services/

# Single file
pytest tests/unit/services/test_auth_service.py

# Single test
pytest tests/unit/services/test_auth_service.py::TestAuthService::test_register_user_success

# With coverage
pytest tests/ --cov=app
```

### Write a Test
```python
@pytest.mark.asyncio
async def test_my_service_success(async_db):
    # SETUP
    user = await UserFactory.create(async_db)
    
    # ACT
    result = await my_service.do_something(user.id)
    
    # ASSERT
    assert result is not None
    assert result.owner_id == user.id
```

### Fixture Availability
```python
# Just declare what you need
async def test_something(
    async_db: AsyncSession,           # In-memory database
    user_with_notebook,               # Pre-created user + notebook
    auth_service: AuthService,        # Service instance
):
    pass
```

---

## 📝 Service Methods Cheat Sheet

### AuthService
```python
user, otp = await auth_service.register_user(email, password)
await auth_service.verify_email(email, otp_code)
tokens = await auth_service.login(email, password)
tokens = await auth_service.refresh_tokens(refresh_token)
await auth_service.logout(user_id)
```

### NotebookService
```python
notebook = await notebook_service.create_notebook(user_id, title)
notebook = await notebook_service.get_notebook(notebook_id, user_id)
notebook = await notebook_service.update_notebook(notebook_id, user_id, title=...)
await notebook_service.delete_notebook(notebook_id, user_id)
notebooks = await notebook_service.list_user_notebooks(user_id)
```

### ChatService
```python
conv = await chat_service.create_conversation(user_id, title)
message = await chat_service.add_message(conversation_id, user_id, role, content)
messages = await chat_service.get_conversation_messages(conversation_id, user_id)
await chat_service.delete_conversation(conversation_id, user_id)
```

### DocumentService
```python
doc = await document_service.upload_document(user_id, filename, file_content)
doc = await document_service.get_document(document_id, user_id)
status = await document_service.get_document_status(document_id, user_id)
await document_service.delete_document(document_id, user_id)
```

### QuizService
```python
quiz = await quiz_service.create_quiz(user_id, notebook_id, title)
quiz = await quiz_service.generate_quiz_questions(quiz_id, user_id, notebook_id)
quiz = await quiz_service.get_quiz(quiz_id, user_id)
quizzes = await quiz_service.list_notebook_quizzes(user_id, notebook_id)
await quiz_service.delete_quiz(quiz_id, user_id)
```

---

## 🔧 Getting a Service in Your Code

### Option 1: Use Container (Recommended)
```python
from app.infrastructure.container import ServiceContainer

container = ServiceContainer(db)
my_service = container.get_my_service()
result = await my_service.method()
```

### Option 2: Use Dependency Injection (Endpoints)
```python
@router.get("/")
async def my_endpoint(service=Depends(get_my_service)):
    result = await service.method()
```

### Option 3: Direct Instantiation (Tests)
```python
service = MyService(repo=my_repo, infrastructure=my_provider)
result = await service.method()
```

---

## 📚 Documentation Files

| File | When to Read | Time |
|------|--------------|------|
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | Want big picture | 5 min |
| [ENDPOINT_REFACTORING_GUIDE.md](ENDPOINT_REFACTORING_GUIDE.md) | Refactoring endpoints | 10 min |
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | Writing tests | 15 min |
| [INTEGRATION_TESTING_GUIDE.md](INTEGRATION_TESTING_GUIDE.md) | Integration tests | 20 min |
| Code examples | Learn patterns | 30 min |

---

## 🎯 Current Focus

**Phase**: Endpoint Refactoring
**Status**: 1/5 complete
**Next Step**: Refactor chat.py using ChatService

Follow pattern from `app/api/v1/endpoints/auth.py`

---

## ✅ Architecture Checklist

When adding a service, verify:

- [ ] Service has no FastAPI imports
- [ ] All data access via repository
- [ ] Dependencies injected in `__init__`
- [ ] Raises DomainError subclasses (not HTTPException)
- [ ] Has comprehensive error handling
- [ ] Has async/await for all I/O
- [ ] Has logging for debugging
- [ ] Added to ServiceContainer
- [ ] Added to `__init__.py` exports
- [ ] Has unit tests (no HTTP)
- [ ] Tests show isolation (can run independently)

When refactoring endpoint, verify:

- [ ] Imports service via Depends
- [ ] Business logic removed (all in service)
- [ ] Validation done by Pydantic + service
- [ ] Error handling maps DomainError → HTTPException
- [ ] Handler is 10-15 lines max
- [ ] No direct DB queries
- [ ] No infrastructure imports

---

## 🚨 Help! I'm Stuck

### Service test fails
**Check**: Did you use correct async fixtures? Did you await the call?
```python
# Make sure you await
result = await my_service.method()  # ← await is required
```

### Endpoint returns wrong status code
**Check**: DomainError type and mapping
```python
# Verify exception type is correct
assert isinstance(exc, NotFoundError)  # Returns 404
```

### Import Error in service
**Check**: No FastAPI imports allowed
```bash
grep -l "from fastapi" app/domain/services/
# Should return nothing
```

### Service not created
**Check**: Is it in ServiceContainer?
```python
# app/infrastructure/container.py
def get_my_service(self) -> MyService:
    return MyService(deps=...)
```

---

## 💡 Pro Tips

1. **Use factories for test data**: `UserFactory.create(db)` not manual queries
2. **Catch specific errors**: `except NotFoundError` not `except Exception`
3. **Mark tests async**: `@pytest.mark.asyncio` required for async tests
4. **Read existing code**: Auth service + auth endpoint is reference implementation
5. **Run tests often**: `pytest tests/unit/services/ -v` while developing
6. **Keep handlers thin**: If endpoint > 20 lines, move to service
7. **Document errors**: What should fail and which error should be raised?

---

## 📞 Quick Links

- **Repository Hub**: [app/domain/repositories/](app/domain/repositories/)
- **Service Hub**: [app/domain/services/](app/domain/services/)
- **Exception Types**: [app/domain/errors/exceptions.py](app/domain/errors/exceptions.py)
- **Endpoint Templates**: [app/api/v1/endpoints/auth.py](app/api/v1/endpoints/auth.py)
- **Container**: [app/infrastructure/container.py](app/infrastructure/container.py)
- **Test Examples**: [tests/unit/services/](tests/unit/services/)
- **Fixtures**: [tests/_fixtures.py](tests/_fixtures.py)

---

**Remember**: Every layer depends only on the layer below. Services don't know about HTTP. Endpoints don't contain logic. Tests prove the system works.

**Questions?** Check the guides or look at working examples (auth.py, test_auth_service.py).

