---
name: whisper
description: "Use when transcribing audio to text, processing voice messages, building STT pipelines, or debugging speech recognition accuracy issues."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/openai/whisper"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "whisper-large-v3-turbo (Groq), large-v3 (local)"
sdk_version: "faster-whisper 1.2.1, openai-whisper 20250625, groq 1.1.1"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Whisper (Speech-to-Text)

## What This Tool Does

Whisper is OpenAI's general-purpose speech recognition model trained on 680,000 hours
of multilingual audio. It performs multilingual speech recognition, speech translation,
and language identification. EOS uses Whisper through three execution paths:

- **Groq Whisper API** (cloud, primary for Discord voice) -- whisper-large-v3-turbo via
  Groq's LPU inference. Sub-second latency for real-time voice conversations. Used by
  `SilenceDetectingSink` in discord_bot.py.
- **faster-whisper** (local, primary for Telegram/media) -- CTranslate2 re-implementation.
  4x faster than OpenAI Whisper with same accuracy. Used by `media_processor.py` and
  `voice_engine.py` IntelligentVoiceProcessor.
- **openai-whisper** (local, fallback) -- Original PyTorch implementation. Heavier but
  used as fallback when faster-whisper is unavailable. Used by `voice_engine.py` VoiceEngine
  and `apify_scraper.py` for video transcript extraction.

Model sizes available (local):
| Model  | Parameters | VRAM   | Relative Speed | English WER |
|--------|-----------|--------|----------------|-------------|
| tiny   | 39M       | ~1 GB  | ~10x           | ~7.6%       |
| base   | 74M       | ~1 GB  | ~7x            | ~5.0%       |
| small  | 244M      | ~2 GB  | ~4x            | ~3.4%       |
| medium | 769M      | ~5 GB  | ~2x            | ~2.9%       |
| large-v3 | 1.55B   | ~10 GB | 1x             | ~2.0%       |

## EOS Integration

### Discord voice (Groq cloud path)
`services/discord_bot.py` -- `transcribe_with_groq()` function.
`SilenceDetectingSink` accumulates per-user audio frames, flushes after 1.5s silence,
writes stereo 48kHz WAV, sends to Groq whisper-large-v3-turbo. Result routes through
EOS gateway for response generation.

```python
# discord_bot.py line 217
def transcribe_with_groq(audio_path: str) -> str:
    client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f,
            language="en",
        )
    return result.text.strip()
```

### Telegram/media (faster-whisper local path)
`eos_ai/media_processor.py` -- `_local_transcribe()` method.
Always uses local Whisper for voice/audio media, even when Gemini is available.
Falls back to openai-whisper if faster-whisper import fails.

```python
# media_processor.py line 241
def _local_transcribe(self, audio_path: str) -> str:
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device='cpu', compute_type='int8')
    segments, _ = model.transcribe(audio_path)
    return ' '.join(s.text for s in segments).strip()
```

### Voice engine (dual path)
`eos_ai/voice_engine.py` -- Two classes use Whisper:
- `IntelligentVoiceProcessor.transcribe_fast()` -- faster-whisper with VAD filter,
  falls back to VoiceEngine.transcribe()
- `VoiceEngine.transcribe()` -- openai-whisper, lazy-loads on first call
- `VoiceEngine.transcribe_with_vad()` -- webrtcvad segments + openai-whisper per segment

### Video transcript extraction
`services/apify_scraper.py` -- `transcribe_video()` function.
Downloads audio via yt-dlp, transcribes with openai-whisper small model for
ICP relevance filtering on Instagram video content.

### Harness registry
Registered as `groq_whisper` in `eos_ai/harness_registry.py`. Status: active.
Provides: `speech_to_text`. Config key: `GROQ_API_KEY`.

## Authentication

### Groq API (cloud path)
1. Get API key from https://console.groq.com
2. Store as `GROQ_API_KEY` in both `services/.env` and `eos_ai/.env`
3. SDK: `from groq import Groq; client = Groq(api_key=os.getenv("GROQ_API_KEY"))`
4. No OAuth, no refresh tokens -- simple API key auth

### Local paths (faster-whisper / openai-whisper)
No authentication required. Models download from Hugging Face Hub on first use.
Model cache: `~/.cache/huggingface/hub/` (faster-whisper) or `~/.cache/whisper/` (openai-whisper).
First load requires internet access; subsequent loads are offline.

## Quick Reference

### Transcribe with Groq (cloud, fastest)
```python
from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
with open("audio.wav", "rb") as f:
    result = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=f,
        language="en",           # optional, improves accuracy
        response_format="text",  # or "json", "verbose_json"
    )
text = result.text
```

### Transcribe with faster-whisper (local, recommended)
```python
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    "audio.wav",
    beam_size=5,          # accuracy vs speed (1=fastest, 5=default)
    language="en",        # skip language detection
    vad_filter=True,      # silence removal
    vad_parameters=dict(min_silence_duration_ms=500),
)
text = " ".join(seg.text for seg in segments).strip()
```

### Transcribe with openai-whisper (local, fallback)
```python
import whisper
model = whisper.load_model("small")
result = model.transcribe("audio.wav")
text = result["text"].strip()
```

### Convert OGG voice to WAV (Telegram voice messages)
```python
import subprocess
subprocess.run([
    "ffmpeg", "-i", "voice.ogg",
    "-ar", "16000",    # 16kHz sample rate
    "-ac", "1",        # mono
    "-f", "wav",
    "voice.wav",
], capture_output=True)
```

### Convert Discord stereo 48kHz to Whisper-optimal format
```python
import subprocess
subprocess.run([
    "ffmpeg", "-i", "discord.wav",
    "-ar", "16000", "-ac", "1", "-f", "wav",
    "mono16k.wav",
], capture_output=True)
```

## Conceptual Model

```
Audio Input
  |
  +-- Cloud Path (Discord voice, real-time)
  |     |
  |     +-- SilenceDetectingSink (48kHz stereo WAV)
  |     +-- Groq API (whisper-large-v3-turbo)
  |     +-- < 1 second latency
  |     +-- Best accuracy (large-v3 turbo)
  |
  +-- Local Path (Telegram, media, batch)
  |     |
  |     +-- faster-whisper (CTranslate2, int8 quantized)
  |     |     +-- Built-in Silero VAD filter
  |     |     +-- 4x faster than original
  |     |     +-- Model: small (default in EOS)
  |     |
  |     +-- openai-whisper (PyTorch, fallback)
  |           +-- Model: base (voice_engine) or small (media_processor, apify)
  |           +-- Requires torch (~2 GB RAM)
  |
  +-- Pre-processing (when needed)
        |
        +-- ffmpeg: format conversion (OGG/MP3 -> WAV)
        +-- Resample to 16kHz mono (Whisper native rate)
        +-- VAD: Silero (neural) or webrtcvad (rule-based)
```

See references/best_practices.md for rate limits, model benchmarks, and anti-patterns.

## Gotchas

### Groq sends raw WAV -- no pre-conversion needed
Discord records at 48kHz stereo. Groq's API accepts this directly -- do NOT
pre-convert to 16kHz mono before sending to Groq. The API handles resampling.
Only convert for local Whisper where 16kHz mono is optimal.

### faster-whisper segments are a generator
`model.transcribe()` returns `(generator, info)`. The segments generator is lazy --
it only processes audio as you iterate. Calling `list(segments)` forces full processing.
If you only need text, iterate once: `" ".join(s.text for s in segments)`.
Do NOT iterate twice -- the generator is exhausted after first pass.

### openai-whisper loads model into RAM on every call if not cached
`whisper.load_model("small")` downloads and loads ~500 MB into RAM each time.
In EOS, `VoiceEngine` caches this in `self._whisper_model`. The `apify_scraper.py`
does NOT cache -- it reloads per video. For batch use, always cache the model object.

### Audio files over 25 MB fail on Groq
Groq's Whisper API has a 25 MB file size limit. Discord voice utterances are small
(1-10 seconds), so this rarely hits. For longer recordings, split with ffmpeg first
or use local Whisper.

### Hallucinated text on silence or noise
Whisper hallucinates text (often repeated phrases or random sentences) when given
silence, white noise, or very low speech confidence audio. The VAD filter in
faster-whisper (`vad_filter=True`) mitigates this. For openai-whisper, use
webrtcvad pre-filtering (VoiceEngine.transcribe_with_vad). EOS also gates on
`len(text.split()) < 2` in the Discord voice loop to discard hallucinated fragments.

### Model download blocks first transcription
First call to any Whisper variant downloads the model from Hugging Face.
faster-whisper small: ~500 MB. openai-whisper small: ~500 MB (plus torch ~2 GB).
In Docker containers, this happens on first voice message after restart unless
the model cache volume is persisted.

### int8 compute_type requires CPU or CUDA
faster-whisper with `compute_type='int8'` works on CPU. On GPU, use `'float16'`
or `'int8_float16'`. Using `'int8'` on GPU silently falls back to float32,
wasting VRAM. EOS runs CPU-only (`device='cpu'`).
