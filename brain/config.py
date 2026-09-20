import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("KLYOR_BRAIN_HOST", "0.0.0.0")
    port: int = int(os.getenv("KLYOR_BRAIN_PORT", "8000"))


settings = Settings()
