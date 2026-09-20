from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LEARNING_PATH = ROOT / "datasets" / "instructions" / "learned_examples.json"


@dataclass(frozen=True)
class LearningCandidate:
    instruction: str
    response: str
    source: str
    confidence: float


def _normalise(text: str) -> str:
    return " ".join(text.lower().strip().split())


def load() -> list[dict]:
    if not LEARNING_PATH.exists():
        return []

    try:
        payload = json.loads(
            LEARNING_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    return [
        item
        for item in payload
        if isinstance(item, dict)
        and item.get("instruction")
        and item.get("response")
    ]


def is_valid_candidate(candidate: LearningCandidate) -> bool:
    instruction = candidate.instruction.strip()
    response = candidate.response.strip()

    if not instruction or not response:
        return False

    if candidate.confidence < 0.85:
        return False

    if len(response) < 20:
        return False

    blocked = (
        "i couldn't retrieve web results",
        "i don't know that yet",
        "no results found",
        "something went wrong",
    )

    lowered = response.lower()

    if any(
        phrase in lowered
        for phrase in blocked
    ):
        return False

    return True


def save(candidate: LearningCandidate) -> bool:
    if not is_valid_candidate(candidate):
        return False

    learned = load()
    target = _normalise(candidate.instruction)

    learned = [
        item
        for item in learned
        if _normalise(
            str(item.get("instruction", ""))
        ) != target
    ]

    learned.append(
        {
            "instruction": candidate.instruction.strip(),
            "response": candidate.response.strip(),
            "source": candidate.source,
            "confidence": round(
                candidate.confidence,
                4,
            ),
        }
    )

    LEARNING_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LEARNING_PATH.write_text(
        json.dumps(
            learned,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return True
