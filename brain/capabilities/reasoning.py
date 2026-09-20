from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ReasoningResult:
    response: str
    confidence: float
    steps: list[str]


class ReasoningCapability:
    """
    Lightweight symbolic reasoning layer.

    This is deliberately deterministic. It does not pretend to be
    a large language model. It combines known facts and calculations
    into transparent reasoning steps.
    """

    COMPARISON_WORDS = {
        "compare",
        "difference",
        "different",
        "similar",
        "versus",
        "vs",
    }

    EXPLANATION_WORDS = {
        "why",
        "how",
        "explain",
        "explanation",
        "because",
    }

    def can_reason(self, text: str) -> bool:
        words = set(
            re.findall(r"[a-zA-Z]+", text.lower())
        )

        return bool(
            words
            & (
                self.COMPARISON_WORDS
                | self.EXPLANATION_WORDS
            )
        )

    def answer(
        self,
        text: str,
        knowledge: list[dict],
    ) -> ReasoningResult | None:
        if not self.can_reason(text):
            return None

        lowered = text.lower()

        # Find concepts mentioned by the user.
        matches = []

        for item in knowledge:
            concept = str(item.get("concept", "")).lower()

            if not concept:
                continue

            if concept in lowered:
                matches.append(item)

        if len(matches) < 2:
            return None

        if any(
            word in lowered
            for word in self.COMPARISON_WORDS
        ):
            first = matches[0]
            second = matches[1]

            first_name = first.get("concept", "First concept")
            second_name = second.get("concept", "Second concept")

            first_definition = (
                first.get("definition")
                or first.get("explanation")
                or "No definition available."
            )

            second_definition = (
                second.get("definition")
                or second.get("explanation")
                or "No definition available."
            )

            response = (
                f"**{first_name}**\n\n"
                f"{first_definition}\n\n"
                f"**{second_name}**\n\n"
                f"{second_definition}\n\n"
                f"**Relationship**\n\n"
                f"Both are related concepts, but they describe "
                f"different parts of the subject."
            )

            return ReasoningResult(
                response=response,
                confidence=0.72,
                steps=[
                    f"Identified {first_name}.",
                    f"Identified {second_name}.",
                    "Compared their definitions.",
                ],
            )

        # Explanation requests can be answered from a known concept.
        best = matches[0]

        definition = (
            best.get("definition")
            or best.get("explanation")
        )

        if definition:
            concept = best.get("concept", "This concept")

            response = (
                f"**{concept}**\n\n"
                f"{definition}\n\n"
                f"The key idea is that this concept can be "
                f"understood from its definition and its "
                f"relationship to related concepts."
            )

            return ReasoningResult(
                response=response,
                confidence=0.65,
                steps=[
                    f"Identified {concept}.",
                    "Retrieved its known definition.",
                    "Constructed an explanation.",
                ],
            )

        return None
