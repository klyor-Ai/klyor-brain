from __future__ import annotations

import re

from brain.tools.search_engine import search_web


class WebCapability:
    SEARCH_TRIGGERS = (
        "search",
        "look up",
        "look it up",
        "find online",
        "find on the web",
        "latest",
        "today",
        "current",
        "recent",
        "news",
        "what happened",
        "who is",
        "when did",
    )

    @classmethod
    def should_search(cls, query: str) -> bool:
        lowered = query.lower().strip()

        return any(
            trigger in lowered
            for trigger in cls.SEARCH_TRIGGERS
        )

    def search(self, query: str) -> list[dict]:
        return search_web(query, max_results=5)

    @staticmethod
    def _clean_snippet(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()

        # Avoid accidentally returning raw result metadata as prose.
        text = text.replace("…", "...")

        return text

    @classmethod
    def summarise_results(
        cls,
        query: str,
        results: list[dict],
    ) -> str | None:
        """Turn search results into a concise deterministic answer."""
        useful: list[dict] = []

        for result in results:
            title = str(result.get("title") or "").strip()
            snippet = cls._clean_snippet(
                str(result.get("snippet") or "")
            )
            url = str(result.get("url") or "").strip()

            if not snippet:
                continue

            useful.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                }
            )

        if not useful:
            return None

        # For factual searches, prefer the strongest first snippet instead
        # of dumping five unrelated results into the chat.
        primary = useful[0]
        answer = primary["snippet"]

        if primary["title"]:
            answer = f"**{primary['title']}**\n\n{answer}"

        # Include a small source section so the answer remains traceable.
        source_lines = []

        for result in useful[:3]:
            if result["url"]:
                label = result["title"] or result["url"]
                source_lines.append(
                    f"- [{label}]({result['url']})"
                )

        if source_lines:
            answer += "\n\n**Sources**\n\n" + "\n".join(source_lines)

        return answer

    def answer(self, query: str) -> str | None:
        if not self.should_search(query):
            return None

        results = self.search(query)

        if not results:
            return (
                "I couldn't retrieve web results for that request."
            )

        return self.summarise_results(query, results)
