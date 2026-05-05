<<<<<<< Updated upstream
---
name: google_gemini
description: "Use when any EOS module needs to call Gemini models for text generation, multimodal analysis, embeddings, or function calling via the google.genai Python SDK."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://ai.google.dev/gemini-api/docs"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "google-genai 1.68.0"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Google Gemini
<!--
TOOL SKILL TEMPLATE v1.0
Researched from official documentation + installed SDK inspection.
References contain the authoritative source.
SKILL.md = how EOS uses it.
references/best_practices.md = what docs say.
Update references/ when tool releases updates.
SKILL.md updates only if interface changed.
-->

## What This Tool Does

Google Gemini is a family of multimodal large language models from Google DeepMind.
EOS uses Gemini as its PRIMARY LLM provider when Anthropic credits are depleted.

Core capabilities:
- **Text generation** — conversation, analysis, scoring, classification
- **Multimodal input** — images, video, audio, PDF documents natively in prompt
- **Embeddings** — gemini-embedding-001 and text-embedding-004 for semantic search
- **Function calling** — structured tool use with JSON schema declarations
- **Grounding** — Google Search grounding for real-time factual responses
- **Code execution** — server-side Python sandbox for computation
- **Context caching** — cache large contexts to reduce cost on repeated queries
- **Long context** — up to 1M tokens input on 2.5 Pro and 2.5 Flash
- **Thinking** — 2.5 models support configurable thinking budgets for complex reasoning

Design philosophy: multimodal-native from the ground up. Unlike wrapper APIs that bolt
vision onto text models, Gemini processes all modalities in a single forward pass.
Interleaved text+image+audio in a single prompt is first-class, not an afterthought.

### Model Lineup (current)

| Model | Input Limit | Output Limit | Key Strengths |
|---|---|---|---|
| gemini-2.5-pro | 1,048,576 | 65,536 | Best reasoning, code, complex tasks, thinking |
| gemini-2.5-flash | 1,048,576 | 65,536 | Fast, cheap, good quality, thinking budget |
| gemini-2.0-flash | 1,048,576 | 8,192 | Legacy — deprecated for new users |
| gemini-1.5-pro | 2,097,152 | 8,192 | Legacy — 2M context window |
| gemini-1.5-flash | 1,048,576 | 8,192 | Legacy — cheapest |
| gemini-embedding-001 | 8,192 | N/A | Embeddings, 768 dimensions |
| text-embedding-004 | 2,048 | N/A | Embeddings, 768 dimensions |

**EOS default: gemini-2.5-flash** — best cost/quality/speed tradeoff.

## EOS Integration

### Primary: model_router.py
- Registered as `gemini-pro` in MODEL_REGISTRY with model_id `gemini-2.5-flash`
- Provider priority: CC_SDK (0) > Anthropic (1) > **Gemini (2)** > Groq (3) > Ollama (5)
- Quality score: 0.65 (at escalation threshold — responses accepted, not escalated)
- Strengths: MULTIMODAL, LONG_CONTEXT, ANALYSIS, FAST_RESPONSE, CONVERSATION
- Cost tracked: $0.000075 per 1K tokens
- Called via `ModelRouter._call_gemini()` using `google.genai.Client`

### Secondary: embedding_engine.py
- Tier 2 fallback (after fastembed local, 384-dim)
- Uses `gemini-embedding-001` (768-dim vectors)
- Activated when fastembed fails or unavailable

### Secondary: media_processor.py
- Processes images, video, audio, documents via Gemini multimodal
- Uses `google.genai` new SDK with `genai_types` for config
- Falls back to old `google.generativeai` SDK if new SDK unavailable

### Other modules referencing Gemini:
- `system_health.py` — health checks on Gemini availability
- `gateway.py` — message classification routing
- `cognitive_loop.py` — core PERCEIVE/GENERATE/ACT loop
- `error_handler.py` — Gemini-specific error recovery patterns
- `harness_registry.py` — harness configuration
- `knowledge_domains.py` — domain knowledge routing
- `model_preferences.py` — business context model selection

## Authentication

### API Key (EOS method)
```python
# In eos_ai/.env
GEMINI_API_KEY=your-api-key-here

# In code — always load from env, never hardcode
from google import genai
import os
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
```

### How EOS loads it
```python
from dotenv import load_dotenv
from pathlib import Path
# Services .env first, eos_ai .env second (wins on conflict)
load_dotenv(Path(__file__).parent.parent / 'services' / '.env')
load_dotenv(Path(__file__).parent.parent / 'eos_ai' / '.env', override=True)
# Then os.getenv('GEMINI_API_KEY')
```

Never hardcode the API key. Always `os.getenv('GEMINI_API_KEY')`.

### Vertex AI auth (not used in EOS — for reference)
```python
client = genai.Client(
    vertexai=True,
    project='your-project-id',
    location='us-central1',
)
```

## Quick Reference

### Text generation (EOS pattern — matches model_router._call_gemini)
```python
from google import genai
from google.genai import types as genai_types
import os

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Analyze this business situation.',
    config=genai_types.GenerateContentConfig(
        max_output_tokens=1000,
        system_instruction='You are a business analyst.',
        temperature=0.7,
    ),
)
print(response.text)
```

### Multimodal (image + text)
```python
from pathlib import Path
from google.genai import types as genai_types

image_bytes = Path('screenshot.png').read_bytes()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        genai_types.Part.from_bytes(data=image_bytes, mime_type='image/png'),
        'What competitor tactics do you see in this screenshot?',
    ],
)
print(response.text)
```

### Embeddings (matches embedding_engine.py Tier 2)
```python
result = client.models.embed_content(
    model='gemini-embedding-001',
    contents='text to embed',
)
vector = result.embeddings[0].values  # list[float], 768-dim
```

### Function calling
```python
tools = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name='get_lead_status',
            description='Get the status of a lead in the CRM',
            parameters=genai_types.Schema(
                type='OBJECT',
                properties={
                    'lead_id': genai_types.Schema(type='STRING'),
                },
                required=['lead_id'],
            ),
        ),
    ],
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What is the status of lead ABC123?',
    config=genai_types.GenerateContentConfig(tools=[tools]),
)
# Check response.candidates[0].content.parts for function_call
```

### Streaming
```python
response = client.models.generate_content_stream(
    model='gemini-2.5-flash',
    contents='Write a market analysis.',
    config=genai_types.GenerateContentConfig(max_output_tokens=2000),
)
for chunk in response:
    print(chunk.text, end='', flush=True)
```

### Context caching (cost optimization)
```python
cache = client.caches.create(
    model='gemini-2.5-flash',
    contents=[large_document_text],
    config=genai_types.CreateCachedContentConfig(
        display_name='business-docs',
        ttl='3600s',
    ),
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Summarize the key risks.',
    config=genai_types.GenerateContentConfig(
        cached_content=cache.name,
    ),
)
```

### Thinking (2.5 models only)
```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Solve this complex problem step by step.',
    config=genai_types.GenerateContentConfig(
        thinking_config=genai_types.ThinkingConfig(
            thinking_budget=1024,
        ),
    ),
)
```

### File upload (for large media >20MB)
```python
uploaded = client.files.upload(
    file='large_video.mp4',
    config=genai_types.UploadFileConfig(mime_type='video/mp4'),
)
# Poll until processing complete
import time
while uploaded.state.name == 'PROCESSING':
    time.sleep(2)
    uploaded = client.files.get(name=uploaded.name)

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[uploaded, 'Analyze this video.'],
)
```

## Gotchas

### Confirmed in EOS production

1. **Spending cap 429** — Gemini API returns HTTP 429 when the project spending
   cap is exceeded. All calls fail until the cap is raised in Google AI Studio >
   Settings. This is NOT a rate limit — it is a billing cap. The error message
   references "billing" or "quota", not "RESOURCE_EXHAUSTED".

2. **gemini-2.0-flash deprecated** — Returns 404 or degraded responses for new
   API keys. Always use `gemini-2.5-flash`. Update any code still referencing 2.0.

3. **Old SDK deprecated** — `google.generativeai` (`import google.generativeai as genai`)
   is deprecated. Always use `google.genai` (`from google import genai`). The old SDK
   uses `genai.configure()` + `genai.GenerativeModel()`. The new SDK uses
   `genai.Client()` + `client.models.generate_content()`. Incompatible patterns.

4. **response.text can be None** — Safety filters or empty content return `None`,
   not `""`. Always guard: `response.text or ""`. EOS does this in model_router.py.

5. **Rate limit vs spending cap** — Both return 429. Rate limits say
   "RESOURCE_EXHAUSTED" in error body. Spending caps reference "billing" or "quota".
   Different recovery: rate limits need backoff, spending caps need console action.

6. **System instruction in config** — New SDK: `GenerateContentConfig(system_instruction=...)`.
   NOT a top-level parameter on `generate_content()`. EOS model_router.py does this correctly.

7. **Large media requires file upload** — Videos/audio over ~20MB must use
   `client.files.upload()` then reference by URI. Inline base64 practical limit ~20MB.

8. **Embedding model confusion** — `text-embedding-004` (2048 token limit) and
   `gemini-embedding-001` (8192 token limit) are different models. EOS uses
   `gemini-embedding-001` in embedding_engine.py.

9. **Temperature 0 not deterministic** — Responses vary even with temperature=0.
   Use `seed` parameter for more consistency (still not guaranteed).

10. **Thinking tokens billed as output** — 2.5 model thinking budget tokens count
    toward output token billing even if not visible in response text.

11. **Ollama fallback truncation** — When Gemini is down and Ollama catches the
    request, system prompts get truncated to 3000 chars and prompts to 4000 chars.
    Quality drops significantly. Monitor Gemini availability.

See references/best_practices.md for rate limits, error codes, pricing, and advanced patterns.
=======
---
name: google_gemini
description: "Use when any EOS module needs to call Gemini models for text generation, multimodal analysis, embeddings, or function calling via the google.genai Python SDK."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://ai.google.dev/gemini-api/docs"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "google-genai 1.68.0"
speed_category: fast
---

# Tool: Google Gemini
<!--
TOOL SKILL TEMPLATE v1.0
Researched from official documentation + installed SDK inspection.
References contain the authoritative source.
SKILL.md = how EOS uses it.
references/best_practices.md = what docs say.
Update references/ when tool releases updates.
SKILL.md updates only if interface changed.
-->

## What This Tool Does

Google Gemini is a family of multimodal large language models from Google DeepMind.
EOS uses Gemini as its PRIMARY LLM provider when Anthropic credits are depleted.

Core capabilities:
- **Text generation** — conversation, analysis, scoring, classification
- **Multimodal input** — images, video, audio, PDF documents natively in prompt
- **Embeddings** — gemini-embedding-001 and text-embedding-004 for semantic search
- **Function calling** — structured tool use with JSON schema declarations
- **Grounding** — Google Search grounding for real-time factual responses
- **Code execution** — server-side Python sandbox for computation
- **Context caching** — cache large contexts to reduce cost on repeated queries
- **Long context** — up to 1M tokens input on 2.5 Pro and 2.5 Flash
- **Thinking** — 2.5 models support configurable thinking budgets for complex reasoning

Design philosophy: multimodal-native from the ground up. Unlike wrapper APIs that bolt
vision onto text models, Gemini processes all modalities in a single forward pass.
Interleaved text+image+audio in a single prompt is first-class, not an afterthought.

### Model Lineup (current)

| Model | Input Limit | Output Limit | Key Strengths |
|---|---|---|---|
| gemini-2.5-pro | 1,048,576 | 65,536 | Best reasoning, code, complex tasks, thinking |
| gemini-2.5-flash | 1,048,576 | 65,536 | Fast, cheap, good quality, thinking budget |
| gemini-2.0-flash | 1,048,576 | 8,192 | Legacy — deprecated for new users |
| gemini-1.5-pro | 2,097,152 | 8,192 | Legacy — 2M context window |
| gemini-1.5-flash | 1,048,576 | 8,192 | Legacy — cheapest |
| gemini-embedding-001 | 8,192 | N/A | Embeddings, 768 dimensions |
| text-embedding-004 | 2,048 | N/A | Embeddings, 768 dimensions |

**EOS default: gemini-2.5-flash** — best cost/quality/speed tradeoff.

## EOS Integration

### Primary: model_router.py
- Registered as `gemini-pro` in MODEL_REGISTRY with model_id `gemini-2.5-flash`
- Provider priority: CC_SDK (0) > Anthropic (1) > **Gemini (2)** > Groq (3) > Ollama (5)
- Quality score: 0.65 (at escalation threshold — responses accepted, not escalated)
- Strengths: MULTIMODAL, LONG_CONTEXT, ANALYSIS, FAST_RESPONSE, CONVERSATION
- Cost tracked: $0.000075 per 1K tokens
- Called via `ModelRouter._call_gemini()` using `google.genai.Client`

### Secondary: embedding_engine.py
- Tier 2 fallback (after fastembed local, 384-dim)
- Uses `gemini-embedding-001` (768-dim vectors)
- Activated when fastembed fails or unavailable

### Secondary: media_processor.py
- Processes images, video, audio, documents via Gemini multimodal
- Uses `google.genai` new SDK with `genai_types` for config
- Falls back to old `google.generativeai` SDK if new SDK unavailable

### Other modules referencing Gemini:
- `system_health.py` — health checks on Gemini availability
- `gateway.py` — message classification routing
- `cognitive_loop.py` — core PERCEIVE/GENERATE/ACT loop
- `error_handler.py` — Gemini-specific error recovery patterns
- `harness_registry.py` — harness configuration
- `knowledge_domains.py` — domain knowledge routing
- `model_preferences.py` — business context model selection

## Authentication

### API Key (EOS method)
```python
# In eos_ai/.env
GEMINI_API_KEY=your-api-key-here

# In code — always load from env, never hardcode
from google import genai
import os
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
```

### How EOS loads it
```python
from dotenv import load_dotenv
from pathlib import Path
# Services .env first, eos_ai .env second (wins on conflict)
load_dotenv(Path(__file__).parent.parent / 'services' / '.env')
load_dotenv(Path(__file__).parent.parent / 'eos_ai' / '.env', override=True)
# Then os.getenv('GEMINI_API_KEY')
```

Never hardcode the API key. Always `os.getenv('GEMINI_API_KEY')`.

### Vertex AI auth (not used in EOS — for reference)
```python
client = genai.Client(
    vertexai=True,
    project='your-project-id',
    location='us-central1',
)
```

## Quick Reference

### Text generation (EOS pattern — matches model_router._call_gemini)
```python
from google import genai
from google.genai import types as genai_types
import os

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Analyze this business situation.',
    config=genai_types.GenerateContentConfig(
        max_output_tokens=1000,
        system_instruction='You are a business analyst.',
        temperature=0.7,
    ),
)
print(response.text)
```

### Multimodal (image + text)
```python
from pathlib import Path
from google.genai import types as genai_types

image_bytes = Path('screenshot.png').read_bytes()
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        genai_types.Part.from_bytes(data=image_bytes, mime_type='image/png'),
        'What competitor tactics do you see in this screenshot?',
    ],
)
print(response.text)
```

### Embeddings (matches embedding_engine.py Tier 2)
```python
result = client.models.embed_content(
    model='gemini-embedding-001',
    contents='text to embed',
)
vector = result.embeddings[0].values  # list[float], 768-dim
```

### Function calling
```python
tools = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name='get_lead_status',
            description='Get the status of a lead in the CRM',
            parameters=genai_types.Schema(
                type='OBJECT',
                properties={
                    'lead_id': genai_types.Schema(type='STRING'),
                },
                required=['lead_id'],
            ),
        ),
    ],
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What is the status of lead ABC123?',
    config=genai_types.GenerateContentConfig(tools=[tools]),
)
# Check response.candidates[0].content.parts for function_call
```

### Streaming
```python
response = client.models.generate_content_stream(
    model='gemini-2.5-flash',
    contents='Write a market analysis.',
    config=genai_types.GenerateContentConfig(max_output_tokens=2000),
)
for chunk in response:
    print(chunk.text, end='', flush=True)
```

### Context caching (cost optimization)
```python
cache = client.caches.create(
    model='gemini-2.5-flash',
    contents=[large_document_text],
    config=genai_types.CreateCachedContentConfig(
        display_name='business-docs',
        ttl='3600s',
    ),
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Summarize the key risks.',
    config=genai_types.GenerateContentConfig(
        cached_content=cache.name,
    ),
)
```

### Thinking (2.5 models only)
```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Solve this complex problem step by step.',
    config=genai_types.GenerateContentConfig(
        thinking_config=genai_types.ThinkingConfig(
            thinking_budget=1024,
        ),
    ),
)
```

### File upload (for large media >20MB)
```python
uploaded = client.files.upload(
    file='large_video.mp4',
    config=genai_types.UploadFileConfig(mime_type='video/mp4'),
)
# Poll until processing complete
import time
while uploaded.state.name == 'PROCESSING':
    time.sleep(2)
    uploaded = client.files.get(name=uploaded.name)

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[uploaded, 'Analyze this video.'],
)
```

## Gotchas

### Confirmed in EOS production

1. **Spending cap 429** — Gemini API returns HTTP 429 when the project spending
   cap is exceeded. All calls fail until the cap is raised in Google AI Studio >
   Settings. This is NOT a rate limit — it is a billing cap. The error message
   references "billing" or "quota", not "RESOURCE_EXHAUSTED".

2. **gemini-2.0-flash deprecated** — Returns 404 or degraded responses for new
   API keys. Always use `gemini-2.5-flash`. Update any code still referencing 2.0.

3. **Old SDK deprecated** — `google.generativeai` (`import google.generativeai as genai`)
   is deprecated. Always use `google.genai` (`from google import genai`). The old SDK
   uses `genai.configure()` + `genai.GenerativeModel()`. The new SDK uses
   `genai.Client()` + `client.models.generate_content()`. Incompatible patterns.

4. **response.text can be None** — Safety filters or empty content return `None`,
   not `""`. Always guard: `response.text or ""`. EOS does this in model_router.py.

5. **Rate limit vs spending cap** — Both return 429. Rate limits say
   "RESOURCE_EXHAUSTED" in error body. Spending caps reference "billing" or "quota".
   Different recovery: rate limits need backoff, spending caps need console action.

6. **System instruction in config** — New SDK: `GenerateContentConfig(system_instruction=...)`.
   NOT a top-level parameter on `generate_content()`. EOS model_router.py does this correctly.

7. **Large media requires file upload** — Videos/audio over ~20MB must use
   `client.files.upload()` then reference by URI. Inline base64 practical limit ~20MB.

8. **Embedding model confusion** — `text-embedding-004` (2048 token limit) and
   `gemini-embedding-001` (8192 token limit) are different models. EOS uses
   `gemini-embedding-001` in embedding_engine.py.

9. **Temperature 0 not deterministic** — Responses vary even with temperature=0.
   Use `seed` parameter for more consistency (still not guaranteed).

10. **Thinking tokens billed as output** — 2.5 model thinking budget tokens count
    toward output token billing even if not visible in response text.

11. **Ollama fallback truncation** — When Gemini is down and Ollama catches the
    request, system prompts get truncated to 3000 chars and prompts to 4000 chars.
    Quality drops significantly. Monitor Gemini availability.

See references/best_practices.md for rate limits, error codes, pricing, and advanced patterns.
>>>>>>> Stashed changes
