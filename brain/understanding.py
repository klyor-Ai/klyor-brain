from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import get_close_matches
from brain.english import EnglishAnalysis, analyse


SLANG = {
    "lol": "laughing out loud",
    "lmao": "laughing my ass off",
    "rofl": "rolling on the floor laughing",
    "idk": "I don't know",
    "ikr": "I know right",
    "imo": "in my opinion",
    "imho": "in my humble opinion",
    "tbh": "to be honest",
    "ngl": "not gonna lie",
    "brb": "be right back",
    "btw": "by the way",
    "omg": "oh my god",
    "rn": "right now",
    "irl": "in real life",
    "afk": "away from keyboard",
    "fyi": "for your information",
    "asap": "as soon as possible",
    "fr": "for real",
    "wym": "what do you mean",
    "wdym": "what do you mean",
    "hbu": "how about you",
    "wyd": "what are you doing",
    "yw": "you're welcome",
    "np": "no problem",
    "ty": "thank you",
    "thx": "thanks",
    "pls": "please",
    "plz": "please",
    "abt": "about",
    "bc": "because",
    "bcs": "because",
    "cuz": "because",
    "cos": "because",
    "wbu": "what about you",
}


COMMON_CORRECTIONS = {
    "whats": "what is",
    "wats": "what is",
    "wht": "what",
    "wat": "what",
    "wut": "what",
    "whos": "who is",
    "hows": "how is",
    "wheres": "where is",
    "dont": "don't",
    "doesnt": "doesn't",
    "cant": "can't",
    "couldnt": "couldn't",
    "wouldnt": "wouldn't",
    "shouldnt": "shouldn't",
    "didnt": "didn't",
    "isnt": "isn't",
    "arent": "aren't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "im": "I'm",
    "ive": "I've",
    "ill": "I'll",
    "id": "I'd",
    "youre": "you're",
    "youve": "you've",
    "youll": "you'll",
    "theyre": "they're",
    "thats": "that's",
    "theres": "there's",
    "quantue": "quantum",
    "quantm": "quantum",
    "quantom": "quantum",
    "qantum": "quantum",
    "physcis": "physics",
    "phsyics": "physics",
    "phyiscs": "physics",
    "physic": "physics",
    "emphaty": "empathy",
    "emphathy": "empathy",
    "matths": "maths",
    "mathamatics": "mathematics",
    "mathematcs": "mathematics",
    "engish": "english",
    "langauge": "language",
    "abbrevation": "abbreviation",
    "abreviation": "abbreviation",
    "vocab": "vocabulary",
    "recieve": "receive",
    "beleive": "believe",
    "definately": "definitely",
    "seperate": "separate",
    "occured": "occurred",
    "becuase": "because",
    "becouse": "because",
    "probaly": "probably",
    "probally": "probably",
    "thier": "their",
    "teh": "the",
    "hte": "the",
    "alot": "a lot",
    "everythng": "everything",
    "somthing": "something",
    "abt": "about",
}


FUZZY_VOCABULARY = {
    "quantum",
    "physics",
    "mathematics",
    "mathematical",
    "science",
    "photosynthesis",
    "empathy",
    "abbreviation",
    "vocabulary",
    "language",
    "syntax",
    "grammar",
    "chemistry",
    "biology",
    "astronomy",
    "algorithm",
    "programming",
    "javascript",
    "python",
    "html",
    "css",
    "percentage",
    "fraction",
    "equation",
    "algebra",
    "geometry",
    "calculus",
    "statistics",
}


@dataclass(frozen=True)
class UnderstandingResult:
    original: str
    normalized: str
    corrected: str
    tokens: tuple[str, ...]
    corrections: tuple[str, ...]
    english: EnglishAnalysis
    topic: str = ""


def extract_topic(text: str) -> str:
    """Extract the likely subject from a natural-language request."""

    value = text.strip()

    if not value:
        return ""

    value = re.sub(r"[?!.]+$", "", value).strip()

    patterns = (
        # Contractions such as "what's quantum physics"
        r"^(?:what's|who's|how's|where's|when's|why's)\\s+(.+)$",

        # Normal question forms.
        r"^(?:what|who|when|where|why|how)\\s+"
        r"(?:is|are|was|were|does|do|did|can|could|would)\\s+"
        r"(.+)$",

        r"^(?:what|who|when|where|why|how)\\s+"
        r"(.+)$",

        # Requests such as "can you explain quantum physics".
        r"^(?:can|could|would)\\s+you\\s+"
        r"(?:explain|tell\\s+me\\s+about|describe)\\s+"
        r"(.+)$",

        # Requests such as "tell me about algorithms".
        r"^(?:tell\\s+me\\s+about|tell\\s+me\\s+what)\\s+"
        r"(.+)$",

        # Requests such as "explain quantum physics please".
        r"^(?:explain|describe)\\s+"
        r"(.+?)(?:\\s+please)?$",
    )

    for pattern in patterns:
        match = re.match(
            pattern,
            value,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        topic = match.group(1).strip()

        topic = re.sub(
            r"^(?:a|an|the)\\s+",
            "",
            topic,
            flags=re.IGNORECASE,
        )

        topic = re.sub(
            r"\\s+please$",
            "",
            topic,
            flags=re.IGNORECASE,
        )

        # Keep the extracted topic natural, but normalize
        # simple plural concepts to their singular form.
        words = topic.split()

        if words:
            last = words[-1].lower()

            if last.endswith("ies") and len(last) > 4:
                words[-1] = last[:-3] + "y"
            elif last.endswith("s") and not last.endswith("ss") and len(last) > 3:
                words[-1] = last[:-1]

        return " ".join(words).strip()

    return value

def _clean_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)

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

    return text


def _collapse_repeated_letters(word: str) -> str:
    if len(word) <= 3:
        return word

    return re.sub(r"(.)\1{2,}", r"\1", word)


def _fuzzy_correct_token(token: str) -> str:
    if len(token) < 4:
        return token

    if token in FUZZY_VOCABULARY:
        return token

    matches = get_close_matches(
        token,
        FUZZY_VOCABULARY,
        n=1,
        cutoff=0.84,
    )

    return matches[0] if matches else token



def _normalize_contextual_abbreviations(
    tokens: list[str],
) -> tuple[list[str], list[str]]:
    """
    Normalize common chat abbreviations only when they appear
    in natural-language contexts.

    Deliberately avoids global replacements because tokens such as
    'u', 'r', 'x', and 'y' can be valid programming or mathematical
    syntax.
    """
    lowered = [token.lower() for token in tokens]

    natural_language = any(
        token in {
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "can",
            "could",
            "would",
            "do",
            "does",
            "did",
            "are",
            "is",
            "please",
            "help",
            "explain",
            "tell",
            "you",
            "your",
            "me",
        }
        for token in lowered
    )

    if not natural_language:
        return tokens, []

    output: list[str] = []
    corrections: list[str] = []

    for index, token in enumerate(tokens):
        clean = token.lower().strip(".,!?;:")

        replacement: str | None = None

        if clean == "u":
            replacement = "you"

        elif clean == "r":
            replacement = "are"

        elif clean == "ur":
            next_token = (
                lowered[index + 1]
                if index + 1 < len(lowered)
                else ""
            )

            # "ur welcome" / "ur wrong" -> "you're ..."
            if next_token in {
                "welcome",
                "right",
                "wrong",
                "sure",
                "good",
                "late",
                "early",
                "crazy",
                "funny",
                "correct",
            }:
                replacement = "you're"
            else:
                replacement = "your"

        elif clean == "ya":
            replacement = "you"

        if replacement is not None:
            output.append(replacement)

            if clean != replacement:
                corrections.append(
                    f"{token} -> {replacement}"
                )
        else:
            output.append(token)

    return output, corrections


def _expand_slang(token: str) -> str | None:
    """
    Expand shorthand only when it is unambiguous.

    Single letters such as 'u' and 'r' are deliberately excluded
    because they can be legitimate mathematical/programming tokens.
    """
    clean = token.lower().strip(".,!?;:")

    return SLANG.get(clean)


def understand(text: str) -> UnderstandingResult:
    original = text

    text = _clean_unicode(text)
    text = re.sub(r"\s+", " ", text).strip()

    # Chat-style slash abbreviations.
    text = re.sub(r"\bw/o\b", "without", text, flags=re.IGNORECASE)
    text = re.sub(r"\bw/\b", "with", text, flags=re.IGNORECASE)

    raw_tokens = re.findall(
        r"[A-Za-z0-9']+|[^\w\s]",
        text,
    )

    normalized_tokens: list[str] = []
    corrections: list[str] = []

    for token in raw_tokens:
        if not re.fullmatch(r"[A-Za-z0-9']+", token):
            normalized_tokens.append(token)
            continue

        lowered = token.lower()
        collapsed = _collapse_repeated_letters(lowered)

        if collapsed != lowered:
            corrections.append(
                f"{token} -> {collapsed}"
            )

        replacement = COMMON_CORRECTIONS.get(collapsed)

        if replacement is None:
            replacement = _fuzzy_correct_token(collapsed)

        if replacement != collapsed:
            corrections.append(
                f"{token} -> {replacement}"
            )

        normalized_tokens.extend(
            replacement.split()
        )

    normalized_tokens, contextual_corrections = (
        _normalize_contextual_abbreviations(normalized_tokens)
    )

    corrections.extend(contextual_corrections)

    normalized = " ".join(normalized_tokens)

    normalized = re.sub(
        r"\s+([?.!,;:])",
        r"\1",
        normalized,
    )

    corrected_tokens: list[str] = []

    for token in normalized.split():
        expansion = _expand_slang(token)

        if expansion:
            corrected_tokens.extend(expansion.split())
            corrections.append(
                f"{token} -> {expansion}"
            )
        else:
            corrected_tokens.append(token)

    corrected = " ".join(corrected_tokens)

    tokens = tuple(
        word.lower()
        for word in re.findall(
            r"[a-zA-Z0-9']+",
            corrected,
        )
        if word
    )

    return UnderstandingResult(
        original=original,
        normalized=normalized,
        corrected=corrected,
        tokens=tokens,
        corrections=tuple(
            dict.fromkeys(corrections)
        ),
        english=analyse(corrected),
        topic=extract_topic(corrected),
    )


def likely_unknown_or_typo(
    result: UnderstandingResult,
) -> bool:
    return bool(result.corrections)


def search_query(
    result: UnderstandingResult,
) -> str:
    query = result.corrected.strip()

    query = re.sub(
        r"^(please\s+)?"
        r"(can you\s+)?"
        r"(could you\s+)?",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\b(tell me|explain|show me)\b",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+",
        " ",
        query,
    ).strip()

    return query
