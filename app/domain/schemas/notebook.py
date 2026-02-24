"""Pydantic schemas for notebook API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NotebookCreate(BaseModel):
    """Schema for creating a notebook."""
    title: str = Field(..., min_length=1, max_length=500, description="Notebook title")
    description: Optional[str] = Field(None, description="Notebook description")
    language: str = Field("en", max_length=50, description="Language code (e.g., 'en', 'es')")
    tone: str = Field("educational", max_length=50, description="Tone/style (e.g., 'educational', 'professional')")
    max_context_tokens: int = Field(8000, ge=1000, le=32000, description="Maximum context tokens for AI interactions")


class NotebookUpdate(BaseModel):
    """Schema for updating a notebook."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    language: Optional[str] = Field(None, max_length=50)
    tone: Optional[str] = Field(None, max_length=50)
    max_context_tokens: Optional[int] = Field(None, ge=1000, le=32000)


class NotebookResponse(BaseModel):
    """Schema for notebook response."""
    id: str
    title: str
    description: Optional[str]
    language: str
    tone: str
    max_context_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotebookListResponse(BaseModel):
    """Schema for notebook list response."""
    notebooks: list[NotebookResponse]
    total: int


class NotebookSummaryResponse(BaseModel):
    summary: str
    notebook_id: str
    history_id: str
    style: str


class NotebookMindmapResponse(BaseModel):
    mindmap: dict
    notebook_id: str
    format: str
    history_id: str


class NotebookQuizGenerateRequest(BaseModel):
    topic: str
    num_questions: int = 10
    difficulty: str = "medium"


class NotebookStudyGuideGenerateRequest(BaseModel):
    topic: str
    format: str = "structured"
