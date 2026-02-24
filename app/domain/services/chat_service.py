"""Chat service for conversation management and message handling."""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.domain.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from app.domain.repositories.history_repository import HistoryRepository
from app.domain.repositories.notebook_repository import ChunkRepository
from app.domain.errors import NotFoundError, ForbiddenError
from app.domain.interfaces import ILLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatService:
    """
    Chat service managing conversations and messages.
    
    Responsibilities:
    - Create conversations
    - Manage messages within conversations
    - Authorization checks
    - History tracking
    - Orchestrate LLM generation (via ExternalProcessingService)
    """
    
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        history_repo: HistoryRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.history_repo = history_repo
    
    async def create_conversation(
        self,
        notebook_id: str,
        user_id: str,
        title: str,
        mode: str = "assistant",
        source_id: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation in a notebook.
        
        Args:
            notebook_id: Notebook this conversation belongs to
            user_id: User who created the conversation
            title: Conversation title
            mode: Chat mode (e.g., 'assistant', 'tutor', 'reviewer')
            source_id: Optional source context for the conversation
        """
        conversation = await self.conversation_repo.create(
            notebook_id=notebook_id,
            user_id=user_id,
            title=title,
            mode=mode,
            source_id=source_id,
        )
        
        logger.info(f"Conversation created: {conversation.id} in notebook: {notebook_id}")
        return conversation
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Conversation:
        """
        Get a conversation with authorization check.
        
        Raises:
            NotFoundError: conversation not found
            ForbiddenError: user not authorized
        """
        conversation = await self.conversation_repo.get_by_id_and_user(
            conversation_id,
            user_id,
        )
        if not conversation:
            raise NotFoundError(
                f"Conversation {conversation_id} not found or user not authorized",
                resource_type="Conversation",
                resource_id=conversation_id,
            )
        return conversation
    
    async def list_conversations(
        self,
        notebook_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Conversation]:
        """List conversations in a notebook."""
        # Could add user ownership check here if needed
        return await self.conversation_repo.list_by_notebook(
            notebook_id,
            skip=skip,
            limit=limit,
        )
    
    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        **updates,
    ) -> Conversation:
        """Update conversation metadata."""
        conversation = await self.get_conversation(conversation_id, user_id)
        
        # Allow updating only title and mode
        allowed_fields = {"title", "mode"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if filtered_updates:
            conversation = await self.conversation_repo.update(
                conversation_id,
                **filtered_updates,
            )
            logger.info(f"Conversation updated: {conversation_id}")
        
        return conversation
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation (cascade deletes messages)."""
        conversation = await self.get_conversation(conversation_id, user_id)
        
        success = await self.conversation_repo.delete(conversation_id)
        if success:
            logger.info(f"Conversation deleted: {conversation_id}")
        
        return success
    
    # ========================================================================
    # Message Management
    # ========================================================================
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        chunk_ids: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Target conversation
            user_id: User sending the message
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            chunk_ids: Associated chunk IDs for RAG context
            metadata: Additional message metadata
        """
        # Verify user has access to conversation
        conversation = await self.get_conversation(conversation_id, user_id)
        
        message = await self.message_repo.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
            chunk_ids=chunk_ids or [],
            metadata=metadata or {},
        )
        
        logger.info(f"Message added to conversation: {conversation_id}")
        return message
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """Get messages from a conversation."""
        # Verify access
        await self.get_conversation(conversation_id, user_id)
        
        return await self.message_repo.list_by_conversation(
            conversation_id,
            skip=skip,
            limit=limit,
        )
    
    async def delete_message(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
    ) -> bool:
        """Delete a message from a conversation."""
        # Verify user has access to conversation
        await self.get_conversation(conversation_id, user_id)
        
        message = await self.message_repo.get_by_id(message_id)
        if not message or message.conversation_id != conversation_id:
            raise NotFoundError(
                f"Message {message_id} not found",
                resource_type="Message",
                resource_id=message_id,
            )
        
        success = await self.message_repo.delete(message_id)
        if success:
            logger.info(f"Message deleted: {message_id}")
        
        return success
    
    # ========================================================================
    # History & Audit
    # ========================================================================
    
    async def record_chat_generation(
        self,
        user_id: str,
        conversation_id: str,
        notebook_id: str,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a chat generation in history for audit trail."""
        await self.history_repo.create(
            user_id=user_id,
            history_type="chat",
            title=title,
            content=content,
            content_preview=content[:200] if content else "",
            resource_id=conversation_id,
            notebook_id=notebook_id,
            metadata=metadata or {},
        )
        
        logger.info(f"Chat generation recorded: conversation {conversation_id}")
    
    # ========================================================================
    # RAG-Based Message Generation
    # ========================================================================
    
    async def send_message_with_rag(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        llm_client: ILLMClient,
        chunk_repo: ChunkRepository,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
    ) -> Message:
        """
        Send user message and get AI response with RAG context using vector search.
        """
        # 1. Get conversation and previous messages in parallel
        conversation_task = self.get_conversation(conversation_id, user_id)
        messages_task = self.get_conversation_messages(conversation_id, user_id, limit=10)
        
        conversation, previous_messages = await asyncio.gather(
            conversation_task,
            messages_task
        )
        
        # 3. RAG: Vector search for relevant chunks
        context_chunks = []
        chunk_ids = []
        
        logger.info(
            f"🔍 RAG Retrieval: Searching for chunks using embeddings saved during ingestion. "
            f"Query: '{user_message[:100]}...'"
        )
        
        try:
            relevant_chunks = await chunk_repo.search_by_text(
                query_text=user_message,
                notebook_id=conversation.notebook_id,
                source_id=conversation.source_id,
                top_k=top_k,
                llm_client=llm_client,
            )
            
            context_chunks = [chunk.plain_text for chunk in relevant_chunks]
            chunk_ids = [chunk.id for chunk in relevant_chunks]
            
            logger.info(
                f"✅ RAG Retrieval Success: Found {len(relevant_chunks)} chunks from embeddings. "
                f"Chunk IDs: {chunk_ids}. These chunks were saved with embeddings during document ingestion."
            )
            
            # Log details about each chunk being used
            for i, chunk in enumerate(relevant_chunks):
                similarity = chunk.metadata_.get('similarity_score', 'N/A') if chunk.metadata_ else 'N/A'
                logger.info(
                    f"   📄 Using chunk {i+1}/{len(relevant_chunks)}: "
                    f"id={chunk.id}, chunk_index={chunk.chunk_index}, "
                    f"similarity={similarity}, text_length={len(chunk.plain_text)}"
                )
        except Exception as e:
            logger.warning(f"❌ RAG search failed: {e}. Continuing without context.")
        
        # 4. Build context string
        context = "\n\n".join([
            f"[Chunk {i+1}]: {text}" 
            for i, text in enumerate(context_chunks)
        ]) if context_chunks else ""
        
        if context:
            logger.info(
                f"📝 Built RAG context from {len(context_chunks)} chunks "
                f"(saved with embeddings): total_context_length={len(context)} characters"
            )
        
        # 5. Build conversation history for LLM
        messages_for_llm = []
        if context:
            system_prompt = f"""You are a helpful assistant answering questions about the following content:

{context}

Answer based on the provided context. If the answer is not in the context, say so. Cite which chunk(s) you used when relevant."""
        else:
            system_prompt = "You are a helpful assistant. Answer questions clearly and concisely."
        
        messages_for_llm.append({"role": "system", "content": system_prompt})
        
        for msg in previous_messages[-5:]:
            messages_for_llm.append({"role": msg.role, "content": msg.content})
        
        messages_for_llm.append({"role": "user", "content": user_message})
        
        # 6. Generate AI response
        logger.info(
            f"🤖 Generating AI response using {len(context_chunks)} chunks "
            f"retrieved from embeddings (saved during document ingestion)"
        )
        
        try:
            assistant_response = await llm_client.generate_chat_response(
                messages=messages_for_llm,
                temperature=0.7,
            )
            
            logger.info(
                f"✅ AI response generated successfully using chunks from embeddings. "
                f"Response length: {len(assistant_response)} characters. "
                f"Chunks used: {chunk_ids}"
            )
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            assistant_response = "I apologize, but I'm having trouble generating a response right now."
        
        # 7. Store messages
        await self.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=user_message,
            chunk_ids=chunk_ids,
        )
        
        assistant_msg = await self.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_response,
            chunk_ids=chunk_ids,
        )
        
        return assistant_msg

    async def send_message_with_context(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        llm_client: ILLMClient,
        limit: int = 10,
    ) -> Message:
        """
        Send user message and get AI response using only conversation history.
        Picks a mode-specific system prompt based on conversation.mode (Gap 3).
        """
        conversation = await self.get_conversation(conversation_id, user_id)
        previous_messages = await self.get_conversation_messages(
            conversation_id, user_id, limit=limit
        )

        # ---- Mode-specific system prompts (Syntra Modes feature) -----------
        SYNTRA_PROMPTS = {
            "tutor": (
                "You are Syntra in Tutor Mode. Break down complex topics step by step. "
                "Use analogies, relatable examples, and Socratic questioning to guide the "
                "user toward understanding. Celebrate progress and encourage critical thinking."
            ),
            "fact-checker": (
                "You are Syntra in Fact-Checker Mode. Verify claims rigorously. "
                "Clearly separate confirmed facts from opinions or uncertain claims. "
                "Flag anything unverifiable and always note the basis for your assessment."
            ),
            "brainstormer": (
                "You are Syntra in Brainstormer Mode. Generate creative ideas, alternatives, "
                "and unexpected angles on the topic. Think laterally, challenge assumptions, "
                "and encourage the user to explore bold possibilities."
            ),
            "chat": (
                "You are Syntra, a helpful and intelligent AI learning assistant. "
                "Your goal is to help the user learn and understand complex topics. "
                "Explain concepts clearly, provide examples, and be encouraging."
            ),
        }
        DEFAULT_PROMPT = SYNTRA_PROMPTS["chat"]
        system_prompt = SYNTRA_PROMPTS.get(conversation.mode or "chat", DEFAULT_PROMPT)
        # --------------------------------------------------------------------

        messages_for_llm = [{"role": "system", "content": system_prompt}]

        for msg in previous_messages:
            messages_for_llm.append({"role": msg.role, "content": msg.content})

        messages_for_llm.append({"role": "user", "content": user_message})

        try:
            assistant_response = await llm_client.generate_chat_response(
                messages=messages_for_llm,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"Syntra generation failed: {e}")
            assistant_response = "I apologize, but I'm having trouble thinking right now."

        await self.add_message(conversation_id=conversation_id, user_id=user_id, role="user", content=user_message)

        assistant_msg = await self.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_response,
            metadata={"source": "syntra_contextual", "mode": conversation.mode or "chat"},
        )

        return assistant_msg
    
    # ========================================================================
    # Chat-to-Learning Tools Generation
    # ========================================================================
    
    async def generate_summary_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
        llm_client: ILLMClient,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """
        Generate a summary from the conversation messages.
        
        Args:
            conversation_id: The conversation to summarize
            user_id: User requesting the summary
            llm_client: LLM client for generation
            max_length: Maximum length of summary in characters
            style: Summary style ('concise', 'detailed', 'bullet_points')
            
        Returns:
            Generated summary text
        """
        # Get conversation and messages
        conversation = await self.get_conversation(conversation_id, user_id)
        messages = await self.get_conversation_messages(conversation_id, user_id)
        
        # Build content from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        content = "\n\n".join(content_parts)
        
        if not content.strip():
            raise ValueError("No content available to summarize from conversation")
        
        # Generate summary using LLM
        summary = await llm_client.generate_summary(
            content=content,
            max_length=max_length,
            style=style,
        )
        
        # Record in history
        await self.record_chat_generation(
            user_id=user_id,
            conversation_id=conversation_id,
            notebook_id=conversation.notebook_id,
            title=f"Summary: {conversation.title}",
            content=summary,
            metadata={
                "type": "summary_from_conversation", 
                "style": style, 
                "max_length": max_length
            },
        )
        
        return summary
    
    async def generate_quiz_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
        llm_client: ILLMClient,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """
        Generate a quiz from the conversation messages.
        
        Args:
            conversation_id: The conversation to generate quiz from
            user_id: User requesting the quiz
            llm_client: LLM client for generation
            topic: Topic for the quiz
            num_questions: Number of questions to generate
            difficulty: Difficulty level of questions
            
        Returns:
            List of quiz questions
        """
        # Get conversation and messages
        conversation = await self.get_conversation(conversation_id, user_id)
        messages = await self.get_conversation_messages(conversation_id, user_id)
        
        # Build content from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        content = "\n\n".join(content_parts)
        
        if not content.strip():
            raise ValueError("No content available to generate quiz from conversation")
        
        # Generate quiz using LLM
        quiz = await llm_client.generate_quiz(
            content=content,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        
        # Record in history
        await self.record_chat_generation(
            user_id=user_id,
            conversation_id=conversation_id,
            notebook_id=conversation.notebook_id,
            title=f"Quiz: {topic}",
            content=str(quiz),
            metadata={
                "type": "quiz_from_conversation",
                "topic": topic,
                "num_questions": num_questions,
                "difficulty": difficulty
            },
        )
        
        return quiz
    
    async def generate_study_guide_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
        llm_client: ILLMClient,
        topic: Optional[str] = None,
        format: str = "structured",
    ) -> str:
        """
        Generate a study guide from the conversation messages.
        
        Args:
            conversation_id: The conversation to generate study guide from
            user_id: User requesting the study guide
            llm_client: LLM client for generation
            topic: Optional topic for the study guide
            format: Format of the study guide ('structured', 'outline', 'detailed')
            
        Returns:
            Generated study guide text
        """
        # Get conversation and messages
        conversation = await self.get_conversation(conversation_id, user_id)
        messages = await self.get_conversation_messages(conversation_id, user_id)
        
        # Build content from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        content = "\n\n".join(content_parts)
        
        if not content.strip():
            raise ValueError("No content available to generate study guide from conversation")
        
        # Generate study guide using LLM
        study_guide = await llm_client.generate_study_guide(
            content=content,
            topic=topic or conversation.title,
            format=format,
        )
        
        # Record in history
        await self.record_chat_generation(
            user_id=user_id,
            conversation_id=conversation_id,
            notebook_id=conversation.notebook_id,
            title=f"Study Guide: {topic or conversation.title}",
            content=study_guide,
            metadata={
                "type": "study_guide_from_conversation",
                "format": format,
                "topic": topic or conversation.title
            },
        )
        
        return study_guide
    
    async def generate_mindmap_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
        llm_client: ILLMClient,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate a mindmap from the conversation messages.
        
        Args:
            conversation_id: The conversation to generate mindmap from
            user_id: User requesting the mindmap
            llm_client: LLM client for generation
            format: Format of the mindmap ('json', 'markdown', 'mermaid')
            
        Returns:
            Generated mindmap structure
        """
        # Get conversation and messages
        conversation = await self.get_conversation(conversation_id, user_id)
        messages = await self.get_conversation_messages(conversation_id, user_id)
        
        # Build content from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        content = "\n\n".join(content_parts)
        
        if not content.strip():
            raise ValueError("No content available to generate mindmap from conversation")
        
        # Generate mindmap using LLM
        mindmap = await llm_client.generate_mindmap(
            content=content,
            format=format,
        )
        
        # Record in history
        await self.record_chat_generation(
            user_id=user_id,
            conversation_id=conversation_id,
            notebook_id=conversation.notebook_id,
            title=f"Mindmap: {conversation.title}",
            content=str(mindmap),
            metadata={
                "type": "mindmap_from_conversation",
                "format": format
            },
        )
        
        return mindmap

    async def generate_flashcards_from_conversation(
        self,
        conversation_id: str,
        user_id: str,
        llm_client: ILLMClient,
        topic: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Generate flashcards from the conversation messages.
        
        Args:
            conversation_id: The conversation to generate flashcards from
            user_id: User requesting the flashcards
            llm_client: LLM client for generation
            topic: Optional topic for the flashcards
            
        Returns:
            List of flashcards with front/back pairs
        """
        # Get conversation and messages
        conversation = await self.get_conversation(conversation_id, user_id)
        messages = await self.get_conversation_messages(conversation_id, user_id)
        
        # Build content from messages
        content_parts = []
        for msg in messages:
            content_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        content = "\n\n".join(content_parts)
        
        if not content.strip():
            raise ValueError("No content available to generate flashcards from conversation")
        
        # Create prompt for flashcard generation
        prompt = f"""
        Create flashcards from the following conversation content. 
        Each flashcard should have a front (question or term) and back (answer or definition).
        Make them educational and focused on key concepts discussed.
        
        Content:
        {content}
        
        Topic: {topic or conversation.title}
        
        Return in the following format:
        {{
            "flashcards": [
                {{"front": "question/term", "back": "answer/definition"}},
                {{"front": "question/term", "back": "answer/definition"}}
            ]
        }}
        """
        
        try:
            # Generate flashcards using LLM chat response
            response = await llm_client.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000,
            )
            
            # Parse the response - try to extract JSON
            import re
            import json
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    parsed = json.loads(json_str)
                    flashcards = parsed.get("flashcards", [])
                except json.JSONDecodeError:
                    # If JSON parsing fails, create simple flashcards from content
                    sentences = [s.strip() for s in content.split('.') if s.strip()]
                    flashcards = []
                    for i in range(0, min(len(sentences), 10), 2):
                        if i + 1 < len(sentences):
                            flashcards.append({
                                "front": sentences[i][:100] + "..." if len(sentences[i]) > 100 else sentences[i],
                                "back": sentences[i + 1][:150] + "..." if len(sentences[i + 1]) > 150 else sentences[i + 1]
                            })
            else:
                # Fallback to simple extraction
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                flashcards = []
                for i in range(0, min(len(sentences), 10), 2):
                    if i + 1 < len(sentences):
                        flashcards.append({
                            "front": sentences[i][:100] + "..." if len(sentences[i]) > 100 else sentences[i],
                            "back": sentences[i + 1][:150] + "..." if len(sentences[i + 1]) > 150 else sentences[i + 1]
                        })
        except Exception as e:
            logger.error(f"Error generating flashcards: {e}")
            # Fallback response
            sentences = [s.strip() for s in content.split('.') if s.strip()][:5]
            flashcards = []
            for i, sentence in enumerate(sentences):
                flashcards.append({
                    "front": f"What is concept {i+1}?",
                    "back": sentence[:150] + "..." if len(sentence) > 150 else sentence
                })
        
        # Record in history
        await self.record_chat_generation(
            user_id=user_id,
            conversation_id=conversation_id,
            notebook_id=conversation.notebook_id,
            title=f"Flashcards: {topic or conversation.title}",
            content=str(flashcards),
            metadata={
                "type": "flashcards_from_conversation",
                "topic": topic or conversation.title
            },
        )
        
        return flashcards

