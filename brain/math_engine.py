from __future__ import annotations

import ast
import math
import operator
import re


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _format_number(value: int | float) -> str:
    if isinstance(value, float):
        if not math.isfinite(value):
            return "undefined"

        if value.is_integer():
            return str(int(value))

        return f"{value:.12g}"

    return str(value)


def calculate(expression: str) -> str | None:
    expression = expression.strip()

    if not expression:
        return None

    expression = (
        expression
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("^", "**")
    )

    if not re.fullmatch(r"[\d\s+\-*/%().]+", expression):
        return None

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
    except (
        SyntaxError,
        ValueError,
        TypeError,
        ZeroDivisionError,
        OverflowError,
    ):
        return None

    return _format_number(result)


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise ValueError("Boolean values are not allowed.")

        if isinstance(node.value, (int, float)):
            return node.value

        raise ValueError("Only numbers are allowed.")

    if isinstance(node, ast.BinOp):
        operation = OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Unsupported operation.")

        left = _evaluate(node.left)
        right = _evaluate(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large.")

        result = operation(left, right)

        if abs(result) > 10**100:
            raise ValueError("Result is too large.")

        return result

    if isinstance(node, ast.UnaryOp):
        operation = OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Unsupported operation.")

        return operation(_evaluate(node.operand))

    raise ValueError("Unsupported mathematical expression.")


def _solve_percent_of(text: str) -> str | None:
    cleaned = text.lower().replace(",", "")

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*of\s+(\d+(?:\.\d+)?)",
        cleaned,
    )

    if not match:
        match = re.search(
            r"(\d+(?:\.\d+)?)\s+percent(?:age)?\s+of\s+(\d+(?:\.\d+)?)",
            cleaned,
        )

    if not match:
        return None

    percentage = float(match.group(1))
    total = float(match.group(2))

    return _format_number(total * percentage / 100)


def _solve_fraction_of(text: str) -> str | None:
    cleaned = text.lower().replace(",", "")

    match = re.search(
        r"(\d+)\s*/\s*(\d+)\s+of\s+(\d+(?:\.\d+)?)",
        cleaned,
    )

    if not match:
        return None

    numerator = float(match.group(1))
    denominator = float(match.group(2))
    total = float(match.group(3))

    if denominator == 0:
        return None

    return _format_number(total * numerator / denominator)


def _solve_square_root(text: str) -> str | None:
    cleaned = text.lower().strip()

    match = re.search(
        r"(?:sqrt|square\s+root\s+of)\s+(\d+(?:\.\d+)?)",
        cleaned,
    )

    if not match:
        return None

    value = float(match.group(1))

    if value < 0:
        return None

    return _format_number(math.sqrt(value))


def _solve_power_phrase(text: str) -> str | None:
    cleaned = text.lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s+(?:to\s+the\s+power\s+of|raised\s+to)\s+(-?\d+(?:\.\d+)?)",
        cleaned,
    )

    if not match:
        return None

    base = float(match.group(1))
    exponent = float(match.group(2))

    if abs(exponent) > 100:
        return None

    try:
        return _format_number(base ** exponent)
    except (OverflowError, ZeroDivisionError):
        return None


def _solve_average(text: str) -> str | None:
    cleaned = text.lower()

    match = re.search(
        r"(?:average|mean)\s+of\s+((?:\d+(?:\.\d+)?\s*,?\s*)+)",
        cleaned,
    )

    if not match:
        return None

    values = [
        float(value)
        for value in re.findall(r"\d+(?:\.\d+)?", match.group(1))
    ]

    if not values:
        return None

    return _format_number(sum(values) / len(values))


def extract_expression(text: str) -> str | None:
    cleaned = text.lower().strip()

    number_words = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
        "twenty": "20",
        "hundred": "100",
    }

    for word, value in number_words.items():
        cleaned = re.sub(rf"\b{word}\b", value, cleaned)

    cleaned = re.sub(
        r"\bmultiplied\s+by\b|\btimes\b",
        "*",
        cleaned,
    )

    cleaned = re.sub(
        r"\bdivided\s+by\b",
        "/",
        cleaned,
    )

    cleaned = re.sub(r"\bplus\b", "+", cleaned)
    cleaned = re.sub(r"\bminus\b", "-", cleaned)

    cleaned = re.sub(
        r"\b(?:to the power of|power)\b",
        "^",
        cleaned,
    )

    cleaned = re.sub(
        r"(?<=\d)\s*x\s*(?=\d)",
        "*",
        cleaned,
    )

    cleaned = re.sub(
        r"\b(?:what is|what's|calculate|solve|work out|how much is)\b",
        "",
        cleaned,
    )

    cleaned = cleaned.replace("equals", "")
    cleaned = cleaned.replace("equal to", "")
    cleaned = cleaned.replace("please", "")
    cleaned = cleaned.replace("?", "")
    cleaned = cleaned.replace("=", "")

    cleaned = cleaned.strip()

    if re.fullmatch(
        r"[\d\s+\-*/%().×÷−^]+",
        cleaned,
    ):
        return cleaned

    return None


def solve(text: str) -> str | None:
    """
    Deterministic mathematical solver.

    Natural-language patterns are handled first, then safe
    arithmetic parsing is attempted.
    """

    for solver in (
        _solve_percent_of,
        _solve_fraction_of,
        _solve_square_root,
        _solve_power_phrase,
        _solve_average,
    ):
        result = solver(text)

        if result is not None:
            return result

    expression = extract_expression(text)

    if expression is None:
        return None

    return calculate(expression)
