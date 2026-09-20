from __future__ import annotations

from brain.engine import KlyorBrain
from personality.genome import Personality


BENCHMARKS = [
    {
        "input": "what is 1+1",
        "expected": "2",
        "capability": "mathematics",
    },
    {
        "input": "what is a variable",
        "expected": "variable",
        "capability": "knowledge",
    },
    {
        "input": "what is HTML",
        "expected": "HTML",
        "capability": "knowledge",
    },
    {
        "input": "what is a function",
        "expected": "function",
        "capability": "knowledge",
    },
    {
        "input": "what is debugging",
        "expected": "debug",
        "capability": "knowledge",
    },
]


class PersonalityEvaluator:
    def __init__(self, brain: KlyorBrain) -> None:
        self.brain = brain

    def evaluate(self, personality: Personality) -> Personality:
        points = 0.0
        previous = self.brain.personality
        self.brain.set_personality(personality)

        try:
            for benchmark in BENCHMARKS:
                result = self.brain.answer(benchmark["input"], personality=personality)

                response = result.response.lower()
                expected = benchmark["expected"].lower()

                if expected in response:
                    points += 1.0

                if result.matched:
                    points += 0.5

                if (
                    benchmark["capability"] == "mathematics"
                    and result.capability == "mathematics"
                ):
                    points += 0.5

                if result.capability == "unknown":
                    points -= 0.1

            base_score = points / (len(BENCHMARKS) * 2.0)

            traits = personality.traits
            balance = 1.0 - (
                abs(traits["conciseness"] - traits["technical_detail"]) * 0.15
            )
            curiosity_bonus = traits.get("curiosity", 0.5) * 0.05
            patience_bonus = traits.get("patience", 0.5) * 0.05
            confidence_bonus = 0.05 if traits.get("confidence", 0.5) > 0.7 else 0.0

            score = max(
                0.0,
                min(
                    1.0,
                    (base_score * 0.85)
                    + (balance * 0.1)
                    + curiosity_bonus
                    + patience_bonus
                    + confidence_bonus,
                ),
            )
        finally:
            self.brain.set_personality(previous)

        personality.score = round(score, 4)
        personality.evaluations += 1

        return personality
