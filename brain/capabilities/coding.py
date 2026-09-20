from __future__ import annotations

import re

from training.knowledge import load_coding_knowledge


class CodingCapability:
    CODING_WORDS = {
        "code",
        "coding",
        "program",
        "programming",
        "python",
        "javascript",
        "typescript",
        "html",
        "css",
        "java",
        "rust",
        "golang",
        "go",
        "sql",
        "bash",
        "function",
        "class",
        "loop",
        "debug",
        "debugging",
        "error",
        "syntax",
        "api",
        "script",
        "website",
        "web",
    }

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.knowledge = load_coding_knowledge()

    @classmethod
    def is_coding_request(cls, text: str) -> bool:
        words = {
            word.lower()
            for word in re.findall(r"[a-zA-Z0-9]+", text)
        }

        return bool(words & cls.CODING_WORDS)

    def find_syntax(
        self,
        query: str,
        language: str | None = None,
    ) -> dict | None:
        self.reload()

        query_lower = query.lower()

        best = None
        best_score = 0

        for item in self.knowledge:
            if "language" not in item:
                continue

            if language and item["language"].lower() != language.lower():
                continue

            searchable = " ".join(
                [
                    str(item.get("language", "")),
                    str(item.get("concept", "")),
                    str(item.get("syntax", "")),
                    str(item.get("explanation", "")),
                ]
            ).lower()

            query_words = set(
                re.findall(r"[a-zA-Z0-9]+", query_lower)
            )
            item_words = set(
                re.findall(r"[a-zA-Z0-9]+", searchable)
            )

            score = len(query_words & item_words)

            if score > best_score:
                best_score = score
                best = item

        return best

    @staticmethod
    def extract_language(text: str) -> str | None:
        languages = {
            "python": "python",
            "javascript": "javascript",
            "js": "javascript",
            "typescript": "typescript",
            "ts": "typescript",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "bash": "bash",
            "shell": "bash",
            "java": "java",
            "rust": "rust",
            "go": "go",
            "golang": "go",
        }

        lowered = text.lower()

        for name, normalized in languages.items():
            if re.search(rf"\b{re.escape(name)}\b", lowered):
                return normalized

        return None

    def answer(self, query: str) -> str | None:
        if not self.is_coding_request(query):
            return None

        lowered = query.lower().strip()

        # --------------------------------------------------
        # Simple code generation
        # --------------------------------------------------
        # Keep deterministic generators here for common requests
        # while the larger generation backend is developed.
        if (
            "python" in lowered
            and "print" in lowered
            and (
                "hello" in lowered
                or "hello world" in lowered
            )
        ):
            return (
                "```python\n"
                "print(\"Hello, world!\")\n"
                "```"
            )

        language = self.extract_language(query)
        result = self.find_syntax(query, language)

        if not result:
            return None

        explanation = result.get("explanation", "")
        syntax = result.get("syntax", "")
        example = result.get("example", "")
        result_language = result.get("language", language or "text")

        response = ""

        if explanation:
            response += explanation

        if syntax:
            response += f"\n\n**Syntax**\n\n```{result_language}\n{syntax}\n```"

        if example:
            response += f"\n\n**Example**\n\n```{result_language}\n{example}\n```"

        return response.strip() or None
