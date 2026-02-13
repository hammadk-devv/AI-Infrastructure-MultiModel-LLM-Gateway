import asyncio
import os
from sdk.python.llm_gateway.client import GatewayClient

async def run_demo():
    print("🚀 Starting AI Gateway Demo...")
    
    # Use the local gateway on port 8001
    async with GatewayClient(api_key="lkg_test_123", base_url="http://localhost:8001") as client:
        print("📡 Sending completion request to GPT-4o...")
        try:
            response = await client.create_completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Tell me a joke about AI infrastructure."}]
            )
            print("\n✨ Response from Gateway:")
            print(f"Model: {response.get('model')}")
            print(f"Content: {response.get('choices')[0].get('message').get('content')}")
        except Exception as e:
            print(f"❌ Error during request: {e}")
            print("Note: This might be expected if API keys in .env are invalid/missing quota.")

    print("\n✅ Demo finished.")

if __name__ == "__main__":
    asyncio.run(run_demo())
