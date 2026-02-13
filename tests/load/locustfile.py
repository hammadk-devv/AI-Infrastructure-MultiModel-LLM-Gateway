import random
import uuid
from locust import HttpUser, task, between

class AIIGatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task(3)
    def chat_completion_openai(self):
        self._chat_completion("gpt-4o")

    @task(2)
    def chat_completion_anthropic(self):
        self._chat_completion("claude-3-5-sonnet-latest")

    @task(1)
    def chat_completion_gemini(self):
        self._chat_completion("gemini-1.5-pro")

    def _chat_completion(self, model: str):
        request_id = str(uuid.uuid4())
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": f"Hello, I am testing model {model}. Generate a 10 word response."}
            ],
            "temperature": 0.7,
            "stream": False,
            "metadata": {
                "request_id": request_id,
                "tags": ["load-test"]
            }
        }
        
        # Note: In actual load test, provide a valid x-api-key header
        headers = {
            "x-api-key": "lkg_test_key_for_load_test",
            "Content-Type": "application/json"
        }
        
        with self.client.post("/v1/chat/completions", json=payload, headers=headers, name=f"/chat/completions [{model}]") as response:
            if response.status_code != 200:
                response.failure(f"Failed with status {response.status_code}: {response.text}")

    @task(1)
    def health_check(self):
        self.client.get("/internal/health")
