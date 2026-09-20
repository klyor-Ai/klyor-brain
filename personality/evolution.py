from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from time import time

from brain.engine import KlyorBrain
from personality.evaluator import PersonalityEvaluator
from personality.genome import Personality
from personality.population import Population


ROOT = Path(__file__).resolve().parent.parent
ACTIVE_DIR = ROOT / "personality" / "active"
ARCHIVE_DIR = ROOT / "personality" / "archive"
STATE_DIR = ROOT / "personality" / "state"
STATE_PATH = STATE_DIR / "population.json"


class EvolutionManager:
    def __init__(self) -> None:
        self.lock = Lock()
        self.brain = KlyorBrain()
        self.evaluator = PersonalityEvaluator(self.brain)
        self.population = Population(size=8, state_path=STATE_PATH)
        self.history: list[dict] = []
        self.status = "ready"
        self.learning_state = "ready"

        ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        self._load_history()
        self._restore_population_state()
        self.evaluate_current()

    def _load_history(self) -> None:
        if not STATE_PATH.exists():
            return

        try:
            payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        history = payload.get("history", [])
        if isinstance(history, list):
            self.history = history

    def _restore_population_state(self) -> None:
        if not STATE_PATH.exists():
            return

        try:
            payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        if not isinstance(payload, dict):
            return

        self.population.generation = int(payload.get("generation", self.population.generation))
        self.population.size = int(payload.get("size", self.population.size))

        personalities = payload.get("personalities", [])
        if isinstance(personalities, list) and personalities:
            self.population.personalities = [
                Personality.from_dict(personality)
                for personality in personalities
            ]

        self.population.save()

    def best_personality(self):
        ranked = self.population.rank()
        return ranked[0] if ranked else None

    def record_success(self, instruction: str, response: str, personality_id: str | None = None) -> None:
        personality = None
        if personality_id:
            personality = next(
                (candidate for candidate in self.population.personalities if candidate.id == personality_id),
                None,
            )
        if personality is None:
            personality = self.best_personality()
        if personality is None:
            return

        personality.score = min(1.0, round(personality.score + 0.03, 4))
        personality.evaluations += 1
        personality.status = "active"

        if instruction and response:
            self.brain.teach(instruction, response)

        self.population.save()
        self._save_active()

    def set_status(self, status: str) -> None:
        self.status = status
        self.learning_state = status

    def evaluate_current(self) -> None:
        for personality in self.population.personalities:
            self.evaluator.evaluate(personality)

        self._save_active()
        self.population.save()

    def evolve(self) -> dict:
        with self.lock:
            self.set_status("evolving")
            ranked = self.population.rank()
            survivors = self.population.survivors(3)

            survivor_ids = {
                personality.id
                for personality in survivors
            }

            for personality in ranked:
                if personality.id not in survivor_ids:
                    personality.status = "archived"
                    self._archive(personality)

            self.population.evolve()
            self.evaluate_current()

            best = self.population.rank()[0]
            result = {
                "generation": self.population.generation,
                "population": len(self.population.personalities),
                "best_score": best.score,
                "best_personality": best.to_dict(),
                "best_personality_id": best.id,
                "timestamp": int(time()),
            }

            history_entry = {
                "generation": self.population.generation,
                "best_score": best.score,
                "population": len(self.population.personalities),
                "best_personality_id": best.id,
                "timestamp": int(time()),
            }
            self.history.append(history_entry)
            if len(self.history) > 25:
                self.history = self.history[-25:]

            self.population.state_path.write_text(
                json.dumps(
                    {
                        "generation": self.population.generation,
                        "size": self.population.size,
                        "personalities": [
                            personality.to_dict()
                            for personality in self.population.personalities
                        ],
                        "history": self.history,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.set_status("ready")
            return result

    def _save_active(self) -> None:
        for personality in self.population.personalities:
            path = ACTIVE_DIR / f"{personality.id}.json"
            path.write_text(
                json.dumps(
                    personality.to_dict(),
                    indent=2,
                ),
                encoding="utf-8",
            )

        for active_file in ACTIVE_DIR.glob("*.json"):
            if active_file.stem not in {personality.id for personality in self.population.personalities}:
                archived = ARCHIVE_DIR / active_file.name
                if not archived.exists():
                    archived.write_text(active_file.read_text(encoding="utf-8"), encoding="utf-8")
                active_file.unlink()

    def _archive(self, personality) -> None:
        path = ARCHIVE_DIR / f"{personality.id}.json"
        path.write_text(
            json.dumps(
                personality.to_dict(),
                indent=2,
            ),
            encoding="utf-8",
        )

        active_path = ACTIVE_DIR / f"{personality.id}.json"
        if active_path.exists():
            active_path.unlink()

    def status_summary(self) -> dict:
        ranked = self.population.rank()
        best = ranked[0] if ranked else None
        survivors = self.population.survivors(3)
        return {
            "status": self.status,
            "learning_state": self.learning_state,
            "generation": self.population.generation,
            "population": len(self.population.personalities),
            "survivors": len(survivors),
            "training_examples": len(self.brain.examples),
            "best_score": best.score if best else 0,
            "best_personality_id": best.id if best else None,
            "personalities": [
                personality.to_dict()
                for personality in ranked
            ],
        }

    def stats(self) -> dict:
        ranked = self.population.rank()
        best = ranked[0] if ranked else None
        survivors = self.population.survivors(3)
        return {
            "generation": self.population.generation,
            "population": len(self.population.personalities),
            "survivors": len(survivors),
            "best_score": best.score if best else 0,
            "best_personality": best.to_dict() if best else None,
            "personalities": [
                personality.to_dict()
                for personality in ranked
            ],
            "history": self.history,
        }


evolution = EvolutionManager()
