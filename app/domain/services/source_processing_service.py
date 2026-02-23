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
        logger.info(f"🚀 Starting background processing for source {source_id}")
        logger.info(f"📂 Storage key: {storage_key}")
        
        try:
            # Get source
            logger.info(f"🔍 Retrieving source record for {source_id}")
            source = await self.source_repo.get_by_id(source_id)
            if not source:
                logger.error(f"❌ Source not found: {source_id}")
                await self._mark_failed(source_id, "Source not found")
                return
            
            # Update status to processing
            logger.info(f"🔄 Updating source status to 'processing'")
            await self.source_repo.update(source_id, status="processing")
            logger.info(f"✅ Source {source_id} status updated to processing")
            
            # Validate storage_key
            if not storage_key:
                logger.error(f"❌ Storage key is missing for source {source_id}")
                await self._mark_failed(source_id, "Storage key is missing")
                return
            
            # Extract the actual storage key if it's a full URL
            logger.info(f"🔗 Processing storage key format")
            actual_key = storage_key
            if storage_key.startswith('http://') or storage_key.startswith('https://'):
                # Full URL - extract the key part after the domain
                # Format: https://idr01.zata.ai/vijamindspring/user_id/notebook_id/source_id.ext
                # or: https://idr01.zata.ai/user_id/notebook_id/source_id.ext
                # Remove protocol and domain, keep the path
                from urllib.parse import urlparse
                parsed = urlparse(storage_key)
                actual_key = parsed.path.lstrip('/')
                logger.info(f"🌐 Extracted actual key from URL: {actual_key}")
            
            # Generate presigned URL (10 minutes expiration = 600 seconds)
            logger.info(f"🔐 Generating presigned URL (10-minute expiration)")
            signed_url = await self.storage_provider.get_signed_url(actual_key, expires_in=600)
            logger.info(f"✅ Generated presigned URL for {actual_key}")
            
            # Determine file type and extract text
            file_extension = actual_key.split('.')[-1].lower() if '.' in actual_key else ''
            logger.info(f"📄 File extension detected: {file_extension}")
            
            if file_extension == 'pdf':
                logger.info(f"📄 Processing PDF file")
                # Extract text from PDF using signed URL (no download needed)
                text = await self._extract_pdf_from_url(signed_url)
            elif file_extension in ['txt', 'md']:
                logger.info(f"📄 Processing text file ({file_extension})")
                # Plain text files - fetch from signed URL
                text = await self._fetch_text_from_url(signed_url)
            else:
                # Try to fetch as text for other types
                logger.info(f"📄 Processing file as text (extension: {file_extension})")
                try:
                    text = await self._fetch_text_from_url(signed_url)
                except Exception as e:
                    logger.error(f"❌ Unsupported file type: {file_extension}")
                    await self._mark_failed(source_id, f"Unsupported file type: {file_extension}")
                    return
            
            if not text or len(text.strip()) == 0:
                logger.error(f"❌ No text extracted from file for source {source_id}")
                await self._mark_failed(source_id, "No text extracted from file")
                return
            
            logger.info(f"✅ Text extraction completed: {len(text)} characters extracted")
            
            # Chunk and generate embeddings
            logger.info(f"🧠 Starting RAG ingestion process")
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
            
            logger.info(f"✅ RAG ingestion completed: Created {len(chunks)} chunks for source {source_id}")
            
            # Update source status to completed
            logger.info(f"🏁 Updating source status to 'completed'")
            await self.source_repo.update(source_id, status="completed")
            logger.info(f"🎉 Source {source_id} processing completed successfully!")
            logger.info(f"📊 Processing Summary:")
            logger.info(f"   • Source ID: {source_id}")
            logger.info(f"   • File type: {file_extension}")
            logger.info(f"   • Text extracted: {len(text)} characters")
            logger.info(f"   • Chunks created: {len(chunks)}")
            logger.info(f"   • Status: COMPLETED")
            
        except ValidationError as e:
            logger.error(f"❌ Validation error processing source {source_id}: {e}")
            await self._mark_failed(source_id, f"Validation error: {str(e)}")
        except ExternalServiceError as e:
            logger.error(f"❌ External service error processing source {source_id}: {e}")
            await self._mark_failed(source_id, f"Processing error: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error processing source {source_id}: {e}", exc_info=True)
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
        logger.info("📄 Starting PDF text extraction...")
        try:
            import fitz  # PyMuPDF
            import httpx
            
            # Use httpx to fetch the PDF content first
            # This is more robust than fitz.open(url) which can fail on some systems/URLs
            logger.info("📥 Fetching PDF content from URL...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(signed_url)
                response.raise_for_status()
                pdf_bytes = response.content
            logger.info(f"✅ PDF content fetched: {len(pdf_bytes)} bytes")
            
            # Open PDF from bytes
            logger.info("🔍 Opening PDF and extracting text...")
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            page_count = doc.page_count
            logger.info(f"📊 PDF has {page_count} pages")
            
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                text += page_text
                logger.info(f"   • Page {page_num + 1}: {len(page_text)} characters extracted")
            
            doc.close()
            logger.info(f"✅ PDF text extraction completed: {len(text)} total characters")
            return text
        except ImportError:
            logger.error("❌ PDF processing dependencies (PyMuPDF, httpx) not available")
            raise ExternalServiceError(
                "PDF processing dependencies (PyMuPDF, httpx) not available.",
                service_name="PDFProcessor",
            )
        except Exception as e:
            logger.error(f"❌ Failed to extract PDF from URL: {e}")
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
