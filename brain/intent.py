from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "training"
    / "english"
    / "intents.json"
)


@dataclass(frozen=True)
class IntentMatch:
    name: str
    confidence: float
    matched_pattern: str | None = None


def load_intents() -> dict[str, list[str]]:
    if not DATA_FILE.exists():
        return {}

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("English intent dataset must contain a JSON list.")

    result: dict[str, list[str]] = {}

    for item in data:
        if not isinstance(item, dict):
            continue

        name = item.get("intent")
        examples = item.get("examples")

        if not isinstance(name, str):
            continue

        if not isinstance(examples, list):
            continue

        result[name] = [
            example.strip()
            for example in examples
            if isinstance(example, str) and example.strip()
        ]

    return result


def _normalize_pattern(pattern: str) -> str:
    pattern = pattern.lower().strip()
    pattern = re.sub(r"[?.!,;:]+$", "", pattern)
    pattern = re.sub(r"\s+", " ", pattern)
    return pattern


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    normalized = _normalize_pattern(pattern)

    parts = normalized.split("{topic}")

    if len(parts) == 1:
        return re.compile(
            "^" + re.escape(normalized) + "$",
            re.IGNORECASE,
        )

    prefix = re.escape(parts[0].strip())
    suffix = re.escape(parts[1].strip())

    if prefix and suffix:
        expression = (
            rf"^{prefix}\s+.+?\s+{suffix}$"
        )
    elif prefix:
        expression = rf"^{prefix}\s+.+$"
    else:
        expression = rf"^.+\s+{suffix}$"

    return re.compile(expression, re.IGNORECASE)


def classify_intent(text: str) -> IntentMatch:
    normalized = _normalize_pattern(text)

    if not normalized:
        return IntentMatch(
            name="unknown",
            confidence=0.0,
        )

    intents = load_intents()

    best: IntentMatch | None = None

    for intent_name, patterns in intents.items():
        for pattern in patterns:
            regex = _pattern_to_regex(pattern)

            if regex.fullmatch(normalized):
                confidence = 0.96

                if "{topic}" not in pattern:
                    confidence = 0.99

                candidate = IntentMatch(
                    name=intent_name,
                    confidence=confidence,
                    matched_pattern=pattern,
                )

                if best is None or candidate.confidence > best.confidence:
                    best = candidate

    if best is not None:
        return best

    return IntentMatch(
        name="unknown",
        confidence=0.0,
    )
