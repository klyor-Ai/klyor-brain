import httpx

from .config import settings


class BrainModelError(Exception):
    pass


async def chat(messages: list[dict]) -> tuple[str, dict]:
    url = f"{settings.base_url}/chat/completions"

    payload = {
        "model": settings.model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload)

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text

            raise BrainModelError(
                f"Local model returned HTTP {response.status_code}: {detail}"
            )

        data = response.json()

    except httpx.ConnectError:
        raise BrainModelError(
            "Cannot connect to the local model. Start Ollama and make sure a model is installed."
        )
    except httpx.TimeoutException:
        raise BrainModelError(
            "The local model took too long to respond."
        )
    except BrainModelError:
        raise
    except Exception as exc:
        raise BrainModelError(f"Model request failed: {exc}")

    choices = data.get("choices", [])

    if not choices:
        raise BrainModelError("The model returned no response.")

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if not content:
        raise BrainModelError("The model returned an empty response.")

    usage = data.get("usage") or {}

    return content, {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }
