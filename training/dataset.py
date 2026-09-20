import json
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets"


def load_jsonl(path: Path) -> Iterator[dict]:
    """Load valid JSON objects from a JSONL dataset."""
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc

            if not isinstance(item, dict):
                raise ValueError(
                    f"Line {line_number} of {path} must contain a JSON object."
                )

            yield item


def load_instruction_dataset() -> list[dict]:
    """Load all instruction examples."""
    examples = []

    for path in sorted((DATASETS_DIR / "instructions").glob("*.jsonl")):
        for item in load_jsonl(path):
            if "instruction" not in item or "response" not in item:
                raise ValueError(
                    f"{path} contains an example without "
                    "'instruction' or 'response'."
                )

            examples.append(
                {
                    "instruction": str(item["instruction"]).strip(),
                    "response": str(item["response"]).strip(),
                }
            )

    return examples


if __name__ == "__main__":
    dataset = load_instruction_dataset()

    print(f"Loaded {len(dataset)} training examples.")

    for index, example in enumerate(dataset, start=1):
        print(f"{index}. {example['instruction']}")
