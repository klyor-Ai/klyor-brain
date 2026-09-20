from __future__ import annotations

import re
import math
from dataclasses import dataclass


@dataclass
class ScienceResult:
    response: str
    confidence: float


class ScienceCapability:
    """
    Deterministic science calculator.

    Currently supports common physics and chemistry calculations.
    """

    def answer(self, text: str) -> ScienceResult | None:
        lowered = text.lower()

        if "newton" in lowered and "second law" in lowered:
            return ScienceResult(
                response=(
                    "Newton's second law states that the net force on an object "
                    "equals its mass multiplied by its acceleration.\n\n"
                    "```text\nF = m × a\n```"
                ),
                confidence=0.99,
            )

        # --------------------------------------------------
        # Physics: F = ma
        # --------------------------------------------------

        if (
            "force" in lowered
            and "mass" in lowered
            and "acceleration" in lowered
        ):
            numbers = self._numbers(text)

            if len(numbers) >= 2:
                mass, acceleration = numbers[:2]
                force = mass * acceleration

                return ScienceResult(
                    response=(
                        "**Force calculation**\n\n"
                        "Formula:\n\n"
                        "```text\n"
                        "F = m × a\n"
                        "```\n\n"
                        f"m = {mass}\n"
                        f"a = {acceleration}\n\n"
                        f"F = {force} N"
                    ),
                    confidence=0.95,
                )

        # --------------------------------------------------
        # Physics: density = mass / volume
        # --------------------------------------------------

        if (
            "density" in lowered
            and "mass" in lowered
            and "volume" in lowered
        ):
            numbers = self._numbers(text)

            if len(numbers) >= 2 and numbers[1] != 0:
                mass, volume = numbers[:2]
                density = mass / volume

                return ScienceResult(
                    response=(
                        "**Density calculation**\n\n"
                        "Formula:\n\n"
                        "```text\n"
                        "ρ = m / V\n"
                        "```\n\n"
                        f"m = {mass}\n"
                        f"V = {volume}\n\n"
                        f"ρ = {density:.6g}"
                    ),
                    confidence=0.95,
                )

        # --------------------------------------------------
        # Physics: speed = distance / time
        # --------------------------------------------------

        if (
            "speed" in lowered
            and "distance" in lowered
            and "time" in lowered
        ):
            numbers = self._numbers(text)

            if len(numbers) >= 2 and numbers[1] != 0:
                distance, time = numbers[:2]
                speed = distance / time

                return ScienceResult(
                    response=(
                        "**Speed calculation**\n\n"
                        "Formula:\n\n"
                        "```text\n"
                        "v = d / t\n"
                        "```\n\n"
                        f"d = {distance}\n"
                        f"t = {time}\n\n"
                        f"v = {speed:.6g}"
                    ),
                    confidence=0.95,
                )

        # --------------------------------------------------
        # Physics: kinetic energy
        # --------------------------------------------------

        if "kinetic energy" in lowered:
            numbers = self._numbers(text)

            if len(numbers) >= 2:
                mass, velocity = numbers[:2]
                energy = 0.5 * mass * velocity ** 2

                return ScienceResult(
                    response=(
                        "**Kinetic energy calculation**\n\n"
                        "Formula:\n\n"
                        "```text\n"
                        "E = ½mv²\n"
                        "```\n\n"
                        f"m = {mass}\n"
                        f"v = {velocity}\n\n"
                        f"E = {energy:.6g} J"
                    ),
                    confidence=0.95,
                )

        # --------------------------------------------------
        # Chemistry: concentration
        # --------------------------------------------------

        if (
            "concentration" in lowered
            and ("moles" in lowered or "mol" in lowered)
            and "volume" in lowered
        ):
            numbers = self._numbers(text)

            if len(numbers) >= 2 and numbers[1] != 0:
                moles, volume = numbers[:2]
                concentration = moles / volume

                return ScienceResult(
                    response=(
                        "**Concentration calculation**\n\n"
                        "Formula:\n\n"
                        "```text\n"
                        "c = n / V\n"
                        "```\n\n"
                        f"n = {moles}\n"
                        f"V = {volume}\n\n"
                        f"c = {concentration:.6g}"
                    ),
                    confidence=0.95,
                )

        return None

    @staticmethod
    def _numbers(text: str) -> list[float]:
        values = re.findall(
            r"(?<![A-Za-z])[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)",
            text,
        )

        return [float(value) for value in values]
