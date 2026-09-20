from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "examples.json"


def load_examples() -> list[dict]:
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("English dataset must contain a JSON list.")

    return data


def save_examples(examples: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(examples, file, indent=2, ensure_ascii=False)


def add_example(
    category: str,
    topic: str,
    instruction: str,
    response: str,
    difficulty: str = "basic",
    metadata: dict | None = None,
) -> dict:
    examples = load_examples()

    example = {
        "category": category,
        "topic": topic,
        "instruction": instruction,
        "response": response,
        "difficulty": difficulty,
    }

    if metadata:
        example["metadata"] = metadata

    examples.append(example)
    save_examples(examples)

    return example


def count_examples() -> int:
    return len(load_examples())
