# Google Gemini — Creator-Level Best Practices
Source: https://ai.google.dev/gemini-api/docs
API Version: v1
SDK Version: google-genai 1.68.0
Last Researched: 2026-04-03

---

# Tier 1 — Technical Mastery

## Authentication

Two auth paths exist. EOS uses API key auth exclusively.

**API Key (Google AI Studio)**
```python
from google import genai
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
```
- Free tier available (rate-limited)
- Paid tier via Google AI Studio billing
- Key scoped to project, not model
- Single key works for all Gemini models including embeddings

**Vertex AI (GCP — not used in EOS)**
```python
client = genai.Client(vertexai=True, project='proj-id', location='us-central1')
```
- Uses ADC (Application Default Credentials)
- IAM-based permissions
- Enterprise features: VPC-SC, CMEK, data residency
- Higher rate limits than AI Studio

Key rotation: generate new key in AI Studio, update `GEMINI_API_KEY` in `.env`,
restart services. Old key works until explicitly deleted.

## Core Operations with Exact Signatures

### generate_content (primary)
```python
response = client.models.generate_content(
    model: str,                    # 'gemini-2.5-flash'
    contents: ContentType,         # str | list[Part] | list[Content]
    config: GenerateContentConfig, # optional — controls generation
)
# Returns: GenerateContentResponse
# response.text -> str | None
# response.candidates -> list[Candidate]
# response.candidates[0].content.parts -> list[Part]
# response.candidates[0].finish_reason -> FinishReason
# response.usage_metadata.prompt_token_count -> int
# response.usage_metadata.candidates_token_count -> int
```

### generate_content_stream
```python
for chunk in client.models.generate_content_stream(
    model='gemini-2.5-flash',
    contents='prompt',
    config=genai_types.GenerateContentConfig(...),
):
    print(chunk.text, end='')
```

### embed_content
```python
result = client.models.embed_content(
    model='gemini-embedding-001',
    contents: str | list[str],
    config: EmbedContentConfig | None,  # task_type, title, output_dimensionality
)
# Returns: EmbedContentResponse
# result.embeddings[0].values -> list[float]  (768-dim default)
```

### count_tokens
```python
result = client.models.count_tokens(
    model='gemini-2.5-flash',
    contents='your text here',
)
# result.total_tokens -> int
```

### files.upload / files.get / files.delete
```python
uploaded = client.files.upload(file='path/to/file', config=UploadFileConfig(mime_type='video/mp4'))
status = client.files.get(name=uploaded.name)  # poll for ACTIVE state
client.files.delete(name=uploaded.name)         # cleanup
```

## Pagination Patterns

Model listing supports pagination:
```python
models = client.models.list(config={'page_size': 50})
for model in models:
    print(model.name)
# Iterator handles pagination automatically in the SDK
```

File listing similarly paginated:
```python
files = client.files.list(config={'page_size': 100})
```

Cache listing:
```python
caches = client.caches.list()
```

No cursor management needed — the SDK iterator handles continuation tokens internally.

## Rate Limits

### Free tier (API key, no billing)
| Model | RPM | TPM | RPD |
|---|---|---|---|
| gemini-2.5-flash | 10 | 250,000 | 500 |
| gemini-2.5-pro | 5 | 250,000 | 25 |
| gemini-2.0-flash | 10 | 250,000 | 500 |
| gemini-1.5-flash | 15 | 1,000,000 | 1,500 |
| gemini-1.5-pro | 2 | 32,000 | 50 |
| gemini-embedding-001 | 5 | 100,000 | 100 |
| text-embedding-004 | 5 | 100,000 | 100 |

### Pay-as-you-go tier
| Model | RPM | TPM | RPD |
|---|---|---|---|
| gemini-2.5-flash | 2,000 | 4,000,000 | 10,000 |
| gemini-2.5-pro | 1,000 | 4,000,000 | 5,000 |
| gemini-2.0-flash | 2,000 | 4,000,000 | 10,000 |
| gemini-1.5-flash | 2,000 | 4,000,000 | 10,000 |
| gemini-1.5-pro | 1,000 | 4,000,000 | 10,000 |
| gemini-embedding-001 | 1,500 | 4,000,000 | unlimited |

RPM = requests per minute. TPM = tokens per minute. RPD = requests per day.

### Spending caps
Separate from rate limits. Set in Google AI Studio > Settings > Billing.
Default spending cap may be low ($0 on new projects). 429 errors from spending
caps look different from rate limit 429s — check error body.

## Error Codes and Recovery

| HTTP Code | Error Type | Meaning | Recovery |
|---|---|---|---|
| 400 | INVALID_ARGUMENT | Bad request (malformed content, unsupported model) | Fix request |
| 403 | PERMISSION_DENIED | API key invalid or lacks permissions | Verify key |
| 404 | NOT_FOUND | Model does not exist or is deprecated | Use current model name |
| 429 | RESOURCE_EXHAUSTED | Rate limit exceeded (RPM/TPM/RPD) | Exponential backoff |
| 429 | BILLING_QUOTA | Spending cap exceeded | Raise cap in console |
| 500 | INTERNAL | Server error | Retry with backoff |
| 503 | UNAVAILABLE | Model temporarily overloaded | Retry with backoff |

### Backoff strategy (EOS pattern)
```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
def call_gemini(prompt):
    return client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
```

### Distinguishing 429 types
- Rate limit: error message contains "RESOURCE_EXHAUSTED" — back off and retry
- Spending cap: error message contains "quota" or "billing" — no retry, raise cap

## SDK Idioms

### New SDK (google.genai) — ALWAYS USE THIS
```python
from google import genai
from google.genai import types as genai_types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='prompt',
    config=genai_types.GenerateContentConfig(
        max_output_tokens=1000,
        system_instruction='system prompt',
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        stop_sequences=['\n\n'],
        response_mime_type='application/json',  # JSON mode
        seed=42,  # reproducibility
    ),
)
```

### Old SDK (google.generativeai) — DEPRECATED, DO NOT USE
```python
# DO NOT USE — shown only to recognize and migrate legacy code
import google.generativeai as genai
genai.configure(api_key='...')
model = genai.GenerativeModel('gemini-2.5-flash', system_instruction='...')
response = model.generate_content('prompt')
```

### Migration checklist (old -> new)
1. `import google.generativeai as genai` -> `from google import genai`
2. `genai.configure(api_key=...)` -> `client = genai.Client(api_key=...)`
3. `genai.GenerativeModel(model_name)` -> `client.models.generate_content(model=model_name, ...)`
4. `model.generate_content(prompt)` -> `client.models.generate_content(model=..., contents=prompt)`
5. `genai.embed_content(model=..., content=...)` -> `client.models.embed_content(model=..., contents=...)`
6. Generation config as dict -> `genai_types.GenerateContentConfig(...)`
7. Safety settings as dict -> `genai_types.SafetySetting(...)`

## Anti-Patterns

1. **Hardcoding API keys** — Always `os.getenv('GEMINI_API_KEY')`, never a literal string.

2. **Using old SDK in new code** — `google.generativeai` is deprecated. Always `google.genai`.

3. **Not handling None response** — `response.text` returns `None` when blocked by safety
   filters. Always: `response.text or ""`.

4. **Ignoring finish_reason** — `SAFETY`, `RECITATION`, `MAX_TOKENS` all need different handling.
   Only `STOP` means normal completion.

5. **Sending huge inline media** — Files over ~20MB should use `client.files.upload()`.
   Inline base64 bloats request size and can timeout.

6. **Not setting max_output_tokens** — Default varies by model. Always set explicitly
   to control cost and latency.

7. **Using deprecated models** — `gemini-2.0-flash`, `gemini-pro`, `gemini-pro-vision`
   are all deprecated. Use `gemini-2.5-flash` or `gemini-2.5-pro`.

8. **Catching generic Exception without logging** — Gemini errors carry useful metadata
   (error code, retry info). Always log the full exception.

9. **Not using context caching for repeated contexts** — If sending the same large document
   in multiple requests, use `client.caches.create()` to save 75% on input token costs.

10. **Polling file upload without backoff** — `client.files.get()` should have a sleep
    between polls (2-5 seconds). Video processing can take minutes.

## Data Model

### Content structure
```
GenerateContentRequest
  model: str
  contents: list[Content]
    Content
      role: 'user' | 'model'
      parts: list[Part]
        Part (one of):
          text: str
          inline_data: Blob (bytes + mime_type)
          file_data: FileData (file_uri + mime_type)
          function_call: FunctionCall
          function_response: FunctionResponse
  config: GenerateContentConfig
    system_instruction: str
    max_output_tokens: int
    temperature: float
    top_p: float
    top_k: int
    stop_sequences: list[str]
    tools: list[Tool]
    response_mime_type: str
    thinking_config: ThinkingConfig
    cached_content: str
    safety_settings: list[SafetySetting]
```

### Response structure
```
GenerateContentResponse
  candidates: list[Candidate]
    Candidate
      content: Content (role='model', parts=[...])
      finish_reason: FinishReason (STOP|MAX_TOKENS|SAFETY|RECITATION|OTHER)
      safety_ratings: list[SafetyRating]
  usage_metadata: UsageMetadata
    prompt_token_count: int
    candidates_token_count: int
    total_token_count: int
    cached_content_token_count: int
  text: str | None  (convenience accessor for candidates[0].content.parts[0].text)
```

## Webhooks and Events

Gemini API does not support webhooks or push notifications.
All interactions are request/response (synchronous) or streaming.

For async patterns in EOS:
- Use `generate_content_stream()` for progressive output
- Use `client.files.upload()` + polling for async file processing
- EOS model_router wraps calls synchronously — no async needed at router level

The SDK supports `async` via `client.aio.models.generate_content()` for asyncio contexts.

## Limits

### Per-request limits
- Max input tokens: 1,048,576 (2.5 models), 2,097,152 (1.5 Pro)
- Max output tokens: 65,536 (2.5 models), 8,192 (1.5 models)
- Max images per request: 3,600
- Max video length: ~1 hour (inline), longer via file upload
- Max audio length: ~9.5 hours
- Max file upload size: 2GB per file
- Max total file storage: 20GB per project
- File retention: 48 hours after upload (auto-deleted)

### Embedding limits
- gemini-embedding-001: 8,192 tokens input, 768-dim output, batch up to 100
- text-embedding-004: 2,048 tokens input, 768-dim output, batch up to 100
- Configurable output dimensionality via `output_dimensionality` parameter

### Context caching limits
- Minimum cache size: 32,768 tokens
- Maximum TTL: 1 hour default, configurable
- Cache storage billed separately

## Cost Model

### Gemini 2.5 Flash (EOS default)
- Input: $0.15 per 1M tokens (prompts <= 200K tokens)
- Input: $0.30 per 1M tokens (prompts > 200K tokens, up to 1M)
- Output (non-thinking): $0.60 per 1M tokens
- Output (thinking): $3.50 per 1M tokens
- Context caching (input): $0.0375 per 1M tokens (75% discount)
- Context caching storage: $1.00 per 1M tokens per hour

### Gemini 2.5 Pro
- Input: $1.25 per 1M tokens (prompts <= 200K tokens)
- Input: $2.50 per 1M tokens (prompts > 200K tokens)
- Output (non-thinking): $10.00 per 1M tokens
- Output (thinking): $10.00 per 1M tokens

### Gemini 1.5 Flash
- Input: $0.075 per 1M tokens (prompts <= 128K tokens)
- Output: $0.30 per 1M tokens

### Gemini 1.5 Pro
- Input: $1.25 per 1M tokens (prompts <= 128K tokens)
- Output: $5.00 per 1M tokens

### Embeddings
- text-embedding-004: Free tier available; paid at $0.00 per 1M tokens (free)
- gemini-embedding-001: Free tier available; paid pricing TBD

### Multimodal token costs
- Images: ~258 tokens per image (varies by resolution)
- Video: ~260 tokens per second
- Audio: ~32 tokens per second
- These tokens are billed at the input token rate

## Version Pinning

### Model version strategy
- `gemini-2.5-flash` — points to latest stable 2.5 Flash
- `gemini-2.5-flash-preview-04-17` — specific preview snapshot
- `gemini-2.5-pro` — points to latest stable 2.5 Pro
- Always use the base name (no date suffix) for production unless debugging a regression

### SDK version
- `google-genai>=1.0.0` — new SDK, always use this
- Pin in requirements.txt: `google-genai==1.68.0` (current EOS version)
- Breaking changes between 0.x and 1.x — 1.x is the stable API

### Deprecation timeline
- Models deprecated with 12+ months notice
- Old SDK (`google-generativeai`) deprecated since late 2024
- `gemini-2.0-flash` deprecated for new registrations mid-2025

---

# Tier 2 — Creator Intelligence

## Design Intent

Google designed Gemini as a multimodal-native model family to compete directly with
OpenAI GPT-4 and Anthropic Claude. Key design decisions:

1. **Unified multimodal architecture** — All modalities (text, image, audio, video) processed
   in a single transformer, not separate encoders bolted together. This means cross-modal
   reasoning (e.g., "what does the speaker in this video clip mean by the text on screen?")
   is genuinely integrated, not stitched.

2. **Long context as differentiator** — 1M-2M token context windows are a deliberate
   competitive wedge against Claude (200K) and GPT-4 (128K). Google leverages their
   infrastructure advantage (TPUs, data center scale) to make long context cheap.

3. **Flash as the volume model** — 2.5 Flash is positioned as the "good enough for 90% of
   tasks" model at 10x cheaper than Pro. Google wants developers to default to Flash
   and only escalate to Pro when needed. This matches EOS's model_router philosophy.

4. **Thinking as a dial, not a mode** — 2.5 models let you set a thinking_budget rather than
   choosing between "thinking" and "non-thinking" modes. This gives fine-grained control
   over cost/quality tradeoff per-request.

5. **Grounding via Google Search** — Unique capability: Gemini can ground responses in live
   Google Search results. No other major LLM API offers this natively. Useful for
   real-time market intel and fact-checking.

## Problem-Solution Map

| Problem | Gemini Solution | EOS Application |
|---|---|---|
| Need cheap, fast text generation | gemini-2.5-flash at $0.15/1M input | model_router default |
| Analyze competitor screenshots | Multimodal image+text in single call | media_processor.py |
| Process long documents | 1M token context window | cognitive_loop.py |
| Semantic search over conversations | gemini-embedding-001 (768-dim) | embedding_engine.py Tier 2 |
| Structured data extraction | response_mime_type='application/json' | gateway.py classification |
| Real-time market data | Google Search grounding | world_pulse.py (planned) |
| Reduce cost on repeated prompts | Context caching (75% input discount) | Not yet used — opportunity |
| Complex multi-step reasoning | thinking_budget on 2.5 models | CEO agent escalation |
| Video content analysis | Native video input (up to 1hr) | media_processor.py |
| Audio transcription fallback | Native audio input | media_processor.py (Whisper primary) |

### Hidden capabilities
- **JSON mode** — `response_mime_type='application/json'` forces valid JSON output.
  More reliable than prompt-based JSON extraction.
- **Enum mode** — `response_mime_type='text/x.enum'` with `response_schema` forces
  the model to output exactly one of the specified enum values. Perfect for classification.
- **Code execution** — Gemini can run Python code server-side and return results.
  Useful for math, data analysis, chart generation.
- **Grounded generation** — Add Google Search as a tool for real-time factual grounding.
  Response includes grounding metadata with source URLs.

## Operational Behavior

### Latency characteristics
- gemini-2.5-flash: ~200-500ms TTFT (time to first token), ~50-100 tokens/sec
- gemini-2.5-pro: ~500-2000ms TTFT, ~30-50 tokens/sec
- Thinking adds latency proportional to thinking_budget
- Long context (>100K tokens) adds 1-3 seconds to processing
- Embeddings: ~100-200ms per request

### Failure modes observed in EOS
1. **Spending cap 429** — Most common failure. Looks like rate limit but is billing.
   EOS model_router logs `[ModelRouter] Gemini error:` and falls through to Ollama.
2. **Safety filter false positives** — Business content about "aggressive outreach"
   or "crushing competitors" occasionally triggers HARM_CATEGORY_DANGEROUS_CONTENT.
   `response.text` returns `None`. No configuration to fully disable safety.
3. **Slow responses under load** — When Google's infrastructure is stressed,
   gemini-2.5-flash can spike to 5+ seconds TTFT. model_router has no timeout —
   consider adding one.
4. **Empty responses** — Occasionally returns empty text with finish_reason=STOP.
   Not a safety block — possibly a model artifact. Guard with `response.text or ""`.

### Safety filter configuration
```python
from google.genai import types as genai_types

config = genai_types.GenerateContentConfig(
    safety_settings=[
        genai_types.SafetySetting(
            category='HARM_CATEGORY_HARASSMENT',
            threshold='BLOCK_ONLY_HIGH',
        ),
        genai_types.SafetySetting(
            category='HARM_CATEGORY_DANGEROUS_CONTENT',
            threshold='BLOCK_ONLY_HIGH',
        ),
    ],
)
```
Categories: HARM_CATEGORY_HARASSMENT, HARM_CATEGORY_HATE_SPEECH,
HARM_CATEGORY_SEXUALLY_EXPLICIT, HARM_CATEGORY_DANGEROUS_CONTENT.
Thresholds: BLOCK_NONE (Vertex only), BLOCK_ONLY_HIGH, BLOCK_MEDIUM_AND_ABOVE,
BLOCK_LOW_AND_ABOVE.

## Ecosystem Position

### Where Gemini fits in the LLM landscape
- **vs Claude (Anthropic)**: Gemini wins on multimodal native support, long context (1M vs 200K),
  and pricing. Claude wins on reasoning quality, instruction following, and code generation.
  EOS uses Claude (via CC SDK) for strategic/CEO tasks and Gemini for volume/multimodal.
- **vs GPT-4o (OpenAI)**: Gemini wins on context window, pricing, and native video/audio.
  GPT-4o wins on ecosystem (ChatGPT, plugins, DALL-E). Similar reasoning quality.
- **vs Llama (Meta)**: Gemini is cloud-only API. Llama is open-weight for self-hosting.
  Different use cases. EOS uses Ollama (Qwen, not Llama) as local fallback.

### Google AI ecosystem
- **Google AI Studio** — Web IDE for prototyping prompts, managing API keys, billing
- **Vertex AI** — Enterprise GCP platform with Gemini + other models
- **Firebase Genkit** — App development framework with Gemini integration
- **MLKit** — On-device ML (separate from Gemini API)
- **Gemma** — Open-weight models from Google (2B, 7B, 27B) — not Gemini API

### Composition with other tools
- Gemini + Google Search grounding = real-time factual generation
- Gemini + function calling = structured tool use (CRM lookups, API calls)
- Gemini + context caching = cost-efficient repeated analysis
- Gemini + file upload = large media processing pipeline
- In EOS: Gemini sits in the model_router fallback chain between CC_SDK and Ollama

## Trajectory

### Where Gemini is heading
1. **Model quality convergence** — 2.5 Flash is rapidly approaching Pro quality at
   1/10th the price. Expect Flash to be "good enough" for all but the most complex
   reasoning tasks within 1-2 model generations.

2. **Thinking as standard** — Thinking/reasoning capabilities (like 2.5's thinking_budget)
   will likely become standard across all models, with cost proportional to think time.

3. **Multimodal output** — Currently Gemini only outputs text (+ function calls).
   Image and audio generation output is coming (Imagen integration, native TTS).

4. **Agent frameworks** — Google is building agent infrastructure (Genkit, Vertex AI
   Agent Builder). Gemini will increasingly be positioned as the brain for agentic
   workflows, not just single-turn generation.

5. **Context window expansion** — 2M tokens on 1.5 Pro was a preview. Expect 2M+
   to become standard on 2.5+ models.

6. **Price compression** — Flash pricing has dropped ~10x in 18 months. Expect
   continued aggressive pricing to capture developer market share from OpenAI.

### What to watch for EOS
- When spending cap is raised, Gemini becomes the default workhorse for all non-CEO tasks
- Context caching could significantly reduce cost for repeated document analysis
- Grounded generation via Google Search could power world_pulse without Perplexity
- JSON/enum mode could simplify gateway.py classification (no prompt engineering needed)

## Conceptual Model

### How to think about Gemini in EOS

```
Request Flow:
  Agent needs LLM call
    -> model_router.call_with_fallback()
      -> CC_SDK (Opus) — if available, best quality
      -> Anthropic (Haiku/Sonnet) — if credits available
      -> GEMINI (2.5 Flash) — primary fallback, good quality, cheap
      -> Ollama (qwen2.5:0.5b) — last resort, low quality

Gemini's role in the chain:
  - Catches everything when Anthropic is down (current state)
  - Quality score 0.65 = above escalation threshold
  - Handles: text gen, classification, analysis, multimodal
  - Does NOT handle: web search (Perplexity), local inference (Ollama)
```

### Mental model for token economics
```
Input cost = (text tokens + image tokens + audio tokens + video tokens) * input_price
Output cost = (response tokens + thinking tokens) * output_price
Total cost = input cost + output cost - caching discount

For EOS typical call (1000 input, 500 output, 2.5 Flash):
  Input:  1000 * $0.00000015 = $0.00015
  Output: 500  * $0.0000006  = $0.0003
  Total:  $0.00045 per call
  Budget: ~2,200 calls per $1
```

### Solution recipes

**Recipe 1: Cheap classification**
```python
config = genai_types.GenerateContentConfig(
    max_output_tokens=10,
    temperature=0,
    response_mime_type='text/x.enum',
    response_schema={'enum': ['sales', 'support', 'spam', 'other']},
)
```

**Recipe 2: JSON extraction**
```python
config = genai_types.GenerateContentConfig(
    max_output_tokens=500,
    temperature=0,
    response_mime_type='application/json',
    response_schema={
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'intent': {'type': 'string'},
            'urgency': {'type': 'number'},
        },
    },
)
```

**Recipe 3: Grounded real-time answer**
```python
config = genai_types.GenerateContentConfig(
    tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
)
```

## Industry Expert

### What top practitioners know about Gemini

1. **Flash is underpriced** — At $0.15/1M input tokens, 2.5 Flash is the cheapest
   frontier-class model available. It outperforms GPT-4o-mini on most benchmarks
   while being similarly priced. Use it as default, escalate to Pro or Claude only
   when Flash demonstrably fails.

2. **Thinking budget is the quality knob** — Instead of choosing between models,
   use `thinking_budget` on 2.5 Flash to dial quality up/down per request.
   Budget=0 for classification, budget=2048 for complex analysis. Cheaper than
   switching to Pro.

3. **JSON mode eliminates parsing** — `response_mime_type='application/json'` with
   `response_schema` guarantees valid JSON conforming to your schema. No regex
   extraction, no retry loops, no "please output valid JSON" prompt engineering.

4. **Context caching is underused** — If you send the same system prompt or document
   in >3 requests, caching saves 75% on input tokens. Most developers skip this
   because the API is slightly more complex. For EOS cognitive_loop (which sends
   the same soul docs repeatedly), this could be significant savings.

5. **Grounding replaces web search APIs** — Google Search grounding returns structured
   results with citations. For market intel and fact-checking, this is cheaper and
   more integrated than calling a separate search API (Perplexity, SerpAPI).

6. **Safety filters are the main production headache** — Unlike Claude (which rarely
   refuses business content), Gemini's safety filters can trigger on aggressive
   marketing language, competitive analysis, or anything mentioning weapons/violence
   even in business metaphor context. Lower thresholds to BLOCK_ONLY_HIGH in production.

7. **Streaming is faster perceived latency** — Even when total generation time is the same,
   streaming (`generate_content_stream`) gives users first tokens in ~200ms vs ~2-5s
   for complete response. Use streaming for any user-facing output.

8. **The free tier is viable for development** — 10 RPM on 2.5 Flash with 500 RPD is
   enough for development and testing. Only enable billing when going to production.

---

## EOS Usage Patterns

### Current production pattern (model_router.py)
```python
from google import genai
from google.genai import types as genai_types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
cfg = genai_types.GenerateContentConfig(
    max_output_tokens=max_tokens,
    system_instruction=system or None,
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config=cfg,
)
return response.text or ""
```

### Embedding pattern (embedding_engine.py)
```python
import google.genai as genai
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
result = client.models.embed_content(
    model='models/gemini-embedding-001',
    contents=text,
)
return result.embeddings[0].values  # 768-dim
```

### Multimodal pattern (media_processor.py)
```python
from google import genai
from google.genai import types as genai_types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
# For images: inline bytes
# For large video/audio: client.files.upload() first
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[media_part, analysis_prompt],
    config=genai_types.GenerateContentConfig(max_output_tokens=2000),
)
```

## Gotchas

### Confirmed in EOS production
1. Spending cap 429 looks like rate limit but is billing — check error body
2. `google.generativeai` (old SDK) still imported as fallback in media_processor.py — migrate fully
3. Gemini quality score 0.65 is exactly at escalation threshold — borderline responses may flip
4. No timeout on Gemini calls in model_router — can block indefinitely under load
5. File uploads auto-delete after 48 hours — do not rely on persistent storage
6. Safety filters trigger on aggressive business language — lower to BLOCK_ONLY_HIGH
7. Empty string system_instruction causes 400 error — pass None instead (EOS handles this)
8. `gemini-2.0-flash` returns 404 on new API keys — always use 2.5
9. Thinking tokens billed as output even when not shown — monitor cost on 2.5 models
10. Old SDK fallback in media_processor.py uses different API patterns — test both paths
