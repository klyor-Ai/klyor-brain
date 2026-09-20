from __future__ import annotations

from ddgs import DDGS


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Perform a free DuckDuckGo search and return normalized results."""
    query = query.strip()

    if not query:
        return []

    try:
        raw_results = DDGS().text(
            query,
            max_results=max_results,
        )
    except Exception:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for result in raw_results or []:
        if not isinstance(result, dict):
            continue

        title = str(result.get("title") or "").strip()
        url = str(
            result.get("href")
            or result.get("url")
            or ""
        ).strip()
        snippet = str(
            result.get("body")
            or result.get("snippet")
            or ""
        ).strip()

        if not title and not snippet:
            continue

        identity = url or f"{title}|{snippet}"

        if identity in seen:
            continue

        seen.add(identity)

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
        )

        if len(results) >= max_results:
            break

    return results
