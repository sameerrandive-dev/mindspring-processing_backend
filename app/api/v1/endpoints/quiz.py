from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import json

from app.core.security import get_current_user
from app.domain.models.user import User
from app.domain.models.quiz import Quiz
from app.infrastructure.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


@router.post("/")
async def create_quiz(
    notebook_id: str,
    topic: str,
    questions: Dict[str, Any],  # Quiz questions in structured format
    model: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new quiz."""
    quiz_id = str(uuid4())
    quiz = Quiz(
        id=quiz_id,
        notebook_id=notebook_id,
        user_id=current_user.id,
        topic=topic,
        questions=questions,
        model=model
    )
    
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    
    return {
        "id": quiz.id,
        "notebook_id": quiz.notebook_id,
        "topic": quiz.topic,
        "model": quiz.model,
        "version": quiz.version,
        "created_at": quiz.created_at.isoformat()
    }


@router.get("/")
async def list_quizzes(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """List all quizzes for a notebook."""
    query = select(Quiz).where(
        Quiz.notebook_id == notebook_id,
        Quiz.user_id == current_user.id
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    quizzes = result.scalars().all()
    
    return {
        "quizzes": [
            {
                "id": q.id,
                "topic": q.topic,
                "model": q.model,
                "version": q.version,
                "created_at": q.created_at.isoformat()
            }
            for q in quizzes
        ],
        "total": len(quizzes)
    }


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get quiz details by ID."""
    query = select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id
    )
    result = await db.execute(query)
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return {
        "id": quiz.id,
        "notebook_id": quiz.notebook_id,
        "topic": quiz.topic,
        "questions": quiz.questions,
        "model": quiz.model,
        "version": quiz.version,
        "created_at": quiz.created_at.isoformat()
    }


@router.put("/{quiz_id}")
async def update_quiz(
    quiz_id: str,
    questions: Optional[Dict[str, Any]] = None,
    topic: Optional[str] = None,
    model: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a quiz."""
    query = select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id
    )
    result = await db.execute(query)
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Update fields if provided
    if questions is not None:
        quiz.questions = questions
    if topic is not None:
        quiz.topic = topic
    if model is not None:
        quiz.model = model
    
    quiz.version += 1  # Increment version
    
    await db.commit()
    await db.refresh(quiz)
    
    return {
        "id": quiz.id,
        "notebook_id": quiz.notebook_id,
        "topic": quiz.topic,
        "questions": quiz.questions,
        "model": quiz.model,
        "version": quiz.version,
        "updated_at": quiz.created_at.isoformat()  # Updated timestamp since created_at is immutable
    }


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a quiz by ID."""
    query = select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id
    )
    result = await db.execute(query)
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    await db.delete(quiz)
    await db.commit()
    
    return {"message": "Quiz deleted successfully"}