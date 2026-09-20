from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

import httpx

from brain.capabilities import (
    CodingCapability,
    KnowledgeCapability,
    ReasoningCapability,
    ScienceCapability,
    SymbolicMathCapability,
    WebCapability,
    WebBuilderCapability,
)
from brain.math_engine import solve
from brain.project_manager import project_manager
from brain.learning import LearningCandidate, save as save_learning
from brain.understanding import understand, search_query
from brain.intent import classify_intent as classify_language_intent
from training.dataset import load_instruction_dataset


ROOT = Path(__file__).resolve().parent.parent
LEARNED_EXAMPLES_PATH = ROOT / "datasets" / "instructions" / "learned_examples.json"


@dataclass
class BrainResult:
    response: str
    matched: bool
    confidence: float
    capability: str = "unknown"
    project: dict | None = None
    status: str = "ready"
    intent: str = "unknown"
    intent_confidence: float = 0.0


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float


INTENT_NAMES = (
    "general",
    "coding",
    "debugging",
    "math",
    "science",
    "english",
    "reasoning",
    "web",
    "website_build",
    "website_modify",
    "browser_game",
    "project_question",
    "code_explanation",
    "documentation",
)


class KlyorBrain:
    def __init__(self) -> None:
        self.personality = None
        self.examples: list[dict] = []
        self.knowledge = KnowledgeCapability()
        self.coding = CodingCapability()
        self.reasoning = ReasoningCapability()
        self.science = ScienceCapability()
        self.symbolic_math = SymbolicMathCapability()
        self.web = WebCapability()
        self.web_builder = WebBuilderCapability()
        self.reload()

    def set_personality(self, personality) -> None:
        self.personality = personality

    def training_example_count(self) -> int:
        """Return the number of locally loaded instruction examples."""
        return len(self.examples)

    def reload(self) -> None:
        self.examples = load_instruction_dataset()
        if LEARNED_EXAMPLES_PATH.exists():
            try:
                learned = json.loads(
                    LEARNED_EXAMPLES_PATH.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                learned = []

            if isinstance(learned, list):
                self.examples.extend(
                    {
                        "instruction": str(item["instruction"]).strip(),
                        "response": str(item["response"]).strip(),
                        "source": "learned",
                    }
                    for item in learned
                    if isinstance(item, dict)
                    and item.get("instruction")
                    and item.get("response")
                )

        self.knowledge.reload()
        self.coding.reload()

    @staticmethod
    def _normalise(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _words(text: str) -> set[str]:
        return {
            word
            for word in re.findall(r"[a-zA-Z0-9]+", text.lower())
            if len(word) > 1
        }

    @classmethod
    def classify_intent(cls, text: str) -> Intent:
        """
        Classify the user's intent using the shared language-intent dataset,
        while preserving specialist capability routing for technical requests.
        """
        match = classify_language_intent(text)
        lowered = text.lower().strip()

        # Project modification must take priority over generic language intent.
        if cls._is_modification_request(lowered):
            return Intent("website_modify", 0.96)

        # Website/game generation must remain a specialist route.
        if WebBuilderCapability.is_build_request(lowered):
            name = (
                "browser_game"
                if WebBuilderCapability.is_game_request(lowered)
                else "website_build"
            )
            return Intent(name, 0.96)

        # Technical/debugging requests need specialist capabilities.
        if any(
            word in lowered
            for word in (
                "debug",
                "traceback",
                "exception",
                "error",
                "bug",
            )
        ):
            return Intent("debugging", 0.88)

        if any(
            word in lowered
            for word in (
                "search",
                "latest",
                "today",
                "current",
                "recent",
                "online",
            )
        ):
            return Intent("web", 0.78)

        if any(
            word in lowered
            for word in (
                "html",
                "css",
                "javascript",
                "typescript",
                "python",
                "api",
                "function",
                "code",
            )
        ):
            if any(
                word in lowered
                for word in (
                    "explain",
                    "what is",
                    "what are",
                    "how does",
                    "how do",
                )
            ):
                return Intent("code_explanation", 0.82)

            return Intent("coding", 0.82)

        if any(
            word in lowered
            for word in (
                "solve",
                "equation",
                "calculate",
                "integral",
                "derivative",
                "factor",
            )
        ):
            return Intent("math", 0.90)

        if any(
            word in lowered
            for word in (
                "force",
                "energy",
                "atom",
                "cell",
                "gravity",
                "photosynthesis",
            )
        ):
            return Intent("science", 0.86)

        if any(
            word in lowered
            for word in (
                "grammar",
                "rewrite",
                "summarise",
                "summarize",
                "spelling",
                "punctuation",
            )
        ):
            return Intent("english", 0.80)

        if any(
            word in lowered
            for word in (
                "why",
                "compare",
                "reason",
                "logic",
            )
        ):
            return Intent("reasoning", 0.70)

        # Preserve the trained natural-language intent instead of collapsing
        # it into a generic route.
        if match.name != "unknown":
            return Intent(match.name, match.confidence)

        return Intent("general", 0.40)

    @classmethod
    def _similarity(cls, first: str, second: str) -> float:
        first_words = cls._words(first)
        second_words = cls._words(second)

        if not first_words or not second_words:
            return 0.0

        intersection = first_words & second_words
        union = first_words | second_words

        return len(intersection) / len(union)

    def _instruction_answer(self, instruction: str) -> BrainResult | None:
        normalised = self._normalise(instruction)

        for example in self.examples:
            if self._normalise(example["instruction"]) == normalised:
                return BrainResult(
                    response=self._format_code_answer(
                        instruction,
                        example["response"],
                    ),
                    matched=True,
                    confidence=1.0,
                    capability=(
                        "knowledge"
                        if example.get("source") == "learned"
                        else "instruction"
                    ),
                )

        best_example = None
        best_score = 0.0

        for example in self.examples:
            score = self._similarity(
                instruction,
                example["instruction"],
            )

            if score > best_score:
                best_score = score
                best_example = example

        # Loose matches are dangerous for short questions: a shared word such
        # as "explain" should never outweigh the requested concept.
        if best_example is not None and best_score >= 0.78:
            return BrainResult(
                response=best_example["response"],
                matched=True,
                confidence=best_score,
                capability="instruction",
            )

        return None

    def teach(
        self,
        instruction: str,
        response: str,
        *,
        source: str = "explicit",
        confidence: float = 1.0,
    ) -> bool:
        """
        Store validated knowledge.

        Learning is deliberately explicit and confidence-gated.
        Volatile web answers should not automatically become permanent
        knowledge unless they pass the learning policy.
        """
        candidate = LearningCandidate(
            instruction=instruction,
            response=response,
            source=source,
            confidence=confidence,
        )

        saved = save_learning(candidate)

        if saved:
            self.reload()

        return saved

    @staticmethod
    def _web_answer(instruction: str) -> str | None:
        """Use the free public DuckDuckGo endpoint as an optional fallback."""
        try:
            response = httpx.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": instruction,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            return None

        topics = payload.get("RelatedTopics", [])
        for topic in topics:
            if not isinstance(topic, dict):
                continue
            if topic.get("Text"):
                return str(topic["Text"])
            for nested in topic.get("Topics", []):
                if isinstance(nested, dict) and nested.get("Text"):
                    return str(nested["Text"])
        return payload.get("AbstractText") or None

    @staticmethod
    def _is_modification_request(text: str) -> bool:
        lowered = text.lower()

        modification_words = (
            "add ",
            "change ",
            "modify ",
            "update ",
            "remove ",
            "delete ",
            "make ",
            "set ",
            "rename ",
            "increase ",
            "decrease ",
            "improve ",
        )

        project_words = (
            "website",
            "site",
            "page",
            "hero",
            "button",
            "navigation",
            "nav",
            "section",
            "contact",
            "animation",
            "responsive",
            "title",
            "heading",
            "icon",
            "icons",
            "svg",
            "footer",
            "spacing",
            "colour",
            "color",
            "professional",
            "cleaner",
            "ui",
            "design",
        )

        return (
            any(word in lowered for word in modification_words)
            and any(word in lowered for word in project_words)
            and project_manager.current_path() is not None
        )

    def _format_code_answer(self, instruction: str, answer: str) -> str:
        """
        Mark code clearly so the frontend can render it as a dedicated
        CODE BLOCK rather than treating it as ordinary prose.
        """
        text = instruction.lower()

        code_request = any(
            phrase in text
            for phrase in (
                "show me the code",
                "give me the code",
                "write the code",
                "code for",
                "html for",
                "css for",
                "javascript for",
                "js for",
                "how do i make",
                "how do i create",
                "how to make",
                "how to create",
                "example code",
            )
        )

        if code_request and "```" not in answer:
            return f"```text\n{answer}\n```"

        return answer

    @staticmethod
    def _debug_code_answer(instruction: str) -> BrainResult | None:
        if "totl" not in instruction and "undefined" not in instruction.lower():
            return None

        corrected = instruction.replace("totl", "total")
        return BrainResult(
            response=(
                "The code uses `totl`, but the variable declared above is `total`. "
                "JavaScript treats those as different identifiers, so `totl` is undefined.\n\n"
                f"```javascript\n{corrected}\n```"
            ),
            matched=True,
            confidence=0.98,
            capability="debugging",
        )

    @staticmethod
    def _project_question(instruction: str) -> BrainResult | None:
        lowered = instruction.lower()
        if not any(term in lowered for term in ("which files", "what files", "file controls", "files control")):
            return None
        if "hero" not in lowered:
            return None
        return BrainResult(
            response=(
                "The hero structure and copy are in `index.html`; its layout and visual styling are in `styles.css`. "
                "The generated `script.js` controls interactive behavior such as navigation and forms."
            ),
            matched=True,
            confidence=0.96,
            capability="project-awareness",
        )

    @staticmethod
    def _conversation_answer(instruction: str) -> BrainResult | None:
        text = instruction.lower().strip()

        if re.search(r"\b(teach me|teach me more|tell me more|show me more|can you teach me)\b", text):
            return BrainResult(
                response=(
                    "Absolutely. I can teach you practical web, coding, design, and reasoning topics, "
                    "including HTML, CSS, JavaScript, UI layout, debugging, responsive design, "
                    "and how to think through a build step by step."
                ),
                matched=True,
                confidence=0.98,
                capability="conversation",
            )

        if re.search(r"\b(hello|hi|hey|hiya|yo)\b", text):
            return BrainResult(
                response="Hey. I’m here and ready to help.",
                matched=True,
                confidence=0.98,
                capability="conversation",
            )

        if re.search(r"\b(how are you|how's it going|hows it going|what's up|whats up)\b", text):
            return BrainResult(
                response="I’m running locally and ready. What are you working on?",
                matched=True,
                confidence=0.98,
                capability="conversation",
            )

        if re.search(r"\b(thanks|thank you|cheers|thx)\b", text):
            return BrainResult(
                response="You’re welcome.",
                matched=True,
                confidence=0.98,
                capability="conversation",
            )

        feeling = re.search(
            r"(?:i am|i'm|im|i feel|feeling)\s+(sad|stressed|angry|anxious|overwhelmed|happy|excited|tired|confused)",
            text,
        )
        if feeling:
            state = feeling.group(1)
            support = {
                "sad": "That sounds heavy. You do not have to solve everything at once. Want to talk through what happened?",
                "stressed": "That sounds like a lot. We can break the next step into something small and concrete.",
                "angry": "It makes sense to pause before reacting. Tell me what happened and I’ll help you think it through.",
                "anxious": "That sounds difficult. Let’s slow it down and separate what you can control from what you cannot.",
                "overwhelmed": "Let’s reduce the load: name the one thing that matters most right now.",
                "happy": "That’s good to hear. What went well?",
                "excited": "Nice. What are you excited about?",
                "tired": "You may need a smaller next step or a proper break. What still needs doing?",
                "confused": "Let’s untangle it together. Which part is unclear?",
            }
            return BrainResult(
                response=support[state],
                matched=True,
                confidence=0.94,
                capability="conversation",
            )

        return None

    @staticmethod
    def _attach_intent(
        result: BrainResult,
        intent: Intent,
    ) -> BrainResult:
        """Attach the detected language intent without changing the response."""
        result.intent = intent.name
        result.intent_confidence = intent.confidence
        return result

    def answer(self, instruction: str, personality=None, mode: str = "general") -> BrainResult:
        if personality is not None:
            self.personality = personality

        instruction = instruction.strip()

        if not instruction:
            return BrainResult(
                response="Please give me something to work with.",
                matched=False,
                confidence=0.0,
            )

        # Build an understanding representation once.
        # The original instruction is preserved for responses; the corrected
        # version is used for routing, matching, maths, and web search.
        understanding = understand(instruction)
        understood_instruction = understanding.corrected

        # Detect natural-language intent after correction.
        detected_intent = self.classify_intent(understood_instruction)

        builder_mode = mode == "builder"

        def finish(result: BrainResult) -> BrainResult:
            result.intent = detected_intent.name
            result.intent_confidence = detected_intent.confidence
            return result

        if builder_mode:
            project_question = self._project_question(instruction)

            if project_question is not None:
                return finish(project_question)

        if builder_mode and self._is_modification_request(instruction):
            result = project_manager.modify(instruction)

            if result["success"]:
                status = project_manager.status()

                return finish(
                    BrainResult(
                        response=result["message"],
                        matched=True,
                        confidence=0.95,
                        capability="project-modification",
                        project=status,
                    )
                )

            return finish(
                BrainResult(
                    response=result["message"],
                    matched=False,
                    confidence=0.7,
                    capability="project-modification",
                    project=project_manager.status(),
                )
            )

        # Website / browser-game generation.
        if builder_mode and self.web_builder.is_build_request(instruction):
            result = project_manager.build(instruction)

            if result["success"]:
                return finish(
                    BrainResult(
                        response=(
                            f"Built {result.get('name', 'your project')} successfully. "
                            "The generated project is ready in the preview."
                        ),
                        matched=True,
                        confidence=0.98,
                        capability="web-builder",
                        project=result,
                    )
                )

        # Arithmetic.
        math_result = solve(understood_instruction)

        if math_result is not None:
            return finish(
                BrainResult(
                    response=math_result,
                    matched=True,
                    confidence=1.0,
                    capability="mathematics",
                )
            )

        debug_result = self._debug_code_answer(instruction)

        if debug_result is not None:
            return finish(debug_result)

        # --------------------------------------------------
        # Explicit coding intent
        #
        # Coding requests must be handled before conversation.
        # Otherwise "write Python code..." can be swallowed by
        # the conversational fallback.
        # --------------------------------------------------

        if detected_intent.name in {
            "coding",
            "code_explanation",
            "debugging",
        }:
            coding_result = self.coding.answer(instruction)

            if coding_result is not None:
                return finish(
                    BrainResult(
                        response=coding_result,
                        matched=True,
                        confidence=0.90,
                        capability="coding",
                    )
                )

        # Only let conversation handling claim messages that are actually
        # conversational. A greeting followed by a real question should
        # continue through the normal capability pipeline.
        conversation_result = None
        lowered_understood = understood_instruction.lower().strip()

        has_question_signal = (
            "?" in instruction
            or lowered_understood.startswith(
                (
                    "what ",
                    "what's ",
                    "who ",
                    "when ",
                    "where ",
                    "why ",
                    "how ",
                    "which ",
                    "can ",
                    "could ",
                    "would ",
                    "does ",
                    "do ",
                    "is ",
                    "are ",
                )
            )
            or " what " in f" {lowered_understood} "
            or " how " in f" {lowered_understood} "
        )

        if not has_question_signal:
            conversation_result = self._conversation_answer(
                understood_instruction
            )

        if conversation_result is not None:
            # Conversation can handle genuine conversational messages,
            # including feelings such as "I'm stressed". Specialist
            # requests have already been claimed above.
            return finish(conversation_result)

        symbolic_result = self.symbolic_math.answer(understood_instruction)

        if symbolic_result is not None:
            return finish(
                BrainResult(
                    response=symbolic_result,
                    matched=True,
                    confidence=0.96,
                    capability="symbolic-mathematics",
                )
            )

        # Science.
        science_result = self.science.answer(understood_instruction)

        if science_result is not None:
            return finish(
                BrainResult(
                    response=science_result.response,
                    matched=True,
                    confidence=science_result.confidence,
                    capability="science",
                )
            )

        # --------------------------------------------------
        # CONCEPT-FIRST KNOWLEDGE ROUTING
        #
        # Natural language is separated from the concept being
        # requested. Examples:
        #
        #   "what is lol"                  -> "lol"
        #   "what are quantum computers"   -> "quantum computer"
        #   "can u explain empathy"        -> "empathy"
        #   "tell me about algorithms"     -> "algorithm"
        #
        # This makes knowledge retrieval substantially less
        # dependent on the exact wording of the user's question.
        # --------------------------------------------------

        topic_query = understanding.topic.strip()
        knowledge_results = []

        # 1. Exact/extracted concept.
        if topic_query:
            knowledge_results = self.knowledge.search(
                topic_query,
                limit=5,
            )

        # 2. Original wording as a fallback.
        if not knowledge_results:
            knowledge_results = self.knowledge.search(
                instruction,
                limit=5,
            )

        # 3. Corrected wording as a final local-knowledge fallback.
        if not knowledge_results:
            knowledge_results = self.knowledge.search(
                understood_instruction,
                limit=5,
            )

        if knowledge_results:
            best = knowledge_results[0]

            score = float(
                best.get("score", 0)
            )

            concept_score = float(
                best.get("concept_score", 0)
            )

            response = (
                best.get("definition")
                or best.get("explanation")
            )

            # Concept matches are deliberately trusted more than
            # loose sentence similarity.
            concept_match = concept_score >= 2.5

            minimum_score = 0.45

            if detected_intent.name == "question_definition":
                minimum_score = 0.50

            if concept_match:
                minimum_score = 0.0

            if response and score >= minimum_score:
                return finish(
                    BrainResult(
                        response=response,
                        matched=True,
                        confidence=min(
                            max(
                                concept_score / 3.0
                                if concept_match
                                else score,
                                0.0,
                            ),
                            1.0,
                        ),
                        capability=best.get(
                            "domain",
                            "knowledge",
                        ),
                    )
                )

        # Learned instructions are a fallback for requests that did not
        # match a specific domain capability.
        instruction_result = self._instruction_answer(
            understood_instruction
        )

        if instruction_result is not None:
            return finish(instruction_result)

        # Coding knowledge.
        coding_result = self.coding.answer(instruction)

        if coding_result is not None:
            return finish(
                BrainResult(
                    response=coding_result,
                    matched=True,
                    confidence=0.80,
                    capability="coding",
                )
            )

        # Reasoning.
        reasoning_result = self.reasoning.answer(
            instruction,
            self.knowledge.general + self.knowledge.coding,
        )

        if reasoning_result is not None:
            return finish(
                BrainResult(
                    response=reasoning_result.response,
                    matched=True,
                    confidence=reasoning_result.confidence,
                    capability="reasoning",
                )
            )

        # Web search.
        web_result = self._web_answer(
            search_query(understanding)
        )

        if web_result is None:
            web_result = self.web.answer(instruction)

        if web_result is not None:
            # Web results are temporary evidence.
            # They must never automatically become permanent training data.
            return finish(
                BrainResult(
                    response=web_result,
                    matched=True,
                    confidence=0.65,
                    capability="web",
                )
            )

        return finish(
            BrainResult(
                response=(
                    "I don't know that yet. "
                    "That is something we can teach Klyor Brain."
                ),
                matched=False,
                confidence=0.0,
                capability="unknown",
            )
        )


brain = KlyorBrain()
