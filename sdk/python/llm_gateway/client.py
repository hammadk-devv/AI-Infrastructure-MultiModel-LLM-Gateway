import httpx
import json
from typing import Any, Dict, List, Optional, Union, AsyncIterator

class GatewayClient:
    """Official Python SDK for the AI Infrastructure LLM Gateway."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=self.timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def close(self):
        await self.client.aclose()

    async def create_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        cache: bool = True,
        fallback: bool = True,
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Create a chat completion."""
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "cache": {"enabled": cache},
            "fallback": {"enabled": fallback}
        }

        if stream:
            return self._stream_request(payload)
        
        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def _stream_request(self, payload: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """Handle streaming requests."""
        async with self.client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield json.loads(data)
