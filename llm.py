"""
LLM Integration Module for the Automated Book Generation System.
Supports OpenAI, Anthropic (Claude), and Google Gemini.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import json

import config


# =============================================================================
# ABSTRACT LLM INTERFACE
# =============================================================================

class LLMInterface(ABC):
    """Abstract base class for LLM operations."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Generate text based on prompt."""
        pass
    
    @abstractmethod
    def generate_with_web_search(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text with web search capability (if available)."""
        pass


# =============================================================================
# OPENAI IMPLEMENTATION
# =============================================================================

class OpenAIClient(LLMInterface):
    """OpenAI API client implementation."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.OPENAI_MODEL
        self.client = None
        
    def _get_client(self):
        """Get OpenAI client."""
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self.client
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Generate text using OpenAI."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=config.TEMPERATURE
        )
        
        return response.choices[0].message.content
    
    def generate_with_web_search(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate text with web search using OpenAI's web search enabled models.
        Falls back to regular generation if web search is not available.
        """
        client = self._get_client()
        
        # Try using a web-search enabled model
        web_search_model = "gpt-4o-search-preview"  # or similar web-enabled model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat.completions.create(
                model=web_search_model,
                messages=messages,
                temperature=config.TEMPERATURE
            )
            return response.choices[0].message.content
        except Exception:
            # Fall back to regular generation
            return self.generate(prompt, system_prompt)


# =============================================================================
# ANTHROPIC IMPLEMENTATION
# =============================================================================

class AnthropicClient(LLMInterface):
    """Anthropic Claude API client implementation."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model = model or config.ANTHROPIC_MODEL
        self.client = None
        
    def _get_client(self):
        """Get Anthropic client."""
        if self.client is None:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install anthropic: pip install anthropic")
        return self.client
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Generate text using Anthropic Claude."""
        client = self._get_client()
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = client.messages.create(**kwargs)
        
        return response.content[0].text
    
    def generate_with_web_search(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate text - Anthropic doesn't have native web search.
        Falls back to regular generation.
        """
        # Anthropic doesn't have built-in web search
        # Could integrate with external search API here
        return self.generate(prompt, system_prompt)


# =============================================================================
# GOOGLE GEMINI IMPLEMENTATION
# =============================================================================

class GeminiClient(LLMInterface):
    """Google Gemini API client implementation."""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.GEMINI_MODEL
        self.client = None
        
    def _get_client(self):
        """Get Gemini client."""
        if self.client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
        return self.client
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Generate text using Google Gemini."""
        client = self._get_client()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = client.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": config.TEMPERATURE
            }
        )
        
        return response.text
    
    def generate_with_web_search(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate text with web search using Gemini.
        Note: Gemini has built-in knowledge but external search integration
        would need to be added separately.
        """
        return self.generate(prompt, system_prompt)


# =============================================================================
# OLLAMA (LOCAL) IMPLEMENTATION
# =============================================================================

class OllamaClient(LLMInterface):
    """Ollama local LLM client implementation (FREE - runs locally)."""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL
        
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 1500) -> str:
        """Generate text using Ollama."""
        import requests
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Use smaller token limit for faster generation
        token_limit = min(max_tokens, 1500)
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": token_limit,
                    "temperature": config.TEMPERATURE,
                    "num_ctx": 2048  # Smaller context for speed
                }
            },
            timeout=300  # 5 minute timeout
        )
        response.raise_for_status()
        
        return response.json()["message"]["content"]
    
    def generate_with_web_search(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text - Ollama doesn't have web search, falls back to regular generation."""
        return self.generate(prompt, system_prompt)


# =============================================================================
# WEB SEARCH INTEGRATION (Optional)
# =============================================================================

class WebSearchClient:
    """Optional web search integration using SerpAPI."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.SERP_API_KEY
        
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Perform web search and return results."""
        if not self.api_key:
            return []
        
        try:
            from serpapi import GoogleSearch
            
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "link": r.get("link", "")
                }
                for r in organic_results[:num_results]
            ]
        except ImportError:
            print("Warning: serpapi not installed. Run: pip install google-search-results")
            return []
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    def get_context_from_search(self, query: str, num_results: int = 3) -> str:
        """Get search results formatted as context for LLM."""
        results = self.search(query, num_results)
        if not results:
            return ""
        
        context_parts = ["Relevant information from web search:"]
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n{i}. {result['title']}")
            context_parts.append(f"   {result['snippet']}")
        
        return "\n".join(context_parts)


# =============================================================================
# LLM FACTORY
# =============================================================================

def get_llm_client() -> LLMInterface:
    """Factory function to get the appropriate LLM client."""
    provider = config.LLM_PROVIDER.lower()
    
    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    elif provider == "gemini":
        return GeminiClient()
    elif provider == "ollama":
        return OllamaClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_web_search_client() -> Optional[WebSearchClient]:
    """Get web search client if enabled."""
    if config.WEB_SEARCH_ENABLED:
        return WebSearchClient()
    return None


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

class PromptTemplates:
    """Collection of prompt templates for book generation."""
    
    @staticmethod
    def outline_generation(title: str, notes: str = "") -> str:
        """Generate prompt for outline creation."""
        prompt = f"""Create a book outline for "{title}".

Provide:
1. Brief book overview (2-3 sentences)
2. 5-6 chapter titles with 2-3 bullet points each

Keep it concise."""
        
        if notes:
            prompt += f"\n\nNotes: {notes}"
        
        return prompt
    
    @staticmethod
    def outline_regeneration(title: str, current_outline: str, feedback_notes: str) -> str:
        """Generate prompt for outline regeneration based on feedback."""
        return f"""Revise the following book outline for "{title}" based on the editor's feedback.

Current Outline:
{current_outline}

Editor's Feedback and Requested Changes:
{feedback_notes}

Please create an improved outline that addresses all the feedback while maintaining a coherent structure.
Keep what works well from the original outline and modify/add/remove sections as needed based on the feedback."""
    
    @staticmethod
    def chapter_generation(
        title: str,
        chapter_number: int,
        chapter_title: str,
        chapter_outline: str,
        previous_summaries: str = "",
        chapter_notes: str = ""
    ) -> str:
        """Generate prompt for chapter content creation."""
        prompt = f"""Write Chapter {chapter_number} of the book "{title}".

Chapter Title: {chapter_title}

Chapter Outline/Topics to Cover:
{chapter_outline}"""
        
        if previous_summaries:
            prompt += f"""

Context from Previous Chapters:
{previous_summaries}

Ensure continuity with the previous chapters while avoiding repetition."""
        
        if chapter_notes:
            prompt += f"""

Editor's Notes for This Chapter:
{chapter_notes}

Please incorporate these notes into the chapter."""
        
        prompt += """

Write engaging, well-structured content with:
- Clear explanations and examples
- Smooth transitions between sections
- Appropriate depth for the target audience
- A brief introduction and conclusion for the chapter"""
        
        return prompt
    
    @staticmethod
    def chapter_regeneration(
        title: str,
        chapter_number: int,
        chapter_title: str,
        current_content: str,
        feedback_notes: str,
        previous_summaries: str = ""
    ) -> str:
        """Generate prompt for chapter regeneration based on feedback."""
        prompt = f"""Revise Chapter {chapter_number} ("{chapter_title}") of the book "{title}" based on the editor's feedback.

Current Chapter Content:
{current_content}

Editor's Feedback and Requested Changes:
{feedback_notes}"""
        
        if previous_summaries:
            prompt += f"""

Context from Previous Chapters (for continuity):
{previous_summaries}"""
        
        prompt += """

Please create an improved version of this chapter that:
1. Addresses all the feedback points
2. Maintains consistency with the book's overall flow
3. Keeps the content engaging and well-structured"""
        
        return prompt
    
    @staticmethod
    def chapter_summary(chapter_content: str, chapter_number: int, chapter_title: str) -> str:
        """Generate prompt for creating chapter summary."""
        return f"""Create a concise summary of Chapter {chapter_number} ("{chapter_title}") for use as context in generating subsequent chapters.

Chapter Content:
{chapter_content}

Provide a summary (200-300 words) that captures:
1. Main topics and key points covered
2. Important concepts, terms, or ideas introduced
3. Any significant conclusions or decisions made
4. Elements that might be referenced in later chapters

Focus on information that would be relevant for maintaining continuity in subsequent chapters."""
    
    @staticmethod
    def research_query(topic: str, book_title: str) -> str:
        """Generate prompt for research-backed content."""
        return f"""For the book "{book_title}", I need accurate, fact-based information about:

{topic}

Please provide:
1. Key facts and statistics (with context)
2. Current understanding or consensus in this area
3. Notable examples or case studies
4. Any important caveats or nuances

Focus on accuracy and cite general sources of information where applicable."""
