import json
import logging

import requests
from tavily import TavilyClient

from apps.rag.search.main import SearchResult
from config import SRC_LOG_LEVELS, RAG_WEB_SEARCH_RESULT_COUNT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])




def search_tavily(api_key: str, query: str) -> list[SearchResult]:
    """Search using serper.dev's API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A serper.dev API key
        query (str): The query to search for
    """
    tavily = TavilyClient(api_key=api_key)
    # For basic search:
    # response = tavily.search(query=query)
    # For advanced search:
    response = tavily.search(query=query, search_depth="advanced")
    # Get the search results as context to pass an LLM:
    context = [{"url": obj["url"], "content": obj["content"]} for obj in response.results]

    json_response = response.json()
    results = sorted(
        json_response.get("organic", []), key=lambda x: x.get("position", 0)
    )
    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("description"),
        )
        for result in results[:RAG_WEB_SEARCH_RESULT_COUNT]
    ]
