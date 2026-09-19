from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from brain.config import settings
from brain.model import BrainModelError, chat
from brain.prompts import SYSTEM_PROMPT
from brain.schemas import ChatRequest, ChatResponse

app = FastAPI(
    title="Klyor Brain",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "model": settings.model,
        "backend": settings.base_url,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    for message in request.messages:
        if message.role not in {"user", "assistant"}:
            continue

        if not message.content.strip():
            continue

        messages.append(
            {
                "role": message.role,
                "content": message.content,
            }
        )

    if len(messages) == 1:
        return ChatResponse(
            message="Send me a message and let's start teaching Klyor Brain.",
            model=settings.model,
            usage={},
        )

    try:
        response, usage = await chat(messages)

        return ChatResponse(
            message=response,
            model=settings.model,
            usage=usage,
        )

    except BrainModelError as exc:
        return ChatResponse(
            message=f"⚠️ {exc}",
            model=settings.model,
            usage={},
        )


@app.get("/api/model")
async def model_info():
    return {
        "model": settings.model,
        "base_url": settings.base_url,
        "local": True,
        "paid_api_required": False,
    }
