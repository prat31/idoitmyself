import json
from typing import AsyncGenerator, Dict, Any, List
import httpx

from app.core.config import settings


class AIService:
    """Service wrapper for interacting with OpenRouter LLMs."""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.default_model = settings.DEFAULT_AI_MODEL

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": settings.PROJECT_NAME,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions from OpenRouter via Server-Sent Events."""
        if not self.api_key:
            yield "data: " + json.dumps({"error": "OPENROUTER_API_KEY is not configured."}) + "\n\n"
            return

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'error': f'OpenRouter API Error: {response.status_code}', 'detail': error_text.decode()})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n"


ai_service = AIService()
