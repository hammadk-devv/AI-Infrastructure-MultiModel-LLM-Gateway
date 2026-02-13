# API Reference

## Authentication
All requests must include the `X-API-Key` header.
```bash
curl -H "X-API-Key: lkg_test_123" http://localhost:8000/v1/chat/completions
```

## Endpoints

### 1. Chat Completions
`POST /v1/chat/completions`

**Request Body:**
```json
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

### 2. Model Registry
`GET /admin/models` (Admin Key Required)
List all active models and their configurations.

### 3. Health Check
`GET /internal/health`
Status: `ok` (Publicly accessible)

## Error Catalog
- `401 Unauthorized`: Missing or invalid API key.
- `429 Too Many Requests`: Rate limit per key exceeded.
- `503 Service Unavailable`: All provider fallbacks failed.
