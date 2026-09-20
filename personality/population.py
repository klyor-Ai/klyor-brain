from __future__ import annotations

import json
from pathlib import Path

from personality.genome import Personality


class Population:
    def __init__(self, size: int = 8, state_path: str | Path | None = None) -> None:
        self.size = size
        self.generation = 0
        self.personalities: list[Personality] = []
        self.state_path = Path(state_path) if state_path else Path("personality/state/population.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        saved = self._load_state()
        if saved is not None:
            self.generation = int(saved.get("generation", 0))
            self.size = int(saved.get("size", size))
            self.personalities = [
                Personality.from_dict(personality)
                for personality in saved.get("personalities", [])
            ]
            if not self.personalities:
                self._create_initial_population()
        else:
            self._create_initial_population()

    def _load_state(self) -> dict | None:
        if not self.state_path.exists():
            return None

        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def _create_initial_population(self) -> None:
        self.personalities = [
            Personality.random(generation=self.generation)
            for _ in range(self.size)
        ]
        self.save()

    def save(self) -> None:
        payload = {
            "generation": self.generation,
            "size": self.size,
            "personalities": [
                personality.to_dict()
                for personality in self.personalities
            ],
        }
        self.state_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def rank(self) -> list[Personality]:
        return sorted(
            self.personalities,
            key=lambda personality: personality.score,
            reverse=True,
        )

    def survivors(self, count: int = 3) -> list[Personality]:
        return self.rank()[:count]

    def evolve(self) -> list[Personality]:
        survivors = self.survivors()

        self.generation += 1

        next_generation = list(survivors)

        while len(next_generation) < self.size:
            parent = survivors[
                len(next_generation) % len(survivors)
            ]

            next_generation.append(
                parent.mutate(
                    generation=self.generation,
                )
            )

        for personality in next_generation:
            personality.generation = self.generation
            personality.status = "active"

        self.personalities = next_generation
        self.save()

        return self.personalities
