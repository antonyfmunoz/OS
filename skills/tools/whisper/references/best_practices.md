# Whisper -- Creator-Level Best Practices
Source: https://github.com/openai/whisper, https://github.com/SYSTRAN/faster-whisper, https://console.groq.com/docs/speech-text
API Version: whisper-large-v3-turbo (Groq), large-v3 (OpenAI)
SDK Version: faster-whisper 1.2.1, openai-whisper 20250625, groq 1.1.1
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## Authentication

Whisper operates across three execution contexts with different auth requirements:

**Groq Whisper API (cloud)**
- Auth method: API key in `Authorization: Bearer <key>` header
- SDK handles this: `Groq(api_key=os.getenv("GROQ_API_KEY"))`
- Key obtained from https://console.groq.com/keys
- No OAuth, no refresh tokens, no scopes -- single key grants full access
- Keys do not expire but can be revoked from the console
- EOS env vars: `GROQ_API_KEY` in `services/.env` AND `eos_ai/.env`
- Free tier available with rate limits; paid tier for production volume

**OpenAI Whisper API (cloud, not currently used in EOS)**
- Auth method: API key via `Authorization: Bearer <key>` header
- Key from https://platform.openai.com/api-keys
- EOS does not use this path -- Groq is faster and cheaper for the same model

**Local Whisper (faster-whisper / openai-whisper)**
- No authentication required
- Models auto-download from Hugging Face Hub on first load
- Hugging Face token optional (only needed for gated models, Whisper is not gated)
- Cache locations:
  - faster-whisper: `~/.cache/huggingface/hub/`
  - openai-whisper: `~/.cache/whisper/`

## Core Operations with Exact Signatures

### Groq SDK (groq 1.1.1)
```python
from groq import Groq

client = Groq(api_key: str = None)  # defaults to GROQ_API_KEY env var

# Transcription
result = client.audio.transcriptions.create(
    model: str,              # required: "whisper-large-v3-turbo" or "whisper-large-v3"
    file: BinaryIO,          # required: file-like object (open in "rb" mode)
    language: str = None,    # optional: ISO-639-1 code ("en", "es", "fr", etc.)
    prompt: str = None,      # optional: context hint for style/spelling
    response_format: str = "json",  # "json" | "text" | "verbose_json" | "srt" | "vtt"
    temperature: float = 0,  # optional: 0.0-1.0, higher = more random
    timestamp_granularities: list = None,  # ["word", "segment"] (verbose_json only)
)
# Returns: Transcription object
#   .text: str              -- the transcribed text
#   .segments: list | None  -- when verbose_json, list of {id, start, end, text}
#   .words: list | None     -- when verbose_json + word timestamps

# Translation (to English)
result = client.audio.translations.create(
    model: str,              # required: "whisper-large-v3"
    file: BinaryIO,          # required
    prompt: str = None,
    response_format: str = "json",
    temperature: float = 0,
)
# Returns: same shape as transcriptions
```

### faster-whisper (1.2.1)
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size_or_path: str,     # "tiny"|"base"|"small"|"medium"|"large-v3" or path
    device: str = "auto",        # "cpu"|"cuda"|"auto"
    device_index: int | list = 0,
    compute_type: str = "default",  # "int8"|"float16"|"int8_float16"|"float32"
    cpu_threads: int = 0,        # 0 = auto-detect
    num_workers: int = 1,        # parallel transcriptions
    download_root: str = None,   # custom model cache directory
)

segments, info = model.transcribe(
    input: str | BinaryIO | ndarray,  # file path, file object, or numpy array
    language: str = None,        # ISO-639-1 or None for auto-detect
    task: str = "transcribe",    # "transcribe" | "translate"
    beam_size: int = 5,          # 1 = greedy (fastest), 5 = beam search (default)
    best_of: int = 5,            # candidates when temperature > 0
    patience: float = 1.0,       # beam search patience factor
    length_penalty: float = 1.0, # exponential length penalty
    temperature: float | list = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    compression_ratio_threshold: float = 2.4,
    log_prob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    condition_on_previous_text: bool = True,
    initial_prompt: str = None,  # context hint for spelling/style
    prefix: str = None,          # force start of transcript
    word_timestamps: bool = False,
    vad_filter: bool = False,    # Silero VAD pre-filtering
    vad_parameters: dict = None, # {min_silence_duration_ms, speech_pad_ms, ...}
    without_timestamps: bool = False,
)
# Returns: (generator[Segment], TranscriptionInfo)
#   Segment: .id, .start, .end, .text, .tokens, .avg_logprob,
#            .compression_ratio, .no_speech_prob, .words (if word_timestamps)
#   TranscriptionInfo: .language, .language_probability, .duration,
#                      .all_language_probs, .transcription_options, .vad_options
```

### openai-whisper (20250625)
```python
import whisper

model = whisper.load_model(
    name: str,                  # "tiny"|"base"|"small"|"medium"|"large"|"large-v3"
    device: str = None,         # "cpu"|"cuda" or None for auto
    download_root: str = None,  # custom cache dir
    in_memory: bool = False,    # load entire model to memory
)

result = model.transcribe(
    audio: str | ndarray,       # file path or 16kHz float32 numpy array
    verbose: bool = None,       # print progress
    temperature: float | tuple = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    compression_ratio_threshold: float = 2.4,
    logprob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    condition_on_previous_text: bool = True,
    initial_prompt: str = None,
    word_timestamps: bool = False,
    fp16: bool = True,          # use float16 (GPU only, ignored on CPU)
    language: str = None,       # ISO-639-1 or None for auto-detect
    task: str = "transcribe",   # "transcribe" | "translate"
)
# Returns: dict
#   {"text": str, "segments": list[dict], "language": str}
#   Each segment: {id, seek, start, end, text, tokens, temperature,
#                  avg_logprob, compression_ratio, no_speech_prob}
```

## Pagination Patterns

Not applicable -- Whisper processes single audio files and returns complete results.
For long audio files, Whisper internally segments by 30-second windows with
sliding context. No cursor-based pagination exists.

For batch processing of multiple files, implement your own loop:
```python
from pathlib import Path
results = {}
for audio_file in Path("recordings/").glob("*.wav"):
    segments, info = model.transcribe(str(audio_file))
    results[audio_file.name] = " ".join(s.text for s in segments)
```

## Rate Limits

### Groq Whisper API
- Free tier: 7,200 requests/day (~5 req/min sustained)
- Audio seconds limit: 28,800 audio-seconds/day (8 hours of audio)
- Max file size: 25 MB per request
- Max audio duration: ~2 hours per file (practical limit)
- Rate limit headers in response:
  - `x-ratelimit-limit-requests`
  - `x-ratelimit-remaining-requests`
  - `x-ratelimit-reset-requests`
  - `retry-after` (on 429)
- 429 response on rate limit -- retry with exponential backoff
- Paid tier: significantly higher limits (varies by plan)

### Local Whisper (faster-whisper / openai-whisper)
- No API rate limits -- constrained by hardware
- CPU transcription speed (small model, int8):
  - ~2-4x real-time on modern CPU (10s audio = 2.5-5s processing)
  - faster-whisper is ~4x faster than openai-whisper
- Memory constraints:
  - tiny: ~400 MB RAM
  - base: ~500 MB RAM
  - small: ~1 GB RAM
  - medium: ~2.5 GB RAM
  - large-v3: ~6 GB RAM (CPU), ~4 GB VRAM (GPU)
- EOS VPS has limited RAM -- small model is the ceiling for production use

## Error Codes and Recovery

### Groq API errors
| Status | Meaning | Recovery |
|--------|---------|----------|
| 400 | Invalid request (bad file format, too large) | Check file size < 25MB, valid audio format |
| 401 | Invalid API key | Verify GROQ_API_KEY in env |
| 413 | File too large | Split audio with ffmpeg |
| 429 | Rate limited | Retry with exponential backoff, check retry-after header |
| 500 | Groq server error | Retry once, then fall back to local Whisper |

### faster-whisper errors
| Error | Cause | Recovery |
|-------|-------|----------|
| `RuntimeError: CTranslate2 ... not found` | Model not downloaded | Ensure internet on first run, check cache dir |
| `ValueError: audio must be ...` | Wrong input format | Provide file path string, not bytes |
| `OSError: [Errno 28] No space left` | Model cache disk full | Clear `~/.cache/huggingface/hub/` |
| Empty segments (generator yields nothing) | Silent audio, corrupt file | Check file with ffprobe, use VAD pre-filter |

### openai-whisper errors
| Error | Cause | Recovery |
|-------|-------|----------|
| `RuntimeError: CUDA out of memory` | Model too large for GPU | Use `device='cpu'` or smaller model |
| `torch.cuda.OutOfMemoryError` | Same as above | Same as above |
| `FileNotFoundError` | Audio file missing or wrong path | Verify path exists before calling |
| Hallucinated output | Silence/noise input | Pre-filter with VAD, check result length |

### Retryable vs non-retryable
- Retryable: 429 (rate limit), 500 (server error), connection timeouts
- Non-retryable: 400 (bad request), 401 (auth), 413 (file too large)

## SDK Idioms

### Groq SDK (groq 1.1.1)
```python
# Correct: use context manager for file
from groq import Groq
client = Groq()  # auto-reads GROQ_API_KEY env var

with open(audio_path, "rb") as f:
    result = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=f,
    )
# Access: result.text (string property, not dict key)
```

### faster-whisper idioms
```python
from faster_whisper import WhisperModel

# Correct: create model ONCE, reuse for multiple transcriptions
model = WhisperModel("small", device="cpu", compute_type="int8")

# Correct: consume generator in one pass
segments, info = model.transcribe(audio_path, vad_filter=True)
text = " ".join(segment.text for segment in segments).strip()

# Correct: use vad_parameters for tuning
segments, info = model.transcribe(
    audio_path,
    vad_filter=True,
    vad_parameters=dict(
        min_silence_duration_ms=500,  # silence length to split on
        speech_pad_ms=200,            # padding around speech segments
        threshold=0.5,                # VAD confidence threshold
    ),
)
```

### openai-whisper idioms
```python
import whisper

# Correct: cache model, don't reload per file
model = whisper.load_model("small")

# Correct: pass file path, not bytes
result = model.transcribe("audio.wav")
text = result["text"]  # dict access, not attribute

# Correct: for non-English audio
result = model.transcribe("audio.wav", language="es", task="translate")
# task="translate" converts to English regardless of source language
```

## Anti-Patterns

### 1. Reloading model per transcription
```python
# WRONG: loads ~500 MB into RAM on every call
def transcribe(path):
    import whisper
    model = whisper.load_model("small")
    return model.transcribe(path)["text"]

# CORRECT: load once, reuse
_model = None
def transcribe(path):
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model("small")
    return _model.transcribe(path)["text"]
```

### 2. Iterating faster-whisper segments twice
```python
# WRONG: generator exhausted after first iteration
segments, info = model.transcribe(path)
all_text = " ".join(s.text for s in segments)
timestamps = [(s.start, s.end) for s in segments]  # EMPTY -- generator spent

# CORRECT: collect once
segments, info = model.transcribe(path)
segment_list = list(segments)
all_text = " ".join(s.text for s in segment_list)
timestamps = [(s.start, s.end) for s in segment_list]
```

### 3. Sending raw PCM bytes to Whisper
```python
# WRONG: Whisper expects a file path or proper numpy array
result = model.transcribe(audio_bytes)  # TypeError

# CORRECT: save to temp file first
import tempfile
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    f.write(audio_bytes)
    f.flush()
    result = model.transcribe(f.name)
```

### 4. Not using VAD filter on noisy audio
```python
# WRONG: transcribes silence/noise, gets hallucinations
segments, _ = model.transcribe("noisy_audio.wav")

# CORRECT: enable VAD to skip non-speech segments
segments, _ = model.transcribe("noisy_audio.wav", vad_filter=True)
```

### 5. Using beam_size=5 for real-time voice
```python
# WRONG: beam search is slow for real-time
segments, _ = model.transcribe(path, beam_size=5)

# CORRECT: greedy decoding for real-time, beam for batch
segments, _ = model.transcribe(path, beam_size=1)  # 2-3x faster
```

### 6. Ignoring language parameter when language is known
```python
# WRONG: wastes time on language detection
result = model.transcribe("english_audio.wav")

# CORRECT: skip detection when you know the language
result = model.transcribe("english_audio.wav", language="en")
```

## Data Model

### Whisper's internal representation
```
Audio (any format ffmpeg supports)
  → Resampled to 16kHz mono
  → Log-mel spectrogram (80 frequency bins)
  → 30-second windows with 0.5s overlap
  → Encoder (transformer) → latent representation
  → Decoder (transformer) → token sequence
  → Detokenized text + timestamps
```

### Segment object (faster-whisper)
```python
Segment(
    id: int,                    # sequential segment ID
    seek: int,                  # seek position in audio (frames)
    start: float,               # start time in seconds
    end: float,                 # end time in seconds
    text: str,                  # transcribed text for this segment
    tokens: list[int],          # token IDs
    avg_logprob: float,         # average log probability (-inf to 0)
    compression_ratio: float,   # text compression ratio
    no_speech_prob: float,      # probability of no speech (0-1)
    words: list[Word] | None,   # word-level timestamps if requested
)
```

### TranscriptionInfo (faster-whisper)
```python
TranscriptionInfo(
    language: str,              # detected language code
    language_probability: float,
    duration: float,            # total audio duration in seconds
    duration_after_vad: float,  # duration after VAD filtering
    all_language_probs: list[tuple[str, float]] | None,
    transcription_options: TranscriptionOptions,
    vad_options: VadOptions | None,
)
```

### Quality indicators
- `avg_logprob > -0.5`: high confidence transcription
- `avg_logprob < -1.0`: low confidence, likely errors
- `no_speech_prob > 0.6`: segment is probably silence/noise
- `compression_ratio > 2.4`: likely hallucinated (repetitive text)

## Webhooks and Events

N/A -- Whisper is a synchronous transcription tool. No webhook or event system exists.
For event-driven audio processing in EOS, the event source is the Discord gateway
(voice state updates) or Telegram bot (voice message received), not Whisper itself.

## Limits

### Groq API limits
- Max file size: 25 MB
- Max audio duration: practical limit ~2 hours
- Supported formats: wav, mp3, mp4, m4a, ogg, flac, webm
- Min audio duration: ~0.1 seconds (very short clips produce empty results)

### Local Whisper limits
- Max audio: no hard limit, but RAM-constrained. Processes in 30-second windows.
- Supported formats: anything ffmpeg can decode
- Sample rate: resampled internally to 16kHz. Input can be any rate.
- Channels: converted internally to mono. Input can be stereo.
- faster-whisper model sizes on disk:
  - tiny: ~75 MB, base: ~145 MB, small: ~500 MB
  - medium: ~1.5 GB, large-v3: ~3 GB

### Performance limits (EOS VPS, CPU-only)
- faster-whisper small int8: ~3-4x real-time (10s audio = 2.5-3.3s)
- openai-whisper small: ~1x real-time (10s audio = ~10s)
- openai-whisper base: ~2x real-time
- Concurrent transcriptions: 1 recommended (CPU-bound)

## Cost Model

### Groq Whisper API
- Free tier: 7,200 requests/day, 28,800 audio-seconds/day
- Pricing: $0.00011 per audio second (as of 2025)
- 1 hour of audio: ~$0.40
- 10 minutes of audio: ~$0.066
- EOS usage: Discord voice typically 5-30 seconds per utterance
  - 100 utterances/day at avg 10s = 1,000 audio-seconds = ~$0.11/day
  - Well within free tier for normal use

### Local Whisper
- No API cost -- compute cost only
- VPS compute: already running, marginal cost is zero
- Trade-off: slower than Groq, uses VPS CPU/RAM
- RAM cost: small model needs ~1 GB; must share with other EOS services

### Cost optimization strategy (EOS)
- Real-time Discord voice: Groq (latency matters, free tier sufficient)
- Telegram voice messages: local faster-whisper (latency tolerant, no API cost)
- Batch video transcription: local openai-whisper (cost-free, speed not critical)

## Version Pinning

### Current versions in EOS
- `faster-whisper==1.2.1` in `services/requirements.txt`
- `openai-whisper==20250625` in `services/requirements.txt`
- `groq==1.1.1` installed (pip)
- Groq API model: `whisper-large-v3-turbo` (pinned in discord_bot.py)

### Model versioning
- Whisper large-v3: most accurate, latest stable release from OpenAI
- Whisper large-v3-turbo: Groq-optimized variant, similar accuracy, faster inference
- No API versioning header for Groq -- model string is the version pin
- OpenAI Whisper uses date-based package versions (YYYYMMDD)

### Deprecation notes
- `whisper-large-v2` is superseded by `large-v3` -- do not use
- `distil-whisper` exists as a lighter alternative but is not used in EOS
- faster-whisper tracks CTranslate2 versions -- major CTranslate2 updates may
  require faster-whisper updates

---

# Tier 2 -- Creator Intelligence

## Design Intent and Tradeoffs

Whisper was designed by OpenAI as a "robust" speech recognition system, not a "fast" one.
The core philosophy: train a single model on massive diverse data rather than engineering
features for specific domains. 680,000 hours of multilingual, multi-task supervised data
from the web. This means:

**Tradeoff: Generality over specialization.** Whisper works well on any audio domain
(meetings, podcasts, phone calls, accented speech, noisy environments) but will never
beat a domain-specific model fine-tuned for, say, medical transcription. For EOS this
is the right trade -- founder voice comes from Discord calls, Telegram messages, video
recordings, all different acoustic environments.

**Tradeoff: Accuracy over speed.** The original model prioritizes WER (word error rate)
over latency. This is why faster-whisper exists -- CTranslate2 re-implementation gets
4x speedup through int8 quantization and optimized attention without retraining.

**Tradeoff: English-first with multilingual capability.** Whisper's English performance
is significantly better than other languages. The model allocates disproportionate
capacity to English because the training data is English-heavy. For EOS (English-only
founder), this is a non-issue.

**What Whisper is NOT:** It is not a real-time streaming transcription system. It processes
complete audio chunks. Groq makes it feel real-time through hardware acceleration, but
the model itself is designed for batch processing of audio segments.

## Problem-Solution Map and Hidden Capabilities

### Problem: Accurate transcription across environments
Solution: Use the right model size for the context. Small for known-English real-time,
large-v3 (via Groq) for accuracy-critical transcriptions.

### Problem: Hallucination on silence/noise
Solution: Stack VAD before Whisper. faster-whisper's built-in `vad_filter=True` uses
Silero VAD. For openai-whisper, use webrtcvad pre-filtering (as EOS does in VADProcessor).

### Problem: Speaker is using domain-specific terms
Solution: Use `initial_prompt` parameter to prime the decoder with expected vocabulary:
```python
segments, _ = model.transcribe(path, initial_prompt="Initiate Arena, Lyfe Institute, Munoz Conglomerate, DEX")
```
This dramatically improves recognition of brand names, product names, and jargon.

### Hidden capability: Translation
Whisper can translate from 99 languages to English in a single pass. No separate
translation step needed:
```python
segments, _ = model.transcribe(foreign_audio, task="translate")
```

### Hidden capability: Word-level timestamps
Both faster-whisper and openai-whisper support word-level timing:
```python
segments, _ = model.transcribe(path, word_timestamps=True)
for seg in segments:
    for word in seg.words:
        print(f"{word.start:.2f}-{word.end:.2f}: {word.word}")
```
Useful for subtitle generation, keyword spotting, or syncing transcript to video.

### Hidden capability: Language detection without transcription
```python
# faster-whisper: detect language only
model = WhisperModel("small", device="cpu", compute_type="int8")
language, probability, all_probs = model.detect_language(audio_path)
```

### Hidden capability: Confidence scoring per segment
`avg_logprob` and `no_speech_prob` on each segment enable quality gating.
Reject segments where `no_speech_prob > 0.6` or `avg_logprob < -1.0`.

## Operational Behavior and Edge Cases

### Hallucination patterns
Whisper hallucinates in predictable ways:
- **Repetition:** "Thank you. Thank you. Thank you." on silence
- **Phantom speech:** "Thanks for watching!" or "Subscribe" on noise (YouTube training data bias)
- **Language drift:** switches to another language mid-transcript if confidence drops
- Mitigation: VAD filter, compression_ratio_threshold (default 2.4), segment-level filtering

### 30-second window boundary effects
Whisper processes audio in 30-second windows. If a word spans a window boundary,
it may be split or duplicated. `condition_on_previous_text=True` (default) reduces this
but can also propagate errors from one window to the next.

### Temperature fallback cascade
When Whisper detects low confidence, it automatically retries with higher temperature.
Default cascade: `[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]`. Each retry reprocesses the segment.
This means a single difficult segment can take 6x longer. Set `temperature=0.0` (single
value, not list) when speed matters and you accept lower accuracy on hard segments.

### Concurrent transcription on single CPU
Running multiple transcriptions simultaneously on a single CPU causes contention and
slows all of them. In EOS, the voice pipeline is single-threaded by design --
`run_in_executor` offloads to a thread but faster-whisper's CTranslate2 backend holds
the GIL during compute-heavy operations.

### Audio format edge cases
- MP3 with variable bitrate: works fine, ffmpeg handles internally
- OGG/Opus (Telegram voice): requires ffmpeg conversion to WAV first
- WebM (browser recordings): works with faster-whisper, may need conversion for openai-whisper
- FLAC: works natively, no conversion needed
- Zero-length audio files: returns empty text (no error), check file size before calling

### Discord-specific: stereo 48kHz
Discord records at 48kHz stereo (2 channels). Both Groq API and local Whisper handle
this, but resampling to 16kHz mono before local Whisper saves ~6x processing on the
spectrogram computation. For Groq, send as-is -- the API resamples server-side.

## Ecosystem Position and Composition

### Where Whisper sits in architecture
Whisper is the **input transformation layer** -- it converts audio signals into text
that the rest of the AI pipeline can process. It sits between:
- **Upstream:** Audio capture (Discord sinks, Telegram downloads, file uploads)
- **Downstream:** NLP pipeline (intent classification, EOS gateway, cognitive loop)

### Natural complements in EOS
- **Silero VAD** -- neural voice activity detection. Pre-filters audio before Whisper.
  Used in IntelligentVoiceProcessor for real-time speech detection.
- **webrtcvad** -- rule-based VAD fallback. Used in VADProcessor for segment extraction.
- **ffmpeg** -- audio format conversion. Required for OGG->WAV (Telegram), optional
  for resampling (16kHz mono optimization).
- **Coqui TTS / espeak** -- text-to-speech on the output side. Whisper transcribes
  inbound; TTS synthesizes outbound. Bidirectional voice loop.
- **Groq LPU** -- hardware acceleration for Whisper inference. Turns a batch model
  into a real-time service.

### Integration anti-patterns
- **Whisper + real-time streaming:** Whisper is not a streaming model. Don't try to
  feed it a live audio stream. Buffer into utterances (as SilenceDetectingSink does),
  then transcribe each utterance.
- **Whisper + speaker diarization:** Whisper does not identify who is speaking.
  For multi-speaker scenarios, combine with pyannote-audio or similar diarization tool.
- **Whisper alone for meeting notes:** Whisper transcribes but doesn't summarize.
  EOS correctly chains Whisper -> CognitiveLoop ANALYZE for meeting intelligence.

## Trajectory and Evolution

### Where Whisper is heading
- **Turbo variants:** Groq and others are releasing optimized versions (large-v3-turbo)
  that maintain accuracy with reduced latency. Expect more turbo variants.
- **Distil-Whisper:** Hugging Face distilled versions (distil-large-v3) offer 5.8x
  speedup with minimal accuracy loss. Not yet in EOS but worth monitoring.
- **Whisper large-v3-turbo:** Released late 2024, 809M parameters (vs 1.55B for large-v3).
  Half the size, nearly the same accuracy. Groq serves this as their default.
- **Local GPU inference:** As GPU VPS prices drop, running large-v3 locally with
  faster-whisper on GPU becomes cost-effective vs cloud API.

### Deprecation signals
- `whisper-1` (OpenAI API model name) maps to Whisper v2 -- deprecated in favor of v3
- Original `large` model superseded by `large-v2` then `large-v3`
- `medium.en`, `small.en` (English-only) models are maintained but the multilingual
  versions are now competitive on English, making .en variants less necessary

### What to watch
- OpenAI may release Whisper v4 with improved multilingual and code-switching
- Groq expanding model support -- may add distil-whisper or custom fine-tuned models
- faster-whisper CTranslate2 backend may be replaced by more efficient runtimes

## Conceptual Model and Solution Recipes

### Mental model: Whisper as a translation layer
Think of Whisper as a universal audio-to-text adapter. The key primitives:
- **Transcribe:** audio in source language -> text in source language
- **Translate:** audio in any language -> text in English
- **Detect:** audio -> language identification
- **Segment:** audio -> timestamped text chunks

### Recipe 1: Real-time voice assistant (EOS Discord)
```
1. User speaks in Discord voice channel
2. SilenceDetectingSink buffers audio, detects 1.5s silence
3. Flush buffer to WAV file (48kHz stereo)
4. Send WAV to Groq whisper-large-v3-turbo
5. Receive text in < 1 second
6. Gate: len(words) >= 2 (discard hallucinations)
7. Classify speech type (command/question/thinking_aloud)
8. Route through EOS gateway if actionable
9. Speak response via TTS
```

### Recipe 2: Telegram voice message processing (EOS)
```
1. User sends voice message in Telegram
2. Download OGG/Opus file
3. Convert: ffmpeg -i voice.ogg -ar 16000 -ac 1 -f wav voice.wav
4. Transcribe locally: faster-whisper small, int8, vad_filter=True
5. If user wants analysis (not just transcript):
   - Chain transcript to CognitiveLoop for AI response
6. Return transcript + optional AI analysis
```

### Recipe 3: Content relevance filtering (apify_scraper)
```
1. Scraper finds Instagram video post
2. Download audio: yt-dlp --extract-audio --audio-format mp3
3. Transcribe: openai-whisper small model
4. Check transcript length > 20 chars (discard failures)
5. Send transcript + caption to Claude for ICP relevance scoring
6. Filter: only engage with relevant content
```

### Recipe 4: Meeting intelligence
```
1. Start meeting mode (Telegram or Discord)
2. For each voice segment:
   a. Transcribe with faster-whisper (local, no API cost for long meetings)
   b. Append to session transcript with timestamp
3. On meeting end:
   a. Concatenate full transcript
   b. Send to CognitiveLoop ANALYZE
   c. Extract: summary, action items, decisions, follow-ups
```

### Recipe 5: Batch audio processing with quality gating
```python
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")

results = []
for audio_file in audio_files:
    segments, info = model.transcribe(
        audio_file,
        vad_filter=True,
        language="en",
        beam_size=5,
    )
    high_quality = []
    for seg in segments:
        if seg.no_speech_prob < 0.6 and seg.avg_logprob > -1.0:
            high_quality.append(seg.text)
    results.append(" ".join(high_quality))
```

## Industry Expert and Cutting-Edge Usage

### Groq LPU: turning batch into real-time
Groq's Language Processing Units achieve sub-second Whisper inference on large-v3,
making it viable for real-time voice assistants. This is a hardware innovation, not
a model innovation -- the same Whisper model runs on specialized silicon. EOS exploits
this for Discord voice where latency < 1s is critical for natural conversation.

### VAD + Whisper pipeline (industry standard)
The pattern EOS uses (Silero VAD -> Whisper) is now industry standard for production
voice systems. Key insight: Whisper should never process silence. VAD eliminates
hallucination at the source. faster-whisper baking Silero VAD directly into the
`vad_filter` parameter reflects this becoming the default pattern.

### initial_prompt for domain adaptation
Production systems use `initial_prompt` to inject domain vocabulary without fine-tuning.
For a business OS like EOS, priming with brand names and business terms significantly
improves accuracy on founder-specific vocabulary:
```python
EOS_PROMPT = "Initiate Arena, Lyfe Institute, Munoz Conglomerate, DEX, Empyrean Studio"
segments, _ = model.transcribe(path, initial_prompt=EOS_PROMPT)
```

### Whisper + diarization for multi-speaker meetings
Cutting-edge systems combine Whisper with pyannote-audio for speaker-attributed
transcripts. This enables "Speaker 1 said X, Speaker 2 said Y" in meeting notes.
EOS does not currently implement this but it's the natural next step for meeting
intelligence. The pipeline: pyannote segments by speaker -> Whisper transcribes
each segment -> merge with speaker labels.

### Speculative decoding
Emerging pattern: use a tiny/base model for initial fast pass, then verify uncertain
segments with large model. Reduces average latency while maintaining accuracy.
Not yet implemented in faster-whisper but available in some research codebases.

### Whisper for content intelligence
Beyond transcription, Whisper enables:
- **Audio SEO:** Transcribe all video content, make it searchable
- **Content compliance:** Scan audio for specific phrases or topics
- **Engagement analysis:** Combine with sentiment analysis on transcript
- **Multilingual reach:** Translate content to English for analysis, regardless of source

---

## EOS Usage Patterns

### Three-tier transcription strategy
1. **Groq cloud** (discord_bot.py): Real-time Discord voice. whisper-large-v3-turbo.
   Priority: latency. Cost: free tier sufficient.
2. **faster-whisper local** (media_processor.py, voice_engine.py): Telegram voice,
   media uploads. Small model, int8. Priority: zero API cost. Latency: acceptable.
3. **openai-whisper local** (voice_engine.py fallback, apify_scraper.py): When
   faster-whisper unavailable or for batch video processing. Small model.
   Priority: compatibility. Latency: slowest.

### Model size selection in EOS
- `small` is the standard across all local paths (media_processor, apify_scraper)
- `base` is the default in voice_engine.py (lighter for real-time voice)
- `whisper-large-v3-turbo` via Groq for maximum accuracy with cloud latency

### Audio format handling
- Discord: 48kHz stereo WAV -> Groq (no conversion needed)
- Telegram: OGG/Opus -> ffmpeg to WAV 16kHz mono -> local Whisper
- File uploads: any format -> local Whisper (ffmpeg handles internally)
- Video scraping: yt-dlp extracts MP3 -> local Whisper

## Gotchas

### Groq 429 when spending cap exceeded
Groq returns 429 not just for rate limits but also when the account spending cap is hit.
The error message differs: rate limit 429 has `retry-after`, spending cap 429 does not.
Fall back to local Whisper when Groq returns 429 without retry-after.

### faster-whisper model download hangs in Docker
If the Docker container has no internet access, `WhisperModel("small")` hangs
indefinitely trying to download from Hugging Face. Either pre-download models
into a volume mount or ensure container has outbound access on first run.

### openai-whisper requires torch (2+ GB)
Installing `openai-whisper` pulls in PyTorch (~2 GB). On a RAM-constrained VPS,
this can cause OOM during installation or runtime. Prefer faster-whisper which uses
CTranslate2 (much lighter). EOS has both installed but faster-whisper is always
tried first in media_processor.py.

### Whisper "Thank you for watching" hallucination
The most common hallucination is YouTube-style outros ("Thanks for watching",
"Please subscribe", "See you next time"). This comes from YouTube training data.
Filter by checking compression_ratio > 2.4 or maintaining a blocklist of known
hallucination phrases.

### WebSearch was blocked during research
External documentation sources (Groq docs, OpenAI docs, faster-whisper GitHub) could
not be fetched during skill creation. Content is based on codebase analysis, installed
package inspection, and training data. Verify Groq rate limit numbers and pricing
against https://console.groq.com/docs when web access is available.
