from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: str = "general"


class ChatResponse(BaseModel):
    message: str
    learned: bool
    confidence: float
    capability: str = "unknown"
    project: dict | None = None
    status: str = "ready"


class BrainStats(BaseModel):
    training_examples: int
    engine: str
