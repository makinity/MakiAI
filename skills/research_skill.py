"""
MakiAI — Research Skill (research_skill.py)
Autonomous web search and web page reading skill using the BareResearch engine.

Supports:
  1. Live Web Search & Question Answering ("search for...", "who is...", "what is the latest...", "lookup...")
  2. Direct URL Reading & Summarization ("read this link...", "check https://...", "summarize this page...")
"""

import os
import re
import urllib.parse
import webbrowser
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

        # Detect if user requested to open in Chrome / browser
        open_in_browser = bool(re.search(r"\b(chrome|browser|google\s+tab|open\s+(?:a\s+)?tab)\b", cleaned, flags=re.IGNORECASE))

        # Otherwise, handle as web search
        query = self._extract_search_query(cleaned)
        
        if open_in_browser and query:
            try:
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open_new_tab(search_url)
                print(f"[ResearchSkill] Launched browser tab for: {search_url}")
            except Exception as e:
                print(f"[ResearchSkill] Browser launch error: {e}")

        return self._handle_search(query, opened_in_browser=open_in_browser)

    def _extract_search_query(self, text: str) -> str:
        """Clean command wrappers and distill natural speech into a core search query."""
        cleaned = text.strip()
        
        # Remove common spoken conversational preambles (English & Taglish)
        patterns = [
            r"^(?:please\s+)?(?:search(?:\s+the\s+web|\s+google|\s+online)?\s+(?:for|about)?|look\s+up|find\s+(?:information\s+about|out\s+about|out\s+if|out|me)|google|research)\s+",
            r"^(?:can\s+you\s+)?(?:help\s+me\s+)?(?:find\s+out\s+(?:if|about)?|search|find|lookup|research)\s+",
            r"^(?:what\s+is\s+the\s+latest\s+on|who\s+won\s+the|tell\s+me\s+about)\s+",
            r"^(?:paki\s+)?(?:mag\s*research(?:\s+ka)?(?:\s+nang)?|magsaliksik(?:\s+ka)?|hanapin\s+sa\s+internet\s+(?:ang)?)\s*(?:tungkol\s+sa\s+|para\s+sa\s+|ukol\s+sa\s+)?",
            r"^(?:tungkol\s+sa\s+|para\s+sa\s+|ukol\s+sa\s+)",
        ]

        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove trailing instructions like "you can do a deep research on my Chrome"
        cleaned = re.sub(r"[,.]?\s*(?:you\s+can\s+)?(?:do\s+a\s+)?(?:deep\s+)?(?:research|search)\s+(?:on|in)\s+(?:my\s+)?(?:chrome|browser).*$", "", cleaned, flags=re.IGNORECASE).strip()

        # Use quick AI query distillation for complex sentences
        if len(cleaned.split()) > 7 and self.gemini:
            try:
                prompt = f"""Extract the core search engine query keywords from this user request:
"{cleaned}"
Return ONLY the clean 2-6 word search query. No quotes, no explanations."""
                distilled = self.gemini.send(prompt, "").strip().strip('"').strip("'")
                if distilled and len(distilled) < 80:
                    return distilled
            except Exception:
                pass

        return cleaned if cleaned else text

    def _handle_search(self, query: str, opened_in_browser: bool = False) -> str:
        """Search the web and synthesize the answer with AI."""
        if not query:
            return "What would you like me to look up for you, sir?"

        search_data = self.researcher.search(query, max_results=5)
        provider = search_data.get("provider", "Web")
        direct_answer = search_data.get("answer")
        results = search_data.get("results", [])

        browser_note = " I've also opened the search results in Chrome for you." if opened_in_browser else ""

        if not results and not direct_answer:
            return f"I searched the web for {query}, but couldn't find any relevant results right now, sir.{browser_note}"

        # Build context for LLM
        formatted_results = []
        if direct_answer:
            formatted_results.append(f"Direct Summary Answer: {direct_answer}\n")

        for idx, r in enumerate(results, 1):
            formatted_results.append(f"[{idx}] {r.get('title')}\nURL: {r.get('url')}\nContent: {r.get('desc')}\n")

        context_str = "\n".join(formatted_results)

        app_name = os.getenv("APP_NAME", "MakiAI")
        user_name = os.getenv("USER_NAME", "User")
        prompt = f"""You are {app_name}, personal assistant to {user_name} (sir).
Here are the live search results from {provider} for the query: "{query}"

{context_str}

Instruction:
Answer sir's query accurately, concisely, and naturally based on these search results.
Speak directly to sir. Do not use asterisks, markdown, or bullet points — keep it spoken English.
If there are specific numbers, dates, or names, state them clearly."""

        response = self.gemini.send(prompt, "")
        if response and response.strip():
            return f"{response.strip()}{browser_note}"

        # Fallback to direct answer or top title if AI is unavailable
        if direct_answer:
            return f"According to online sources, {direct_answer}{browser_note}"
        elif results:
            top = results[0]
            return f"Here is what I found regarding {query}: {top.get('title')}. {top.get('desc')}{browser_note}"
        return f"I completed the search for {query}, sir.{browser_note}"

    def _handle_read_url(self, url: str, question: str) -> str:
        """Fetch URL content and answer user's question about it."""
        page_content = self.researcher.read_url(url)
        if not page_content or page_content.startswith("HTTP Error") or page_content.startswith("Invalid"):
            return f"I wasn't able to open that link, sir. {page_content}"

        instruction = question if question else "Summarize the key information from this page."
        app_name = os.getenv("APP_NAME", "MakiAI")
        user_name = os.getenv("USER_NAME", "User")

        prompt = f"""You are {app_name}, personal assistant to {user_name} (sir).
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
