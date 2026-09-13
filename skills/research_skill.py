"""
MakiAI — Research Skill (research_skill.py)
Autonomous web search and web page reading skill using the BareResearch engine.

Supports:
  1. Live Web Search & Question Answering ("search for...", "who is...", "what is the latest...", "lookup...")
  2. Direct URL Reading & Summarization ("read this link...", "check https://...", "summarize this page...")
"""

import re
from typing import Optional
from skills.base_skill import BaseSkill
from services.research.bare_research import BareResearch


class ResearchSkill(BaseSkill):
    """
    Skill for answering questions using real-time web search and reading web pages.
    """

    SKILL_ID = "research"
    REQUIRED_FILES = []

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.researcher = BareResearch()

    def execute(self, text: str) -> str:
        """
        Detect whether user is querying a URL or asking a search question.
        """
        cleaned = text.strip()

        # Check for URL in the text
        url_match = re.search(r"https?://[^\s,;]+", cleaned)
        if url_match:
            url = url_match.group(0).rstrip(".,;)")
            # Extract any specific question the user asked about the URL
            user_question = re.sub(r"https?://[^\s,;]+", "", cleaned).strip()
            return self._handle_read_url(url, user_question)

        # Otherwise, handle as web search
        query = self._extract_search_query(cleaned)
        return self._handle_search(query)

    def _extract_search_query(self, text: str) -> str:
        """Clean command wrappers to get the core search query."""
        cleaned = text.strip()
        # Remove common prefixes
        patterns = [
            r"^(?:please\s+)?(?:search(?:\s+the\s+web|\s+google|\s+online)?\s+(?:for|about)?|look\s+up|find\s+(?:information\s+about|out\s+about|me)|google|research)\s+",
            r"^(?:can\s+you\s+)?(?:search|find|lookup|research)\s+",
            r"^(?:what\s+is\s+the\s+latest\s+on|who\s+won\s+the|tell\s+me\s+about)\s+",
        ]
        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        return cleaned if cleaned else text

    def _handle_search(self, query: str) -> str:
        """Search the web and synthesize the answer with AI."""
        if not query:
            return "What would you like me to look up for you, sir?"

        search_data = self.researcher.search(query, max_results=5)
        provider = search_data.get("provider", "Web")
        direct_answer = search_data.get("answer")
        results = search_data.get("results", [])

        if not results and not direct_answer:
            return f"I searched the web for {query}, but couldn't find any relevant results right now, sir."

        # Build context for LLM
        formatted_results = []
        if direct_answer:
            formatted_results.append(f"Direct Summary Answer: {direct_answer}\n")

        for idx, r in enumerate(results, 1):
            formatted_results.append(f"[{idx}] {r.get('title')}\nURL: {r.get('url')}\nContent: {r.get('desc')}\n")

        context_str = "\n".join(formatted_results)

        prompt = f"""You are MakiAI, personal assistant to Mark (sir).
Here are the live search results from {provider} for the query: "{query}"

{context_str}

Instruction:
Answer sir's query accurately, concisely, and naturally based on these search results.
Speak directly to sir. Do not use asterisks, markdown, or bullet points — keep it spoken English.
If there are specific numbers, dates, or names, state them clearly."""

        response = self.gemini.send(prompt, "")
        if response and response.strip():
            return response.strip()

        # Fallback to direct answer or top title if AI is unavailable
        if direct_answer:
            return f"According to online sources, {direct_answer}"
        elif results:
            top = results[0]
            return f"Here is what I found regarding {query}: {top.get('title')}. {top.get('desc')}"
        return f"I completed the search for {query}, sir."

    def _handle_read_url(self, url: str, question: str) -> str:
        """Fetch URL content and answer user's question about it."""
        page_content = self.researcher.read_url(url)
        if not page_content or page_content.startswith("HTTP Error") or page_content.startswith("Invalid"):
            return f"I wasn't able to open that link, sir. {page_content}"

        instruction = question if question else "Summarize the key information from this page."

        prompt = f"""You are MakiAI, personal assistant to Mark (sir).
Sir asked you to inspect the web page at: {url}
Sir's question / instruction: "{instruction}"

Page Content:
{page_content}

Instruction:
Provide a clear, conversational, and direct response answering sir's request.
Speak naturally without bullet points, asterisks, or markdown formatting."""

        response = self.gemini.send(prompt, "")
        if response and response.strip():
            return response.strip()

        return f"I read the page at {url}, sir. It contains approximately {len(page_content)} characters of text."
