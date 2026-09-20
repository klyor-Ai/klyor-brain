from __future__ import annotations

import re

from training.knowledge import load_knowledge, load_coding_knowledge


class KnowledgeCapability:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.general = load_knowledge()
        self.coding = load_coding_knowledge()

    @staticmethod
    def words(text: str) -> set[str]:
        return {
            word.lower()
            for word in re.findall(r"[a-zA-Z0-9]+", text)
            if len(word) > 1
        }

    @classmethod
    def similarity(cls, query: str, candidate: str) -> float:
        query_words = cls.words(query)
        candidate_words = cls.words(candidate)

        if not query_words or not candidate_words:
            return 0.0

        intersection = query_words & candidate_words
        union = query_words | candidate_words

        return len(intersection) / len(union)

    @staticmethod
    def singularize(word: str) -> str:
        word = word.lower().strip()

        if len(word) <= 3:
            return word

        irregular = {
            "people": "person",
            "children": "child",
            "men": "man",
            "women": "woman",
            "mice": "mouse",
            "teeth": "tooth",
            "feet": "foot",
            "computers": "computer",
            "qubits": "qubit",
        }

        if word in irregular:
            return irregular[word]

        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"

        if word.endswith(("ches", "shes")) and len(word) > 4:
            return word[:-2]

        if word.endswith(("xes", "zes")) and len(word) > 4:
            return word[:-2]

        if word.endswith("ses") and len(word) > 4:
            return word[:-2]

        if word.endswith("s") and not word.endswith("ss"):
            return word[:-1]

        return word

    @classmethod
    def normalize_concept_phrase(cls, text: str) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        return " ".join(
            cls.singularize(word)
            for word in words
        )

    @classmethod
    def concept_score(cls, query: str, concept: str) -> float:
        query_normalized = re.sub(
            r"\s+",
            " ",
            query.lower().strip(),
        )

        concept_normalized = re.sub(
            r"\s+",
            " ",
            concept.lower().strip(),
        )

        if not concept_normalized:
            return 0.0

        normalized_query = cls.normalize_concept_phrase(
            query_normalized
        )

        normalized_concept = cls.normalize_concept_phrase(
            concept_normalized
        )

        if normalized_query == normalized_concept:
            return 3.0

        if re.search(
            rf"(?<![a-z0-9])"
            rf"{re.escape(normalized_concept)}"
            rf"(?![a-z0-9])",
            normalized_query,
        ):
            return 2.5

        return 0.0

    @classmethod
    def rank_score(
        cls,
        query: str,
        item: dict,
    ) -> tuple[float, float, float]:
        concept = str(
            item.get("concept", "")
        ).strip()

        searchable = " ".join(
            str(item.get(key, ""))
            for key in (
                "concept",
                "definition",
                "language",
                "explanation",
                "syntax",
            )
        )

        concept_score = cls.concept_score(
            query,
            concept,
        )

        similarity_score = cls.similarity(
            query,
            searchable,
        )

        # Concept identity is the primary signal.
        #
        # A concept match should never lose just because another
        # definition happens to share more words with the question.
        total = (
            concept_score * 100
            + similarity_score
        )

        return (
            total,
            concept_score,
            similarity_score,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        self.reload()

        candidates = []

        for index, item in enumerate(
            self.general + self.coding
        ):
            total, concept_score, similarity_score = (
                self.rank_score(
                    query,
                    item,
                )
            )

            if total <= 0:
                continue

            candidates.append(
                (
                    total,
                    concept_score,
                    similarity_score,
                    index,
                    item,
                )
            )

        candidates.sort(
            key=lambda value: (
                -value[0],
                -value[1],
                -value[2],
                value[3],
            )
        )

        results = []

        for (
            total,
            concept_score,
            similarity_score,
            _index,
            item,
        ) in candidates[:limit]:
            results.append(
                {
                    **item,
                    "score": round(total, 4),
                    "concept_score": round(
                        concept_score,
                        4,
                    ),
                    "similarity_score": round(
                        similarity_score,
                        4,
                    ),
                }
            )

        return results

    def answer(self, query: str) -> str | None:
        results = self.search(
            query,
            limit=3,
        )

        if not results:
            return None

        best = results[0]

        definition = best.get("definition")

        if definition:
            return definition

        explanation = best.get("explanation")

        if explanation:
            return explanation

        return None
