from __future__ import annotations

import re

import sympy as sp


class SymbolicMathCapability:
    """
    Symbolic mathematics using SymPy.

    Handles equations, derivatives, integrals, factorisation,
    simplification and symbolic expressions.
    """

    def answer(self, text: str) -> str | None:
        lowered = text.lower().strip()

        # Do not steal plain arithmetic from math_engine.
        if self._looks_like_plain_arithmetic(lowered):
            return None

        # --------------------------------------------------
        # Derivatives
        # --------------------------------------------------

        if (
            "derivative" in lowered
            or "differentiate" in lowered
            or "differentiate" in lowered
        ):
            expression = self._extract_after_keywords(
                text,
                [
                    "derivative of",
                    "differentiate",
                ],
            )

            if expression:
                try:
                    x = sp.symbols("x")
                    parsed = sp.sympify(expression)
                    result = sp.diff(parsed, x)

                    return (
                        "**Derivative**\n\n"
                        f"```text\n"
                        f"d/dx ({sp.sstr(parsed)}) = "
                        f"{sp.sstr(result)}\n"
                        f"```"
                    )
                except Exception:
                    return None

        # --------------------------------------------------
        # Integrals
        # --------------------------------------------------

        if "integral" in lowered or "integrate" in lowered:
            expression = self._extract_after_keywords(
                text,
                [
                    "integral of",
                    "integrate",
                ],
            )

            if expression:
                try:
                    x = sp.symbols("x")
                    parsed = sp.sympify(expression)
                    result = sp.integrate(parsed, x)

                    return (
                        "**Integral**\n\n"
                        f"```text\n"
                        f"∫ ({sp.sstr(parsed)}) dx = "
                        f"{sp.sstr(result)} + C\n"
                        f"```"
                    )
                except Exception:
                    return None

        # --------------------------------------------------
        # Factor
        # --------------------------------------------------

        if "factor" in lowered:
            expression = self._extract_after_keywords(
                text,
                ["factor"],
            )

            if expression:
                try:
                    parsed = sp.sympify(expression)
                    result = sp.factor(parsed)

                    return (
                        "**Factorisation**\n\n"
                        f"```text\n"
                        f"{sp.sstr(parsed)} = "
                        f"{sp.sstr(result)}\n"
                        f"```"
                    )
                except Exception:
                    return None

        # --------------------------------------------------
        # Simplify
        # --------------------------------------------------

        if "simplify" in lowered:
            expression = self._extract_after_keywords(
                text,
                ["simplify"],
            )

            if expression:
                try:
                    parsed = sp.sympify(expression)
                    result = sp.simplify(parsed)

                    return (
                        "**Simplification**\n\n"
                        f"```text\n"
                        f"{sp.sstr(parsed)} → "
                        f"{sp.sstr(result)}\n"
                        f"```"
                    )
                except Exception:
                    return None

        # --------------------------------------------------
        # Solve equation
        # --------------------------------------------------

        if "solve" in lowered and "=" in text:
            expression = text.lower()

            expression = re.sub(
                r"^(please\s+)?solve\s+",
                "",
                expression,
            )

            try:
                left, right = expression.split("=", 1)

                x = sp.symbols("x")

                left = re.sub(r"(?<=\d)x\b", "*x", left)
                right = re.sub(r"(?<=\d)x\b", "*x", right)

                equation = sp.Eq(
                    sp.sympify(left.strip()),
                    sp.sympify(right.strip()),
                )

                result = sp.solve(equation, x)

                return (
                    "**Equation solution**\n\n"
                    f"```text\n"
                    f"{sp.sstr(equation)}\n"
                    f"x = {sp.sstr(result)}\n"
                    f"```"
                )
            except Exception:
                return None

        return None

    @staticmethod
    def _extract_after_keywords(
        text: str,
        keywords: list[str],
    ) -> str | None:
        lowered = text.lower()

        for keyword in keywords:
            index = lowered.find(keyword)

            if index >= 0:
                expression = text[
                    index + len(keyword):
                ].strip()

                expression = expression.rstrip("?.")

                if expression:
                    return expression

        return None

    @staticmethod
    def _looks_like_plain_arithmetic(text: str) -> bool:
        cleaned = re.sub(
            r"\b(what is|calculate|what's)\b",
            "",
            text,
        )

        return bool(
            re.fullmatch(
                r"[\d\s+\-*/%().×÷−^=]+",
                cleaned.strip(),
            )
        )
