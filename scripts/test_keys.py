import asyncio
import httpx
from app.core.settings import get_settings
from app.application.llm.gemini_adapter import GeminiAdapter
from app.domain.adapters import LLMCompletionRequest, LLMMessage, MessageRole

async def test_gemini():
    settings = get_settings()
    print(f"Using Gemini API Key: {settings.gemini_api_key[:10]}...")
    
    client = httpx.AsyncClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        headers={
            "Content-Type": "application/json",
        }
    )
    adapter = GeminiAdapter(client)
    
    req = LLMCompletionRequest(
        model="gemini-1.5-flash",
        messages=[LLMMessage(role=MessageRole.USER, content="Say hello")],
        temperature=0.7,
        max_tokens=10,
        tools=None,
        tool_choice=None,
        request_id="test-request"
    )
    
    try:
        result = await adapter.acompletion(req)
        print(f"Success: {result.content}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_gemini())
