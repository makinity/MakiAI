"""
MakiAI — Bare Research Service (bare_research.py)
A zero-dependency, multi-tier web search and scraping engine inspired by paulablaza/bare-research.

Capabilities:
  1. Multi-Tier Search:
     Tavily (AI answer) -> Serper (Google API) -> Exa (Neural) -> DuckDuckGo (Free, 0-key fallback)
  2. Multi-Tier Scrape / Read URL:
     Firecrawl (Clean Markdown) -> Standard Library HTML Extractor -> Local Browser fallback
  3. Zero external package requirements (pure Python standard library).
"""

import os
import re
import json
import html
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any, List


def check_url(url: str) -> bool:
    """Validate URL format and prevent local network SSRF."""
    if not url.startswith(("http://", "https://")):
        return False
    try:
        host = urllib.parse.urlparse(url).hostname or ""
        if host.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        return True
    except Exception:
        return False


def request_json(url: str, headers: Optional[dict] = None, data: Any = None, method: Optional[str] = None, timeout: int = 12) -> Optional[dict]:
    """Execute HTTP request and return parsed JSON."""
    if not check_url(url):
        return None

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else str(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
        method = method or "POST"

    try:
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"[BareResearch] JSON request error to {url}: {e}")
        return None


class BareResearch:
    """
    Autonomous search and webpage reader with multi-tier provider fallbacks.
    """

    def __init__(self):
        pass

    # ─── Search Providers ─────────────────────────────────────────────────────

    def search_tavily(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            return None
        try:
            data = request_json(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {key}"},
                data={"query": query, "max_results": max_results, "include_answer": True},
            )
            if not data or "results" not in data:
                return None
            results = [
                {"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("content", "")}
                for r in data.get("results", [])
            ]
            return {"provider": "Tavily", "answer": data.get("answer"), "results": results}
        except Exception as e:
            print(f"[BareResearch] Tavily error: {e}")
            return None

    def search_serper(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        key = os.getenv("SERPER_API_KEY") or os.getenv("SEARCH_SERPER_API_KEY")
        if not key:
            return None
        try:
            data = request_json(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key},
                data={"q": query, "num": max_results},
            )
            if not data:
                return None
            results = [
                {"title": r.get("title", ""), "url": r.get("link", ""), "desc": r.get("snippet", "")}
                for r in data.get("organic", [])[:max_results]
            ]
            answer = None
            if "answerBox" in data:
                answer = data["answerBox"].get("snippet") or data["answerBox"].get("answer")
            elif "knowledgeGraph" in data:
                answer = data["knowledgeGraph"].get("description")
            return {"provider": "Google (Serper)", "answer": answer, "results": results}
        except Exception as e:
            print(f"[BareResearch] Serper error: {e}")
            return None

    def search_exa(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        key = os.getenv("EXA_API_KEY")
        if not key:
            return None
        try:
            data = request_json(
                "https://api.exa.ai/search",
                headers={"x-api-key": key},
                data={"query": query, "numResults": max_results, "useAutoprompt": True},
            )
            if not data or "results" not in data:
                return None
            results = [
                {"title": r.get("title", ""), "url": r.get("url", ""), "desc": r.get("text", "")}
                for r in data.get("results", [])[:max_results]
            ]
            return {"provider": "Exa", "answer": None, "results": results}
        except Exception as e:
            print(f"[BareResearch] Exa error: {e}")
            return None

    def search_duckduckgo(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Free, zero-key fallback using DuckDuckGo HTML search."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        results = []
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                html_doc = response.read().decode("utf-8", errors="replace")

            # Extract result blocks via regex
            snippets = re.findall(
                r'<a class="result__snippet[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                html_doc,
                re.DOTALL,
            )
            titles = re.findall(
                r'<a class="result__url[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                html_doc,
                re.DOTALL,
            )

            # Match links and titles
            links = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html_doc,
                re.DOTALL,
            )

            for link, raw_title in links[:max_results]:
                # Clean title
                clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                # Parse redirect url
                actual_url = link
                if "uddg=" in link:
                    m = re.search(r"uddg=([^&]+)", link)
                    if m:
                        actual_url = urllib.parse.unquote(m.group(1))

                results.append({
                    "title": clean_title,
                    "url": actual_url,
                    "desc": clean_title,
                })
        except Exception as e:
            print(f"[BareResearch] DuckDuckGo free search fallback error: {e}")

        return {"provider": "DuckDuckGo (Free)", "answer": None, "results": results}

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Execute search across available providers in order of quality & speed:
        Tavily -> Serper (Google) -> Exa -> DuckDuckGo
        """
        print(f"[BareResearch] Searching web for: '{query}'...")
        
        # 1. Tavily
        res = self.search_tavily(query, max_results)
        if res and res.get("results"):
            print(f"[BareResearch] Search fulfilled by Tavily AI.")
            return res

        # 2. Serper (Google)
        res = self.search_serper(query, max_results)
        if res and res.get("results"):
            print(f"[BareResearch] Search fulfilled by Google (Serper).")
            return res

        # 3. Exa
        res = self.search_exa(query, max_results)
        if res and res.get("results"):
            print(f"[BareResearch] Search fulfilled by Exa.")
            return res

        # 4. DuckDuckGo (Free fallback)
        res = self.search_duckduckgo(query, max_results)
        print(f"[BareResearch] Search fulfilled by DuckDuckGo fallback ({len(res.get('results', []))} results).")
        return res

    # ─── Scrape & Web Page Extraction ─────────────────────────────────────────

    def scrape_firecrawl(self, url: str) -> Optional[str]:
        """Scrape webpage to clean Markdown using Firecrawl API."""
        key = os.getenv("FIRECRAWL_API_KEY")
        if not key:
            return None
        try:
            data = request_json(
                "https://api.firecrawl.dev/v0/scrape",
                headers={"Authorization": f"Bearer {key}"},
                data={"url": url, "pageOptions": {"onlyMainContent": True}},
                timeout=18,
            )
            if data and data.get("success") and "data" in data:
                return data["data"].get("markdown") or data["data"].get("content")
        except Exception as e:
            print(f"[BareResearch] Firecrawl scrape error: {e}")
        return None

    def scrape_http(self, url: str, max_chars: int = 6000) -> str:
        """Zero-dependency HTML to readable text extractor."""
        if not check_url(url):
            return f"Invalid or disallowed URL: {url}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text" not in content_type and "html" not in content_type and "json" not in content_type:
                    return f"[Non-text content: {content_type}]"

                raw_html = response.read().decode("utf-8", errors="replace")

            # Clean HTML into readable markdown/text
            # Remove scripts, styles, svg, and noisy tags
            clean = re.sub(r"<(script|style|svg|noscript|header|footer|nav)[\s\S]*?</\1>", " ", raw_html, flags=re.IGNORECASE)
            # Replace paragraph / headings with newlines
            clean = re.sub(r"</?(h[1-6]|p|div|li|article|section)[^>]*>", "\n", clean, flags=re.IGNORECASE)
            # Remove all remaining tags
            clean = re.sub(r"<[^>]+>", " ", clean)
            # Unescape entities
            clean = html.unescape(clean)
            # Collapse whitespace
            clean = re.sub(r"\n\s*\n+", "\n\n", clean)
            clean = re.sub(r"[ \t]+", " ", clean).strip()

            if len(clean) > max_chars:
                clean = clean[:max_chars] + f"\n\n[... Truncated from {len(clean)} characters ...]"

            return clean if clean else "No readable text content found on page."

        except urllib.error.HTTPError as e:
            return f"HTTP Error {e.code}: {e.reason}"
        except Exception as e:
            return f"Error reading URL: {e}"

    def read_url(self, url: str) -> str:
        """Read web page using Firecrawl or standard HTTP fallback."""
        print(f"[BareResearch] Reading page content: {url}")
        
        # 1. Try Firecrawl (Clean Markdown)
        md = self.scrape_firecrawl(url)
        if md and len(md.strip()) > 50:
            print(f"[BareResearch] Page extracted via Firecrawl.")
            return md

        # 2. Free built-in HTTP extractor
        text = self.scrape_http(url)
        print(f"[BareResearch] Page extracted via built-in HTTP parser ({len(text)} chars).")
        return text
