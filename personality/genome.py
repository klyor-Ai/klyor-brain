from __future__ import annotations

from dataclasses import asdict, dataclass
import random
import uuid


TRAITS = (
    "conciseness",
    "curiosity",
    "patience",
    "confidence",
    "technical_detail",
    "creativity",
)


@dataclass
class Personality:
    id: str
    generation: int
    traits: dict[str, float]
    score: float = 0.0
    evaluations: int = 0
    status: str = "active"

    @classmethod
    def random(cls, generation: int = 0) -> "Personality":
        return cls(
            id=f"personality_{uuid.uuid4().hex[:8]}",
            generation=generation,
            traits={
                trait: round(random.uniform(0.25, 0.85), 3)
                for trait in TRAITS
            },
        )

    @classmethod
    def from_dict(cls, payload: dict) -> "Personality":
        traits = payload.get("traits", {})
        if not isinstance(traits, dict):
            traits = {trait: 0.5 for trait in TRAITS}

        return cls(
            id=str(payload.get("id") or f"personality_{uuid.uuid4().hex[:8]}"),
            generation=int(payload.get("generation", 0)),
            traits={
                trait: float(traits.get(trait, 0.5))
                for trait in TRAITS
            },
            score=float(payload.get("score", 0.0)),
            evaluations=int(payload.get("evaluations", 0)),
            status=str(payload.get("status", "active")),
        )

    def mutate(
        self,
        generation: int,
        mutation_strength: float = 0.15,
    ) -> "Personality":
        traits = dict(self.traits)

        trait = random.choice(TRAITS)
        change = random.uniform(
            -mutation_strength,
            mutation_strength,
        )

        traits[trait] = round(
            max(0.0, min(1.0, traits[trait] + change)),
            3,
        )

        return Personality(
            id=f"personality_{uuid.uuid4().hex[:8]}",
            generation=generation,
            traits=traits,
        )

    def to_dict(self) -> dict:
        return asdict(self)
