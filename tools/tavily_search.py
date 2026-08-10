import os
import logging

logger = logging.getLogger(__name__)

# Toggle to enable/disable web search entirely
USE_WEB_SEARCH = os.getenv("USE_WEB_SEARCH", "true").lower() != "false"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def _search_duckduckgo(query, max_results=1):
    from ddgs import DDGS

    cleaned = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            cleaned.append({
                "title": r.get("title", "Untitled"),
                "url": r.get("href", ""),
                "content": (r.get("body") or "").strip(),
            })
    return cleaned


def _search_tavily(query, max_results=1):
    import requests

    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()

    cleaned = []
    for r in data.get("results", [])[:max_results]:
        cleaned.append({
            "title": r.get("title", "Untitled"),
            "url": r.get("url", ""),
            "content": (r.get("content") or "").strip(),
        })
    return cleaned


def search_tavily_snippets(query, max_results=1):
    """
    Fetch web context snippets for a query. Uses DuckDuckGo (free, no API key)
    by default, and falls back to Tavily only if TAVILY_API_KEY is set and
    DuckDuckGo fails or is unavailable.
    """
    if not USE_WEB_SEARCH:
        logger.info("[Search] Skipped (USE_WEB_SEARCH=false)")
        return []

    try:
        results = _search_duckduckgo(query, max_results)
        logger.info(f"[DuckDuckGo] Found {len(results)} result(s) for: {query[:50]}...")
        return results
    except Exception as e:
        logger.warning(f"[DuckDuckGo] search failed: {e}")

    if TAVILY_API_KEY:
        try:
            results = _search_tavily(query, max_results)
            logger.info(f"[Tavily] Found {len(results)} result(s) for: {query[:50]}...")
            return results
        except Exception as e:
            logger.warning(f"[Tavily] search failed: {e}")

    logger.warning(f"[Search] No results for: {query[:50]}... (all providers failed/unavailable)")
    return []
