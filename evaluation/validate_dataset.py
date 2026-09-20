from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.dataset import load_instruction_dataset


def main() -> None:
    examples = load_instruction_dataset()

    if not examples:
        raise SystemExit("Dataset is empty.")

    for index, example in enumerate(examples, start=1):
        if not example["instruction"]:
            raise SystemExit(f"Example {index} has an empty instruction.")

        if not example["response"]:
            raise SystemExit(f"Example {index} has an empty response.")

    print("Klyor Brain dataset validation passed.")
    print(f"Examples: {len(examples)}")


if __name__ == "__main__":
    main()
