# Groq API — Best Practices

## When to use
- STT (speech-to-text) via Whisper — primary use in EOS
- Fast LLM inference via Llama/Mixtral — secondary

## STT best practices

```python
from groq import Groq
import os

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def transcribe(audio_path: str) -> str:
    try:
        with open(audio_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model='whisper-large-v3-turbo',
                file=f,
                language='en',
            )
        return result.text.strip()
    except Exception as e:
        print(f'[Groq STT] Error: {e}')
        return ''
```

## Audio requirements
- Format: WAV, MP3, M4A, MP4, FLAC, OGG
- Max size: 25MB per request
- Sample rate: 16kHz recommended for best accuracy
- Channels: Mono preferred (Discord delivers stereo 48kHz — acceptable)
- EOS records WAV: 2ch, 16-bit, 48kHz — works fine with Groq

## Model selection
- `whisper-large-v3-turbo` — fastest + accurate (use this)
- `whisper-large-v3` — most accurate, slower
- `distil-whisper-large-v3-en` — English-only, fastest

## LLM via Groq (fast inference)
```python
response = client.chat.completions.create(
    model='llama3-8b-8192',
    messages=[{'role': 'user', 'content': prompt}],
    max_tokens=500,
)
text = response.choices[0].message.content.strip()
```

## Free tier limits
- Generous free tier — check console.groq.com/usage
- Rate limits: varies by model, typically 30 req/min
- `GROQ_API_KEY` in `eos_ai/.env`

## EOS usage pattern
`transcribe_with_groq()` in `discord_bot.py` — called by `SilenceDetectingSink` after silence detection fires.

## Common mistakes
- Sending empty audio files (check file size > 0 before sending)
- Not stripping whitespace from result
- Timeout too low — use default (Groq is fast, < 5s typical)
- Using wrong model name (check Groq docs for current model IDs)
- Not handling `GroqRateLimitError` — add try/except
