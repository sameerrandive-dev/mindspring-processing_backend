from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, chat, notebooks, quiz, health, sources


api_router = APIRouter()

# Include all API routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(notebooks.router, prefix="/notebooks", tags=["notebooks"])
api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
api_router.include_router(sources.router, prefix="", tags=["sources"])  # No prefix, uses full paths
api_router.include_router(health.router, prefix="/health", tags=["health"])