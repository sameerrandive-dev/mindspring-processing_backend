from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from typing import List, Optional
from uuid import uuid4
import hashlib
import os
from datetime import datetime

from app.core.security import get_current_user
from app.domain.models.user import User
from app.domain.models.document import Document
from app.domain.models.job import Job
from app.infrastructure.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload a document for processing."""
    # Validate file type
    allowed_types = [
        "application/pdf", 
        "application/msword", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed types: {allowed_types}"
        )
    
    # Calculate file hash
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check if file already exists
    existing_doc_query = select(Document).where(
        Document.file_hash == file_hash,
        Document.user_id == current_user.id
    )
    result = await db.execute(existing_doc_query)
    existing_doc = result.scalar_one_or_none()
    
    if existing_doc:
        return {
            "message": "File already exists",
            "document_id": existing_doc.id,
            "status": existing_doc.status
        }
    
    # Create document record
    document_id = str(uuid4())
    document = Document(
        id=document_id,
        user_id=current_user.id,
        file_name=file.filename,
        file_size=len(file_content),
        file_hash=file_hash,
        storage_key=f"documents/{current_user.id}/{document_id}/{file.filename}",
        status="pending"
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Create a processing job
    job = Job(
        id=str(uuid4()),
        document_id=document.id,
        user_id=current_user.id,
        job_type="document_processing",
        status="pending"
    )
    
    db.add(job)
    await db.commit()
    
    return {
        "document_id": document.id,
        "filename": document.file_name,
        "status": document.status,
        "job_id": job.id,
        "message": "Document uploaded successfully and processing started"
    }


@router.get("/")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """List all documents for the current user."""
    query = select(Document).where(Document.user_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.file_name,
                "size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            }
            for doc in documents
        ],
        "total": len(documents)
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get document details by ID."""
    query = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {
        "id": document.id,
        "filename": document.file_name,
        "size": document.file_size,
        "hash": document.file_hash,
        "storage_key": document.storage_key,
        "status": document.status,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat()
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a document by ID."""
    query = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # TODO: Actually delete the file from storage (S3, etc.)
    # For now, just mark as deleted in the database
    
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}