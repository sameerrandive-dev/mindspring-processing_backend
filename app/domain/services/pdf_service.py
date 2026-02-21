"""PDF processing service for document extraction."""

import logging
from typing import Optional, List

from app.domain.errors import ExternalServiceError
from app.domain.interfaces import IPdfProcessor

logger = logging.getLogger(__name__)


class PdfService:
    """
    PDF processing service for text extraction.
    
    Responsibilities:
    - Extract text from PDFs
    - Parse page structure
    - Handle processing errors
    - Integrate with PDF processors (PyMuPDF, docling, etc.)
    """
    
    def __init__(self, pdf_processor: IPdfProcessor):
        self.pdf_processor = pdf_processor
    
    async def extract_text(self, file_path: str) -> str:
        """
        Extract all text from a PDF file.
        
        Raises:
            ExternalServiceError: PDF processing failed
        """
        try:
            text = await self.pdf_processor.extract_text(file_path)
            logger.info(f"Text extracted from PDF: {file_path} ({len(text)} chars)")
            return text
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to extract text from PDF",
                service_name="PDFProcessor",
                original_error=e,
            )
    
    async def extract_pages(self, file_path: str) -> List[dict]:
        """
        Extract pages with page numbers and content.
        
        Returns:
            List of dicts with 'page_number', 'text', 'metadata'
        """
        try:
            pages = await self.pdf_processor.extract_pages(file_path)
            logger.info(f"Pages extracted from PDF: {file_path} ({len(pages)} pages)")
            return pages
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to extract pages from PDF",
                service_name="PDFProcessor",
                original_error=e,
            )
