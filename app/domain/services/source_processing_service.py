"""Source processing service for async file processing."""

import logging
from typing import Optional

from app.domain.repositories.notebook_repository import SourceRepository
from app.domain.services.rag_ingest_service import RAGIngestService
from app.domain.services.pdf_service import PdfService
from app.domain.interfaces import IStorageProvider, IPdfProcessor
from app.domain.errors import ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)


class SourceProcessingService:
    """
    Service for processing uploaded source files asynchronously.
    
    Responsibilities:
    - Extract text from uploaded files (PDF, etc.)
    - Chunk and embed document content
    - Update source status
    - Handle processing errors
    """
    
    def __init__(
        self,
        source_repo: SourceRepository,
        storage_provider: IStorageProvider,
        rag_ingest_service: RAGIngestService,
        pdf_service: Optional[PdfService] = None,
    ):
        self.source_repo = source_repo
        self.storage_provider = storage_provider
        self.rag_ingest_service = rag_ingest_service
        self.pdf_service = pdf_service
    
    async def process_source_file(
        self,
        source_id: str,
        storage_key: str,
    ) -> None:
        """
        Process an uploaded source file asynchronously using presigned URLs.
        
        Flow:
        1. Generate presigned URL (10-minute expiration) for private bucket access
        2. Extract text directly from URL (no file download needed)
        3. Chunk and generate embeddings
        4. Store chunks
        5. Update source status to "completed"
        
        Args:
            source_id: Source ID to process
            storage_key: Storage key/URL of uploaded file
        """
        try:
            # Get source
            source = await self.source_repo.get_by_id(source_id)
            if not source:
                logger.error(f"Source not found: {source_id}")
                await self._mark_failed(source_id, "Source not found")
                return
            
            # Update status to processing
            await self.source_repo.update(source_id, status="processing")
            logger.info(f"Processing source {source_id} from storage key: {storage_key}")
            
            # Validate storage_key
            if not storage_key:
                await self._mark_failed(source_id, "Storage key is missing")
                return
            
            # Extract the actual storage key if it's a full URL
            # New format: bucket_name/user_id/notebook_id/source_id.ext
            # If storage_key contains the public URL prefix, extract just the key part
            actual_key = storage_key
            if storage_key.startswith('http://') or storage_key.startswith('https://'):
                # Full URL - extract the key part after the domain
                # Format: https://idr01.zata.ai/vijamindspring/user_id/notebook_id/source_id.ext
                # or: https://idr01.zata.ai/user_id/notebook_id/source_id.ext
                # Remove protocol and domain, keep the path
                from urllib.parse import urlparse
                parsed = urlparse(storage_key)
                actual_key = parsed.path.lstrip('/')
            
            # Generate presigned URL (10 minutes expiration = 600 seconds)
            signed_url = await self.storage_provider.get_signed_url(actual_key, expires_in=600)
            logger.info(f"Generated presigned URL for {actual_key} (expires in 10 minutes)")
            
            # Determine file type and extract text
            file_extension = actual_key.split('.')[-1].lower() if '.' in actual_key else ''
            
            if file_extension == 'pdf':
                # Extract text from PDF using signed URL (no download needed)
                text = await self._extract_pdf_from_url(signed_url)
            elif file_extension in ['txt', 'md']:
                # Plain text files - fetch from signed URL
                text = await self._fetch_text_from_url(signed_url)
            else:
                # Try to fetch as text for other types
                try:
                    text = await self._fetch_text_from_url(signed_url)
                except Exception as e:
                    logger.error(f"Unsupported file type: {file_extension}")
                    await self._mark_failed(source_id, f"Unsupported file type: {file_extension}")
                    return
            
            if not text or len(text.strip()) == 0:
                await self._mark_failed(source_id, "No text extracted from file")
                return
            
            logger.info(f"Extracted {len(text)} characters from source {source_id}")
            
            # Chunk and generate embeddings
            chunks = await self.rag_ingest_service.ingest_document(
                source_id=source_id,
                notebook_id=source.notebook_id,
                document_text=text,
                metadata={
                    "storage_key": storage_key,
                    "file_type": file_extension,
                    "text_length": len(text),
                },
            )
            
            logger.info(f"Created {len(chunks)} chunks for source {source_id}")
            
            # Update source status to completed
            await self.source_repo.update(source_id, status="completed")
            logger.info(f"Source {source_id} processing completed successfully")
            
        except ValidationError as e:
            logger.error(f"Validation error processing source {source_id}: {e}")
            await self._mark_failed(source_id, f"Validation error: {str(e)}")
        except ExternalServiceError as e:
            logger.error(f"External service error processing source {source_id}: {e}")
            await self._mark_failed(source_id, f"Processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing source {source_id}: {e}", exc_info=True)
            # Ensure the source is marked as failed even for unexpected exceptions
            # to prevent it from being stuck in "processing" state
            await self._mark_failed(source_id, f"Unexpected system error: {str(e)}")
    
    async def _extract_pdf_from_url(self, signed_url: str) -> str:
        """
        Extract text from PDF using presigned URL (no download needed).
        
        Args:
            signed_url: Presigned URL to the PDF file
            
        Returns:
            Extracted text
        """
        try:
            import fitz  # PyMuPDF
            import httpx
            
            # Use httpx to fetch the PDF content first
            # This is more robust than fitz.open(url) which can fail on some systems/URLs
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(signed_url)
                response.raise_for_status()
                pdf_bytes = response.content
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            raise ExternalServiceError(
                "PDF processing dependencies (PyMuPDF, httpx) not available.",
                service_name="PDFProcessor",
            )
        except Exception as e:
            logger.error(f"Failed to extract PDF from URL: {e}")
            raise ExternalServiceError(
                f"Failed to extract text from PDF: {str(e)}",
                service_name="PDFProcessor",
                original_error=e,
            )
    
    async def _fetch_text_from_url(self, signed_url: str) -> str:
        """
        Fetch text content from presigned URL.
        
        Args:
            signed_url: Presigned URL to the text file
            
        Returns:
            Text content
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(signed_url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Failed to fetch text from URL: {e}")
            raise ExternalServiceError(
                f"Failed to fetch text from URL: {str(e)}",
                service_name="StorageProvider",
                original_error=e,
            )
    
    async def _mark_failed(self, source_id: str, error_message: str) -> None:
        """Mark source as failed with error message."""
        try:
            await self.source_repo.update(
                source_id,
                status="failed",
                metadata_={"error": error_message},
            )
            logger.error(f"Source {source_id} marked as failed: {error_message}")
        except Exception as e:
            logger.error(f"Failed to mark source {source_id} as failed: {e}", exc_info=True)
