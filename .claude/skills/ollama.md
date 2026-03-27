# Ollama — Best Practices

## When to use
Local LLM fallback when Anthropic credits are depleted.
Current model: `qwen2.5:3b`
EOS routes to Ollama automatically via `agent_runtime.py`.

## Check if running
```bash
curl -s http://localhost:11434/api/tags
# Returns JSON with models list
```

## Direct API call
```python
import requests

def call_ollama(
    prompt: str,
    system: str = '',
    model: str = 'qwen2.5:3b',
    max_tokens: int = 1000,
) -> str:
    payload = {
        'model': model,
        'prompt': prompt,
        'system': system,
        'stream': False,
        'options': {'num_predict': max_tokens},
    }
    try:
        resp = requests.post(
            'http://localhost:11434/api/generate',
            json=payload,
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get('response', '').strip()
        print(f'[Ollama] HTTP {resp.status_code}')
        return ''
    except requests.exceptions.Timeout:
        print('[Ollama] Timeout — model may be loading')
        return ''
    except Exception as e:
        print(f'[Ollama] Error: {e}')
        return ''
```

## Chat format (preferred for conversations)
```python
payload = {
    'model': 'qwen2.5:3b',
    'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message},
    ],
    'stream': False,
    'options': {'num_predict': 500},
}
resp = requests.post('http://localhost:11434/api/chat', json=payload, timeout=60)
text = resp.json().get('message', {}).get('content', '').strip()
```

## Available models
```bash
ollama list
```

## Performance notes
- `qwen2.5:3b` — fast (~2-5s), good for routing/classification/simple Q&A
- First call loads model into memory — may take 10-15s on cold start
- Subsequent calls are fast
- Response quality lower than Claude — use for triage, not world-class output
- Timeout: always use 60s+ to handle cold starts

## EOS routing
`agent_runtime.py` routes to Ollama when:
- Anthropic credits depleted
- Task type is simple classification or routing
- `model_preferences.py` selects local model

## Common mistakes
- Setting timeout too low (causes spurious failures on cold start)
- Expecting Claude-quality reasoning — Qwen 3B is capable but limited
- Not checking if Ollama is running before calling
- Using `stream: True` without handling streaming response
- Forgetting to strip whitespace from `response` field
