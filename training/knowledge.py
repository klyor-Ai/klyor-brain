from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "datasets" / "knowledge"
CODING_DIR = ROOT / "datasets" / "coding"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    items = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            items.append(json.loads(line))

    return items


def load_knowledge() -> list[dict]:
    items = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.jsonl")):
        items.extend(load_jsonl(path))

    return items


def load_coding_knowledge() -> list[dict]:
    items = []

    for path in sorted(CODING_DIR.glob("*.jsonl")):
        items.extend(load_jsonl(path))

    return items
