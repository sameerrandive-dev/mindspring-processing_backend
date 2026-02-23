"""Real LLM client implementation using NeevCloud/OpenAI API."""

import httpx
import json
import hashlib
import asyncio
import time
from typing import List, Dict, Any, Optional
import logging
from app.domain.interfaces import ILLMClient, ICacheProvider
from app.core.config import settings
from app.infrastructure.monitoring.logging_setup import log_performance

logger = logging.getLogger(__name__)


class RealLLMClient(ILLMClient):
    """Real LLM client using NeevCloud/OpenAI-compatible API."""
    
    def __init__(self, cache_provider: Optional[ICacheProvider] = None):
        self.base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL or "gpt-4"
        self.embedding_model = settings.EMBEDDING_MODEL or "text-embedding-3-small"
        self.embedding_endpoint = settings.EMBEDDING_ENDPOINT or f"{self.base_url}/embeddings"
        self.chat_endpoint = settings.AI_API_ENDPOINT or f"{self.base_url}/chat/completions"
        # Use EMBEDDING_MODEL_KEY for Nebius specifically, fallback to general API key
        self.embedding_api_key = settings.EMBEDDING_MODEL_KEY or settings.NEEVCLOUD_API_KEY or self.api_key
        self.cache_provider = cache_provider
        
        # Create persistent HTTP client with connection pooling
        self._http_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0,
            ),
        )
        
        # Cache TTLs
        self.cache_ttl_chat = getattr(settings, 'CACHE_TTL_CHAT_SECONDS', 600)  # 10 minutes
        self.cache_ttl_embedding = getattr(settings, 'CACHE_TTL_EMBEDDING_SECONDS', 86400)  # 24 hours
        self.max_concurrent_batches = getattr(settings, 'EMBEDDING_MAX_CONCURRENT_BATCHES', 3)
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - LLM calls will fail")

    # -----------------------------------------------------------------------
    # Difficulty mapping — supports FEATURES.md names and legacy aliases
    # -----------------------------------------------------------------------
    DIFFICULTY_MAP: Dict[str, str] = {
        "novice":       "easy (introductory — core definitions and broad concepts)",
        "intermediate": "intermediate (relationships between ideas, process-based questions)",
        "master":       "advanced (deep inference, complex synthesis, expert-level reasoning)",
        # legacy aliases
        "easy":   "easy (introductory)",
        "medium": "intermediate",
        "hard":   "advanced",
    }

    def _resolve_difficulty(self, difficulty: str) -> str:
        """Map user-facing difficulty label to a descriptive LLM prompt phrase."""
        return self.DIFFICULTY_MAP.get(difficulty.lower(), difficulty)
    
    def _generate_cache_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data using MD5 hash."""
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self._http_client.aclose()
    
    async def close(self):
        """Close HTTP client connections."""
        await self._http_client.aclose()
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate chat response from LLM with caching."""
        # Build messages with system prompt
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)
        
        # Check cache (only for temperature <= 0.7 to ensure consistency)
        cache_key = None
        if self.cache_provider and temperature <= 0.7:
            cache_key = self._generate_cache_key(
                "llm:chat",
                {
                    "messages": chat_messages,
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            cached_response = await self.cache_provider.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for LLM chat response")
                log_performance(logger, "llm_chat_cache_hit", 0.001, resource="cache")
                return cached_response
        
        # Generate response from API
        start_time = time.time()
        try:
            response = await self._http_client.post(
                self.chat_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": chat_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data["choices"][0]["message"]["content"]
            
            # Log performance
            duration = time.time() - start_time
            log_performance(logger, "llm_chat_api_call", duration, resource="llm_api")
            
            # Cache the response
            if self.cache_provider and cache_key and temperature <= 0.7:
                await self.cache_provider.set(cache_key, result, ttl_seconds=self.cache_ttl_chat)
            
            return result
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            log_performance(logger, "llm_chat_api_error", duration, resource="llm_api")
            logger.error(f"HTTP error in generate_chat_response: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected response format: {e}")
            raise ValueError(f"Invalid response from LLM API: {e}")
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 20,
    ) -> List[List[float]]:
        """
        Generate embeddings for texts with caching and parallel batch processing.
        
        Args:
            texts: List of strings to embed
            model: Embedding model name
            batch_size: Number of texts per API request
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        start_time = time.time()
        embedding_model = model or self.embedding_model
        
        # Check cache for each text
        texts_to_embed = []
        indices_to_embed = []
        all_embeddings = [None] * len(texts)
        cache_hits = 0
        cache_keys = None
        
        if self.cache_provider:
            cache_keys = [
                self._generate_cache_key(f"embed:{embedding_model}", text)
                for text in texts
            ]
            cached_results = await asyncio.gather(*[
                self.cache_provider.get(key) for key in cache_keys
            ], return_exceptions=True)
            
            for i, (text, cached, cache_key) in enumerate(zip(texts, cached_results, cache_keys)):
                if isinstance(cached, Exception):
                    logger.warning(f"Cache read error for text {i}: {cached}")
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
                elif cached:
                    all_embeddings[i] = cached
                    cache_hits += 1
                else:
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
        else:
            # No cache provider - embed all texts
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))
        
        if cache_hits > 0:
            logger.info(f"Cache hits: {cache_hits}/{len(texts)} embeddings")
            log_performance(logger, "embedding_cache_hits", 0.001, extra_data={"hits": cache_hits, "total": len(texts)})
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            new_embeddings = await self._generate_embeddings_uncached(
                texts_to_embed, embedding_model, batch_size
            )
            
            # Store new embeddings in cache and fill results array
            if self.cache_provider and cache_keys:
                cache_tasks = []
                for idx, embedding in zip(indices_to_embed, new_embeddings):
                    all_embeddings[idx] = embedding
                    cache_key = cache_keys[idx]
                    cache_tasks.append(
                        self.cache_provider.set(
                            cache_key, embedding, ttl_seconds=self.cache_ttl_embedding
                        )
                    )
                # Cache writes can be done asynchronously
                await asyncio.gather(*cache_tasks, return_exceptions=True)
            else:
                for idx, embedding in zip(indices_to_embed, new_embeddings):
                    all_embeddings[idx] = embedding
        
        duration = time.time() - start_time
        log_performance(logger, "embedding_generation", duration, extra_data={
            "total": len(texts),
            "cached": cache_hits,
            "generated": len(texts_to_embed)
        })
        
        return [e for e in all_embeddings if e is not None]
    
    async def _generate_embeddings_uncached(
        self,
        texts: List[str],
        model: str,
        batch_size: int,
    ) -> List[List[float]]:
        """
        Generate embeddings for texts without caching (core logic).
        Processes batches concurrently with semaphore limiting.
        """
        if not texts:
            return []
        
        # Create batches
        batches = [
            texts[i : i + batch_size]
            for i in range(0, len(texts), batch_size)
        ]
        
        logger.info(f"📦 Splitting {len(texts)} texts into {len(batches)} batches (batch size: {batch_size})")
        
        async def process_batch(batch: List[str], batch_num: int) -> List[List[float]]:
            """Process a single batch."""
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"🚀 Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} texts), attempt {attempt + 1}")
                    
                    logger.info(f"📤 Sending embedding request to: {self.embedding_endpoint}")
                    logger.info(f"📝 Batch size: {len(batch)}, Model: {model}")
                    
                    response = await self._http_client.post(
                        self.embedding_endpoint,
                        headers={
                            "Authorization": f"Bearer {self.embedding_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "input": batch,
                        },
                    )
                    
                    logger.info(f"📥 Received response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        response.raise_for_status()
                        data = response.json()
                        
                        # Handle both OpenAI format and other formats
                        if "data" in data:
                            embeddings = [item["embedding"] for item in data["data"]]
                        elif isinstance(data, list):
                            embeddings = [item["embedding"] for item in data]
                        else:
                            raise ValueError("Unexpected embedding response format")
                        
                        logger.info(f"✅ Batch {batch_num + 1} completed: Generated {len(embeddings)} embeddings")
                        return embeddings
                    else:
                        logger.error(f"❌ Nebius API error {response.status_code} for {self.embedding_endpoint}: {response.text}")
                        # More detailed error reporting for debugging
                        if response.status_code == 401:
                            logger.error("⚠️  Authorization error - check your API key is correct")
                        elif response.status_code == 402:
                            logger.error("⚠️  Payment required - check your Nebius account billing status")
                        elif response.status_code == 403:
                            logger.error("⚠️  Forbidden - check your API key permissions")
                        elif response.status_code == 429:
                            logger.error("⚠️  Rate limit exceeded - will retry after delay")
                        else:
                            logger.error(f"⚠️  Other error - check API endpoint and credentials")
                        
                        # Don't retry on certain error codes
                        if response.status_code in [401, 403, 402]:  # Authentication/permission errors
                            raise Exception(f"API authentication error: {response.status_code}")
                        
                        # Retry on rate limit or server errors
                        if attempt < max_retries - 1 and response.status_code in [429, 500, 502, 503, 504]:
                            logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # exponential backoff
                        else:
                            response.raise_for_status()  # Will raise the actual error if we're out of retries
                
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        logger.error(f"❌ Final error processing embedding batch {batch_num + 1} after {max_retries} attempts: {e}")
                        raise
                    else:
                        logger.warning(f"⚠️  Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # exponential backoff
            
            raise Exception(f"Failed to process batch after {max_retries} attempts")
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def process_with_semaphore(batch, batch_num):
            async with semaphore:
                return await process_batch(batch, batch_num)
        
        # Process all batches concurrently (with limit)
        logger.info(f"⚡ Starting concurrent embedding generation for {len(batches)} batches")
        results = await asyncio.gather(*[
            process_with_semaphore(batch, i)
            for i, batch in enumerate(batches)
        ])
        
        # Flatten results
        final_embeddings = [embedding for batch_result in results for embedding in batch_result]
        logger.info(f"🎯 Embedding generation completed: {len(final_embeddings)} total embeddings generated")
        return final_embeddings
    
    async def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions from content."""
        difficulty_label = self._resolve_difficulty(difficulty)
        prompt = f"""Generate {num_questions} quiz questions at {difficulty_label} difficulty based on the following content.

Content:
{content[:4000]}  # Limit content length

Format each question as JSON with:
- question: The question text
- options: Array of 4 options [A, B, C, D]
- correct_answer: The correct option letter (A, B, C, or D)
- explanation: Brief explanation of the correct answer

Return only a JSON array of questions, no other text. Example format:
[
  {{
    "question": "What is...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "A",
    "explanation": "Explanation here"
  }}
]"""

        try:
            response_text = await self.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse JSON response
            # Extract JSON from response (handle markdown code blocks)
            json_str = response_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            questions = json.loads(json_str)
            if not isinstance(questions, list):
                questions = [questions]
            
            # Validate question format
            for q in questions:
                if not all(key in q for key in ["question", "options", "correct_answer"]):
                    logger.warning(f"Invalid question format: {q}")
            
            return questions
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {response_text[:200]}")
            raise ValueError(f"LLM returned invalid JSON for quiz questions: {e}")
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            raise
    
    async def generate_summary(
        self,
        content: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """Generate summary from content."""
        style_instructions = {
            "concise": "Provide a brief, concise summary",
            "detailed": "Provide a comprehensive, detailed summary covering all major points",
            "bullet_points": "Provide a summary in bullet point format with key points"
        }
        
        # Limit content length to avoid token limits (roughly 1500 tokens)
        content_preview = content[:6000] if len(content) > 6000 else content
        
        prompt = f"""{style_instructions.get(style, 'Summarize')} the following content in approximately {max_length} characters.

Content:
{content_preview}

Summary:"""

        try:
            summary = await self.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=min(max_length // 2, 1000),  # Approximate token count
            )
            
            return summary.strip()
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise
    
    async def generate_study_guide(
        self,
        content: str,
        topic: Optional[str] = None,
        format: str = "structured",
    ) -> str:
        """Generate study guide from content."""
        format_instructions = {
            "structured": "Create a well-structured study guide with clear sections, headings, and organized content. Include key concepts, definitions, and important points.",
            "outline": "Create a detailed outline format with hierarchical structure using headings and subheadings. Focus on organization and structure.",
            "detailed": "Create a comprehensive, detailed study guide with in-depth explanations, examples, and thorough coverage of all topics."
        }
        
        topic_part = f" about '{topic}'" if topic else ""
        
        # Limit content length
        content_preview = content[:8000] if len(content) > 8000 else content
        
        prompt = f"""Create a {format_instructions.get(format, 'structured')} study guide{topic_part} based on the following content.

Content:
{content_preview}

Study Guide:"""

        try:
            guide = await self.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=4000,
            )
            
            return guide.strip()
        except Exception as e:
            logger.error(f"Error generating study guide: {e}")
            raise
    
    async def generate_mindmap(
        self,
        content: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Generate mindmap structure from content."""
        format_instructions = {
            "json": """Return a JSON object with hierarchical structure. Format:
{
  "root": {
    "id": "root",
    "label": "Main Topic",
    "children": [
      {
        "id": "node1",
        "label": "Subtopic 1",
        "children": [
          {"id": "leaf1", "label": "Detail 1"},
          {"id": "leaf2", "label": "Detail 2"}
        ]
      }
    ]
  }
}""",
            "mermaid": "Return Mermaid diagram syntax for a mindmap. Use 'graph TD' or 'mindmap' format.",
            "markdown": "Return a markdown-formatted hierarchical list with proper indentation."
        }
        
        # Limit content length
        content_preview = content[:6000] if len(content) > 6000 else content
        
        prompt = f"""Analyze the following content and create a mindmap in {format} format.

Content:
{content_preview}

{format_instructions.get(format, 'Create a structured mindmap')}.

Return only the {format} output, no additional explanation."""

        try:
            response = await self.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=2000,
            )
            
            if format == "json":
                # Extract JSON from response
                json_str = response.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse mindmap JSON: {response[:200]}")
                    # Return a fallback structure
                    return {
                        "root": {
                            "id": "root",
                            "label": "Content Analysis",
                            "children": []
                        }
                    }
            else:
                # For markdown/mermaid, return as string in dict
                return {"content": response.strip()}
        except Exception as e:
            logger.error(f"Error generating mindmap: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Health check for LLM provider."""
        try:
            # Simple test call
            response = await self.generate_chat_response(
                messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
                max_tokens=10,
            )
            return bool(response and len(response) > 0)
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
