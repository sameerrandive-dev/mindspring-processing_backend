"""Mock LLM client for testing."""

from typing import List, Dict, Any, Optional
import logging
from app.domain.interfaces import ILLMClient

logger = logging.getLogger(__name__)


class MockLLMClient(ILLMClient):
    """Mock LLM client for testing without actual API calls."""
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate mock chat response."""
        logger.info("Mock LLM: generating chat response")
        return "This is a mock response from the LLM service."
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
    ) -> List[List[float]]:
        """Generate mock embeddings."""
        logger.info(f"Mock LLM: generating embeddings for {len(texts)} texts")
        # Return dummy embeddings of size 1536 (standard OpenAI embedding size)
        return [[0.1] * 1536 for _ in texts]
    
    async def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Generate mock quiz questions."""
        logger.info(f"Mock LLM: generating {num_questions} quiz questions")
        return [
            {
                "question": f"Question {i+1}?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "difficulty": difficulty,
            }
            for i in range(num_questions)
        ]
    
    async def generate_summary(
        self,
        content: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """Generate mock summary."""
        logger.info(f"Mock LLM: generating {style} summary (max {max_length} chars)")
        
        # Mock summary based on style
        if style == "bullet_points":
            return f"""Summary of content:
• Key point 1 from the content
• Key point 2 from the content
• Key point 3 from the content"""
        elif style == "detailed":
            return f"This is a detailed summary of the content. It covers all major points and provides comprehensive information about the topic. The content discusses various aspects and provides in-depth analysis."
        else:  # concise
            return f"Brief summary: This content covers important topics and key concepts in a concise manner."

    async def generate_study_guide(
        self,
        content: str,
        topic: Optional[str] = None,
        format: str = "structured",
    ) -> str:
        """Generate mock study guide."""
        logger.info(f"Mock LLM: generating {format} study guide for topic: {topic or 'untitled'}")
        
        guide_title = topic or "Study Guide"
        
        if format == "outline":
            return f"""# {guide_title} - Outline

## I. Introduction
- Overview of key concepts

## II. Main Topics
- Topic 1
- Topic 2
- Topic 3

## III. Key Takeaways
- Important point 1
- Important point 2"""
        
        elif format == "detailed":
            return f"""# {guide_title}

## Introduction
This study guide provides comprehensive coverage of the material.

## Section 1: Core Concepts
Detailed explanation of core concepts and their applications.

## Section 2: Advanced Topics
In-depth discussion of advanced topics and their relationships.

## Summary
Key takeaways and important points to remember."""
        
        else:  # structured
            return f"""# {guide_title}

## Overview
Comprehensive study guide covering all essential topics.

## Key Concepts
1. Concept 1: Explanation
2. Concept 2: Explanation
3. Concept 3: Explanation

## Study Tips
- Review key concepts regularly
- Practice with examples
- Focus on understanding relationships"""
    
    async def generate_mindmap(
        self,
        content: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Generate mock mindmap."""
        logger.info(f"Mock LLM: generating mindmap in {format} format")
        
        if format == "mermaid":
            return {"content": """graph TD
    A[Main Topic] --> B[Subtopic 1]
    A --> C[Subtopic 2]
    A --> D[Subtopic 3]
    B --> E[Detail 1]
    B --> F[Detail 2]
    C --> G[Detail 3]"""}
        
        elif format == "markdown":
            return {"content": """# Main Topic
- Subtopic 1
  - Detail 1
  - Detail 2
- Subtopic 2
  - Detail 3
- Subtopic 3"""}
        
        else:  # json
            return {
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
                        },
                        {
                            "id": "node2",
                            "label": "Subtopic 2",
                            "children": [
                                {"id": "leaf3", "label": "Detail 3"}
                            ]
                        },
                        {
                            "id": "node3",
                            "label": "Subtopic 3"
                        }
                    ]
                }
            }
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return True
