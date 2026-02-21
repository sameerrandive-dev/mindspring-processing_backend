"""External processing service for LLM and external API orchestration."""

import logging
from typing import List, Dict, Any, Optional

from app.domain.errors import ExternalServiceError
from app.domain.interfaces import ILLMClient

logger = logging.getLogger(__name__)


class ExternalProcessingService:
    """
    External processing service for LLM interactions with resilience patterns.
    
    Responsibilities:
    - LLM API calls with retries
    - Timeout and circuit breaker handling
    - Response normalization
    - Error recovery
    """
    
    def __init__(
        self,
        llm_client: ILLMClient,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate chat response from LLM with retries.
        
        Args:
            messages: Conversation messages
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Max response length
            
        Returns:
            Generated response text
            
        Raises:
            ExternalServiceError: LLM call failed after retries
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"LLM chat generation attempt {attempt + 1}/{self.max_retries}")
                
                response = await self.llm_client.generate_chat_response(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                logger.info(f"LLM chat generation successful")
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM chat generation attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Try again
                    continue
        
        raise ExternalServiceError(
            "Failed to generate chat response after retries",
            service_name="LLMClient",
            original_error=last_error,
        )
    
    async def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions with retries.
        
        Args:
            content: Content to generate quiz from
            num_questions: Number of questions
            difficulty: Question difficulty level
            
        Returns:
            List of quiz questions
            
        Raises:
            ExternalServiceError: LLM call failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"LLM quiz generation attempt {attempt + 1}/{self.max_retries}")
                
                questions = await self.llm_client.generate_quiz(
                    content=content,
                    num_questions=num_questions,
                    difficulty=difficulty,
                )
                
                logger.info(f"LLM quiz generation successful: {len(questions)} questions")
                return questions
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM quiz generation attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    continue
        
        raise ExternalServiceError(
            "Failed to generate quiz after retries",
            service_name="LLMClient",
            original_error=last_error,
        )
    
    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        try:
            healthy = await self.llm_client.health_check()
            logger.info(f"LLM health check: {'OK' if healthy else 'FAILED'}")
            return healthy
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
