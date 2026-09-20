from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EnglishAnalysis:
    original: str
    normalized: str
    question_type: str
    speech_act: str
    confidence: float
    has_question_mark: bool
    is_greeting: bool
    is_thanks: bool
    is_request: bool


QUESTION_PATTERNS = {
    "what": r"^(?:what|whats|what's)\b",
    "who": r"^(?:who|whos|who's)\b",
    "when": r"^when\b",
    "where": r"^where\b",
    "why": r"^why\b",
    "how": r"^how\b",
    "which": r"^which\b",
    "can": r"^(?:can|could|would)\b",
    "do": r"^(?:do|does|did)\b",
    "is": r"^(?:is|are|was|were)\b",
}


GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "sup",
    "welcome",
}


THANKS_WORDS = {
    "thanks",
    "thank",
    "thx",
    "ty",
    "cheers",
}


REQUEST_PREFIXES = (
    "please ",
    "can you ",
    "could you ",
    "would you ",
    "can u ",
    "could u ",
    "would u ",
    "pls ",
    "plz ",
)


def normalize(text: str) -> str:
    text = text.strip()

    # Normalize Unicode punctuation.
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    # Collapse excessive repeated punctuation.
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)

    # Collapse excessive whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _collapse_word(word: str) -> str:
    """
    Normalize expressive repetition.

    heyyyy -> hey
    helloooo -> hello

    Keep ordinary words untouched.
    """
    if len(word) <= 3:
        return word

    return re.sub(r"(.)\1{2,}", r"\1", word)


def normalize_repeated_letters(text: str) -> str:
    return re.sub(
        r"[A-Za-z]+",
        lambda match: _collapse_word(match.group(0)),
        text,
    )


def detect_question_type(text: str) -> tuple[str, float]:
    lowered = text.lower().strip()

    for question_type, pattern in QUESTION_PATTERNS.items():
        if re.search(pattern, lowered):
            return question_type, 0.95

    if "?" in text:
        return "unknown", 0.70

    return "none", 0.0


def detect_speech_act(text: str) -> tuple[str, float]:
    lowered = text.lower().strip()

    if any(
        lowered == word or lowered.startswith(word + " ")
        for word in GREETING_WORDS
    ):
        return "greeting", 0.98

    if any(
        lowered == word or lowered.startswith(word + " ")
        for word in THANKS_WORDS
    ):
        return "thanks", 0.98

    if any(lowered.startswith(prefix) for prefix in REQUEST_PREFIXES):
        return "request", 0.95

    if lowered.startswith(("tell me ", "explain ", "show me ")):
        return "request", 0.90

    question_type, question_confidence = detect_question_type(lowered)

    if question_type != "none":
        return "question", max(0.90, question_confidence)

    if lowered.endswith("?"):
        return "question", 0.90

    return "statement", 0.70

def analyse(text: str) -> EnglishAnalysis:
    original = text

    normalized = normalize(text)
    normalized = normalize_repeated_letters(normalized)

    question_type, question_confidence = detect_question_type(
        normalized
    )

    speech_act, speech_confidence = detect_speech_act(
        normalized
    )

    confidence = max(
        question_confidence,
        speech_confidence,
    )

    return EnglishAnalysis(
        original=original,
        normalized=normalized,
        question_type=question_type,
        speech_act=speech_act,
        confidence=confidence,
        has_question_mark="?" in normalized,
        is_greeting=speech_act == "greeting",
        is_thanks=speech_act == "thanks",
        is_request=speech_act == "request",
    )
