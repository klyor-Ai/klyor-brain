import uvicorn

from brain.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "runtime.api:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
