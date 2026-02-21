"""Utility functions for document processing."""

import logging
import re
from typing import Dict
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


async def extract_text_from_url(url: str) -> Dict[str, str]:
    """
    Extract text content from a URL.
    
    Args:
        url: URL to extract content from
        
    Returns:
        Dict with 'text' and 'title' keys
        
    Raises:
        ValueError: If URL is invalid or content extraction fails
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise ValueError(
                "Invalid URL protocol. Only HTTP and HTTPS are supported."
            )
        
        # Fetch with timeout and proper headers
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
            )
            
            if not response.is_success:
                if response.status_code == 404:
                    raise ValueError(
                        "The URL was not found (404). Please check that the URL is correct and accessible."
                    )
                elif response.status_code == 403:
                    raise ValueError(
                        "Access to this URL is forbidden (403). The website may require authentication or block automated access."
                    )
                elif response.status_code == 401:
                    raise ValueError(
                        "This URL requires authentication (401). Please ensure the URL is publicly accessible."
                    )
                else:
                    raise ValueError(
                        f"Failed to fetch URL: {response.status_code} {response.status_text}"
                    )
            
            html = response.text
            
            # Extract title
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else url
            
            # Improved HTML to text conversion
            text = html
            
            # Remove script and style tags
            text = re.sub(
                r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(
                r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(
                r"<noscript\b[^<]*(?:(?!</noscript>)<[^<]*)*</noscript>",
                "",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            
            # Remove comments
            text = re.sub(r"<!--[\s\S]*?-->", "", text)
            
            # Convert common HTML entities
            text = text.replace("&nbsp;", " ")
            text = text.replace("&amp;", "&")
            text = text.replace("&lt;", "<")
            text = text.replace("&gt;", ">")
            text = text.replace("&quot;", '"')
            text = text.replace("&#39;", "'")
            
            # Replace block elements with newlines
            text = re.sub(
                r"</?(?:div|p|br|h[1-6]|li|tr|td|th|article|section|header|footer|nav|aside)[^>]*>",
                "\n",
                text,
                flags=re.IGNORECASE,
            )
            
            # Remove all remaining HTML tags
            text = re.sub(r"<[^>]+>", " ", text)
            
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
            
            if not text or len(text) < 50:
                raise ValueError(
                    "Extracted content is too short. The URL might not contain readable text content."
                )
            
            return {"text": text.strip(), "title": title}
            
    except httpx.TimeoutException:
        raise ValueError("Request timeout. The URL took too long to respond.")
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch URL: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting text from URL: {e}", exc_info=True)
        raise ValueError(f"Failed to extract content from URL: {str(e)}")


def process_text_content(text: str) -> str:
    """
    Process and validate text content.
    
    Args:
        text: Raw text content
        
    Returns:
        Processed text
        
    Raises:
        ValueError: If text is invalid or too short
    """
    if not text or not isinstance(text, str):
        raise ValueError("Invalid text content provided")
    
    # Remove excessive whitespace
    processed = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n{3,}", "\n\n")
        .strip()
    )
    
    if len(processed) < 10:
        raise ValueError(
            "Text content is too short. Please provide at least 10 characters."
        )
    
    # Limit text size to prevent issues (10MB max)
    MAX_TEXT_LENGTH = 10 * 1024 * 1024
    if len(processed) > MAX_TEXT_LENGTH:
        processed = processed[:MAX_TEXT_LENGTH]
        logger.warning(f"Text content truncated to {MAX_TEXT_LENGTH} characters")
    
    return processed


def get_file_type(filename: str, mime_type: str = None) -> str:
    """
    Get file type from filename and mime type.
    
    Args:
        filename: File name
        mime_type: Optional MIME type
        
    Returns:
        File type string (pdf, text, document, etc.)
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    
    if mime_type:
        if "pdf" in mime_type.lower():
            return "pdf"
        if "word" in mime_type.lower() or "document" in mime_type.lower():
            return "document"
        if "text" in mime_type.lower() or "plain" in mime_type.lower():
            return "text"
    
    if ext == "pdf":
        return "pdf"
    elif ext in ["txt", "md", "markdown"]:
        return "text"
    elif ext in ["doc", "docx"]:
        return "document"
    else:
        return "file"
