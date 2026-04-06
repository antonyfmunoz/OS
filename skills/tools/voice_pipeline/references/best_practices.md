# Voice Pipeline — Creator-Level Best Practices
Source: numpy.org, librosa.org, github.com/wiseman/py-webrtcvad, github.com/snakers4/silero-vad
API Version: N/A (local processing libraries)
SDK Version: numpy 2.4.3, librosa 0.11.0, webrtcvad 2.0.10, silero-vad 6.2.1
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

N/A — all four libraries are local processing libraries with no API keys,
OAuth, or network authentication. They operate entirely on local data.

- **numpy** — no auth. Pure computation.
- **librosa** — no auth. Reads local files. Uses `soundfile` or `audioread`
  backends for decoding.
- **webrtcvad** — no auth. C extension compiled at install time.
- **silero_vad** — no auth for inference. First load fetches model weights
  from GitHub via `torch.hub` (requires internet once, then cached at
  `~/.cache/torch/hub/snakers4_silero-vad_master/`). No API key needed.

EOS env vars: None required for the voice pipeline libraries themselves.
Related env vars for the broader voice system:
- `GROQ_API_KEY` in `services/.env` — for Groq Whisper STT (downstream)
- `GEMINI_API_KEY` in `eos_ai/.env` — for MediaProcessor audio analysis

## Core Operations with Exact Signatures

### numpy (audio-relevant operations)

```python
import numpy as np

# Parse raw PCM bytes into typed array
audio_int16 = np.frombuffer(
    buffer: bytes,          # required — raw PCM bytes
    dtype=np.int16,         # required — sample format
    count=-1,               # optional — number of samples (-1 = all)
    offset=0,               # optional — byte offset into buffer
)
# Returns: np.ndarray[np.int16], shape (n_samples,)

# Type conversion with normalization
audio_f32 = audio_int16.astype(np.float32)  # cast without scaling
audio_normalized = audio_f32 / 32768.0       # normalize to [-1.0, 1.0]

# Statistical operations on audio
rms = float(np.sqrt(np.mean(audio_f32 ** 2)))   # RMS amplitude
peak = float(np.max(np.abs(audio_f32)))          # peak amplitude
mean_val = float(np.mean(feature_array))          # mean of feature vector

# Array creation for audio buffers
silence = np.zeros(n_samples, dtype=np.int16)     # silent buffer
concatenated = np.concatenate([chunk1, chunk2])   # join audio segments

# Byte serialization (for WAV writing)
pcm_bytes = audio_int16.tobytes()                 # ndarray -> bytes
```

### librosa

```python
import librosa

# Load audio file with automatic resampling
y, sr = librosa.load(
    path: str | Path,       # required — audio file path
    sr: int | None = 22050, # optional — target sample rate (None = native)
    mono: bool = True,      # optional — downmix to mono
    offset: float = 0.0,    # optional — start time in seconds
    duration: float | None = None,  # optional — load duration in seconds
    dtype: np.dtype = np.float32,   # optional — output dtype
)
# Returns: tuple[np.ndarray, int] — (audio array, sample rate)
# Audio is ALREADY normalized to [-1.0, 1.0] float32

# Spectral flatness (Wiener entropy) — tonal vs noise
flatness = librosa.feature.spectral_flatness(
    y: np.ndarray = None,   # required — audio time series
    S: np.ndarray = None,   # optional — pre-computed spectrogram
    n_fft: int = 2048,      # optional — FFT window size
    hop_length: int = 512,  # optional — hop between frames
)
# Returns: np.ndarray shape (1, n_frames) — values in [0, 1]
# 0.0 = perfectly tonal (pure sine), 1.0 = perfectly flat (white noise)

# Zero-crossing rate
zcr = librosa.feature.zero_crossing_rate(
    y: np.ndarray,           # required — audio time series
    frame_length: int = 2048,
    hop_length: int = 512,
)
# Returns: np.ndarray shape (1, n_frames) — values in [0, 1]

# Resample (explicit, when librosa.load sr= is not enough)
y_resampled = librosa.resample(
    y: np.ndarray,           # required — input audio
    orig_sr: int,            # required — original sample rate
    target_sr: int,          # required — target sample rate
    res_type: str = 'soxr_hq',  # optional — resampling algorithm
)
# Returns: np.ndarray — resampled audio

# Mel spectrogram (useful for advanced preprocessing)
S = librosa.feature.melspectrogram(
    y=y, sr=sr,
    n_mels: int = 128,
    n_fft: int = 2048,
    hop_length: int = 512,
)
# Returns: np.ndarray shape (n_mels, n_frames)
```

### webrtcvad

```python
import webrtcvad

# Initialize VAD
vad = webrtcvad.Vad(
    mode: int = None,  # optional — aggressiveness 0-3
)
# mode 0: least aggressive (fewer false negatives, more false positives)
# mode 1: moderate
# mode 2: moderately aggressive (EOS default)
# mode 3: most aggressive (more false negatives, fewer false positives)

vad.set_mode(mode: int)  # change aggressiveness after init

# Check single frame for speech
is_speech = vad.is_speech(
    buf: bytes,             # required — PCM audio frame (EXACT size required)
    sample_rate: int,       # required — 8000, 16000, 32000, or 48000 ONLY
    length: int = None,     # optional — buffer length (auto-detected)
)
# Returns: bool — True if speech detected
# Frame MUST be exactly 10, 20, or 30ms of 16-bit mono PCM
# At 16000 Hz, 30ms = 480 samples * 2 bytes = 960 bytes

# Valid frame sizes (bytes) per sample rate:
# 8000 Hz:  160 (10ms), 320 (20ms), 480 (30ms)
# 16000 Hz: 320 (10ms), 640 (20ms), 960 (30ms)
# 32000 Hz: 640 (10ms), 1280 (20ms), 1920 (30ms)
# 48000 Hz: 960 (10ms), 1920 (20ms), 2880 (30ms)
```

### silero_vad

```python
import torch

# Load model (downloads from GitHub on first call, ~2MB)
model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload: bool = False,    # True = re-download
    onnx: bool = False,            # True = use ONNX runtime (lighter)
)
# Returns: (model, utils_tuple)
# utils contains: (get_speech_timestamps, save_audio, read_audio,
#                  VADIterator, collect_chunks)

# Per-frame speech probability
audio_tensor = torch.FloatTensor(audio_float32_array)
confidence = model(
    audio_tensor,           # required — float32 tensor, normalized [-1, 1]
    sr: int,                # required — sample rate (8000 or 16000)
)
# Returns: torch.Tensor — single float, speech probability 0.0-1.0
# Recommended threshold: 0.5 for general use, 0.3 for high recall

# Get speech timestamps from full audio
get_speech_timestamps = utils[0]
timestamps = get_speech_timestamps(
    audio: torch.Tensor,          # required — full audio tensor
    model,                         # required — loaded model
    threshold: float = 0.5,       # speech probability threshold
    sampling_rate: int = 16000,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 100,
    speech_pad_ms: int = 30,
    return_seconds: bool = False,
)
# Returns: list[dict] — [{'start': int, 'end': int}, ...]
# Values are sample indices (or seconds if return_seconds=True)

# Reset model state (between separate audio files, NOT between frames)
model.reset_states()

# Streaming via VADIterator (chunk-by-chunk processing)
VADIterator = utils[3]
vad_iterator = VADIterator(
    model,
    threshold: float = 0.5,
    sampling_rate: int = 16000,
    min_silence_duration_ms: int = 300,
    speech_pad_ms: int = 30,
)
# Feed chunks:
speech_dict = vad_iterator(chunk_tensor, return_seconds=True)
# Returns: None (no event) | {'start': float} | {'end': float}
vad_iterator.reset_states()  # between separate audio streams
```

## Pagination Patterns

N/A — these are local processing libraries operating on in-memory arrays
and audio files. No API pagination. For large audio files, process in
chunks using streaming patterns:

```python
# Chunked processing pattern for large files
CHUNK_SIZE = 16000 * 30  # 30 seconds at 16kHz
y, sr = librosa.load(path, sr=16000)
for i in range(0, len(y), CHUNK_SIZE):
    chunk = y[i:i + CHUNK_SIZE]
    # process chunk
```

## Rate Limits

N/A for API rate limits. Processing performance constraints:

| Library | Operation | Latency (CPU) | Memory |
|---------|-----------|---------------|--------|
| numpy | frombuffer 1s @ 16kHz | <1ms | ~64KB |
| numpy | float32 normalize 1s | <1ms | ~128KB |
| librosa | load + resample 10s audio | ~200ms | ~1.2MB |
| librosa | spectral_flatness 10s | ~50ms | ~500KB |
| librosa | melspectrogram 10s | ~100ms | ~2MB |
| webrtcvad | is_speech per frame | <0.1ms | negligible |
| webrtcvad | extract_speech 60s file | ~20ms | ~2MB |
| silero_vad | model load (first) | ~2s | ~50MB (torch) |
| silero_vad | model load (cached) | ~500ms | ~50MB (torch) |
| silero_vad | per-frame inference | ~5ms | negligible |
| silero_vad | get_speech_timestamps 60s | ~300ms | ~10MB |

Key bottleneck: Silero VAD model loading. Load once at startup, reuse.
EOS does this via lazy loading in `IntelligentVoiceProcessor.load_silero()`.

## Error Codes and Recovery

### numpy
| Error | Cause | Recovery |
|-------|-------|----------|
| `ValueError: buffer size not divisible by element size` | PCM bytes length not multiple of 2 (int16) | Trim to even length: `buf[:len(buf) - len(buf) % 2]` |
| `ValueError: cannot reshape array of size X into shape Y` | Wrong channel count assumption | Check actual channel count from WAV header |

### librosa
| Error | Cause | Recovery |
|-------|-------|----------|
| `audioread.NoBackendError` | No audio decoder installed | `apt-get install ffmpeg libsndfile1` |
| `librosa.util.exceptions.ParameterError` | Invalid parameter (e.g., sr=0) | Validate inputs before call |
| Empty array returned | File is silence or corrupt | Check `len(y) > 0` and `np.max(np.abs(y)) > 0.001` |

### webrtcvad
| Error | Cause | Recovery |
|-------|-------|----------|
| `webrtcvad.Error` (no specific subtypes) | Wrong frame size or sample rate | Verify exact byte count per formula |
| `webrtcvad.Error` | Sample rate not in {8000, 16000, 32000, 48000} | Resample first |
| Silent crash / wrong results | Audio is stereo not mono | Downmix to mono before VAD |

### silero_vad
| Error | Cause | Recovery |
|-------|-------|----------|
| `urllib.error.URLError` | No internet on first load | Pre-cache model in Docker build |
| `RuntimeError: expected Float tensor` | Input not float32 | Ensure `.astype(np.float32) / 32768.0` |
| `RuntimeError: expected 1D tensor` | Multi-channel input | Flatten or select channel 0 |
| Low confidence on clear speech | Wrong sample rate passed | Must pass actual sr matching the audio |

All errors in the EOS pipeline are caught with try/except and fall back:
Silero fails → returns 0.5 confidence (assume speech). webrtcvad fails →
returns False (assume silence). librosa fails → returns 0.0 music score.

## SDK Idioms

### numpy — audio-specific idioms
```python
# CORRECT: Parse PCM and normalize in one chain
audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

# WRONG: Using float64 (wastes memory, no accuracy benefit for audio)
audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float64) / 32768.0

# CORRECT: Check for silence before processing
if np.max(np.abs(audio)) < 0.01:
    return  # skip silent frames

# CORRECT: Stereo to mono downmix
stereo = np.frombuffer(raw_bytes, dtype=np.int16).reshape(-1, 2)
mono = stereo.mean(axis=1).astype(np.int16)
```

### librosa — idiomatic usage
```python
# CORRECT: Let librosa handle resampling
y, sr = librosa.load(path, sr=16000)  # auto-resample

# WRONG: Load at native rate then manually resample
y, sr = librosa.load(path, sr=None)
y = librosa.resample(y, orig_sr=sr, target_sr=16000)  # redundant

# CORRECT: Feature extraction with consistent parameters
n_fft = 2048
hop_length = 512
flatness = librosa.feature.spectral_flatness(y=y, n_fft=n_fft, hop_length=hop_length)
zcr = librosa.feature.zero_crossing_rate(y, frame_length=n_fft, hop_length=hop_length)
```

### webrtcvad — idiomatic usage
```python
# CORRECT: Calculate exact frame size
frame_duration_ms = 30
frame_size = int(sample_rate * frame_duration_ms / 1000) * 2  # *2 for int16

# CORRECT: Walk audio in exact-size frames
for offset in range(0, len(audio_bytes) - frame_size + 1, frame_size):
    frame = audio_bytes[offset:offset + frame_size]
    if vad.is_speech(frame, sample_rate):
        speech_frames.append(frame)
```

### silero_vad — idiomatic usage
```python
# CORRECT: Lazy load, reuse model
class Processor:
    def __init__(self):
        self._model = None
    def _ensure_model(self):
        if self._model is None:
            self._model, _ = torch.hub.load('snakers4/silero-vad', 'silero_vad')
    def check(self, audio):
        self._ensure_model()
        return self._model(torch.FloatTensor(audio), 16000).item()

# WRONG: Loading model per call
def check(audio):
    model, _ = torch.hub.load(...)  # 500ms+ overhead EVERY call
    return model(torch.FloatTensor(audio), 16000).item()
```

## Anti-Patterns

### 1. Double normalization
```python
# WRONG: librosa.load already normalizes
y, sr = librosa.load(path, sr=16000)
y_norm = y / 32768.0  # y is ALREADY [-1.0, 1.0]!
# Result: near-zero values, everything sounds silent

# CORRECT:
y, sr = librosa.load(path, sr=16000)  # already normalized
# Use y directly
```

### 2. Wrong dtype for webrtcvad
```python
# WRONG: Passing float32 bytes to webrtcvad
audio_float = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
vad.is_speech(audio_float.tobytes(), 16000)  # CRASH: wrong byte count

# CORRECT: webrtcvad needs raw int16 PCM bytes
vad.is_speech(raw_pcm_bytes, 16000)
```

### 3. Feeding stereo audio to mono-expecting VAD
```python
# WRONG: Discord is stereo, VAD expects mono
with wave.open(path, 'rb') as wf:
    frames = wf.readframes(wf.getnframes())
vad.is_speech(frames[:960], 48000)  # stereo bytes = wrong frame size

# CORRECT: Downmix or use only one channel
stereo = np.frombuffer(frames, dtype=np.int16).reshape(-1, 2)
mono = stereo[:, 0]  # left channel
vad.is_speech(mono[:480].tobytes(), 48000)  # 480 samples = 10ms @ 48kHz
```

### 4. Resetting Silero state mid-stream
```python
# WRONG: Resetting between frames of same utterance
for frame in frames:
    model.reset_states()  # kills context!
    conf = model(torch.FloatTensor(frame), 16000).item()

# CORRECT: Reset only between separate audio files/streams
model.reset_states()
for frame in frames:
    conf = model(torch.FloatTensor(frame), 16000).item()
```

### 5. Loading Silero model per frame
```python
# WRONG: ~500ms overhead per call
for frame in audio_frames:
    model, _ = torch.hub.load('snakers4/silero-vad', 'silero_vad')
    conf = model(torch.FloatTensor(frame), 16000).item()

# CORRECT: Load once, reuse
model, _ = torch.hub.load('snakers4/silero-vad', 'silero_vad')
for frame in audio_frames:
    conf = model(torch.FloatTensor(frame), 16000).item()
```

### 6. Ignoring librosa's sr parameter behavior
```python
# WRONG: Assuming sr=None keeps original and returns that rate
y, sr = librosa.load(path)  # sr defaults to 22050! Not native rate!

# CORRECT: Explicit about what you want
y, sr = librosa.load(path, sr=16000)   # resample to 16kHz
y, sr = librosa.load(path, sr=None)    # keep native rate
```

## Data Model

### Audio Format Matrix

| Source | Sample Rate | Channels | Bit Depth | Format |
|--------|------------|----------|-----------|--------|
| Discord voice | 48000 Hz | 2 (stereo) | 16-bit | PCM (raw bytes) |
| Whisper input | 16000 Hz | 1 (mono) | 32-bit float | numpy array |
| Silero input | 8000/16000 Hz | 1 (mono) | 32-bit float | torch tensor |
| webrtcvad input | 8k/16k/32k/48k | 1 (mono) | 16-bit | PCM bytes |
| librosa output | any (specified) | 1 (mono default) | 32-bit float | numpy array |
| WAV file output | varies | varies | 16-bit | PCM in WAV container |

### Key conversions
- Discord PCM → Silero: downsample 48k→16k, stereo→mono, int16→float32/32768
- Discord PCM → webrtcvad: stereo→mono, keep int16 bytes, exact frame slicing
- Discord PCM → librosa: save to WAV first, `librosa.load(path, sr=16000)`
- librosa output → Silero: `torch.FloatTensor(y)` (already float32 normalized)

### EOS internal data structures
```python
# SilenceDetectingSink buffer
self._buffers: dict[int, list[bytes]]   # user_id -> list of PCM frame bytes
self._last_audio: dict[int, float]      # user_id -> time.time() of last frame

# VADProcessor segment extraction
segments: list[bytes]                    # speech regions as raw PCM bytes
speech_frames: list[bytes]               # accumulator during walk

# IntelligentVoiceProcessor context
self.context_window: deque[dict]         # maxlen=10, rolling conversation
# Each entry: {'utterance': str, 'classification': str,
#              'response': str, 'timestamp': str}
```

## Webhooks and Events

N/A — local processing libraries. No webhooks or event subscriptions.

The voice pipeline is event-driven through Discord's voice WebSocket:
- py-cord's `AudioSink.write()` is called per audio frame (the "event")
- `SilenceDetectingSink.monitor_silence()` is the poll loop (300ms interval)
- Flush events trigger `on_utterance()` callback

## Limits

### numpy
- Array size limited by available RAM (no hard cap)
- `np.int16` range: -32768 to 32767
- `np.float32` precision: ~7 decimal digits

### librosa
- `librosa.load` loads entire file into memory — for files >100MB, use
  `offset` and `duration` parameters to load segments
- Default `sr=22050` — always specify explicitly
- `n_fft` must be positive integer, typically power of 2
- Feature frames: `n_frames = 1 + (n_samples - n_fft) // hop_length`

### webrtcvad
- Frame duration: exactly 10, 20, or 30ms (no other values)
- Sample rates: exactly 8000, 16000, 32000, or 48000 Hz
- Input: mono 16-bit PCM only (no float, no stereo, no 8-bit)
- Aggressiveness: integer 0-3 only

### silero_vad
- Input sample rate: 8000 or 16000 Hz only (not 48000)
- Input: 1D float32 tensor, normalized to [-1.0, 1.0]
- Model size: ~2MB weights, ~50MB with torch runtime
- Minimum audio length for reliable detection: ~30ms
- `get_speech_timestamps` loads entire audio into memory

## Cost Model

All four libraries are free and open source. Cost is CPU/memory:

| Resource | numpy | librosa | webrtcvad | silero_vad |
|----------|-------|---------|-----------|------------|
| Install size | ~30MB | ~25MB | ~50KB | ~2MB (+torch ~800MB) |
| Runtime RAM | <1MB per op | ~50MB loaded | <1MB | ~50MB (model) |
| CPU per frame | <0.1ms | N/A (file-level) | <0.1ms | ~5ms |
| License | BSD-3 | ISC | MIT | MIT |

**torch is the heavy dependency.** silero_vad requires torch + torchaudio
(~800MB installed). If memory is constrained, fall back to webrtcvad (zero
heavy deps). EOS handles this with the two-tier architecture: try Silero,
fall back to webrtcvad.

On the EOS VPS (4GB RAM): torch + silero model + Discord bot consumes
~1.2GB. With Ollama running (gemma3:4b = ~3.3GB), memory gets tight.
The `os-bot` service is stopped when Ollama needs full memory.

## Version Pinning

### Current versions in EOS
| Package | Version | Pinned in |
|---------|---------|-----------|
| numpy | 2.4.3 | services/requirements.txt (unpinned) |
| librosa | 0.11.0 | services/requirements.txt (unpinned) |
| webrtcvad | 2.0.10 | services/requirements.txt (unpinned) |
| silero-vad | 6.2.1 | services/requirements.txt (unpinned) |

### Version notes
- **numpy 2.x** — major release. `np.bool` and `np.int` aliases removed.
  Use `np.bool_` and `np.int_` or Python builtins. EOS code is clean.
- **librosa 0.11.0** — current stable. Dropped Python 3.8 support.
  No breaking changes from 0.10.x for features EOS uses.
- **webrtcvad 2.0.10** — last release was 2020. Stable, no updates expected.
  C extension compiles against Python 3.12 without issues.
- **silero-vad 6.x** — major version jump from 5.x. New package structure,
  now installable via pip (`pip install silero-vad`). torch.hub still works.
  ONNX support improved.
- **Recommendation**: Pin exact versions in requirements.txt to prevent
  surprise breaks: `numpy==2.4.3`, `librosa==0.11.0`, `silero-vad==6.2.1`.

### Deprecation watch
- numpy: `np.float_` → use `np.float64`. `np.complex_` → `np.complex128`
- librosa: `librosa.output.write_wav` removed in 0.8+ → use `soundfile.write`
- webrtcvad: No active development. May not compile on future Python versions.
  Alternative: `py-webrtcvad-wheels` provides pre-built wheels.
- silero_vad: torch.hub loading path may change. Monitor snakers4/silero-vad
  releases. ONNX path is more stable long-term.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

### numpy
Created by Travis Oliphant (2005) as the unification of Numeric and numarray.
Design philosophy: fast C-backed array operations with Python syntax. The key
tradeoff is **generality over specialization** — numpy does not know about audio,
but its array primitives (`frombuffer`, `astype`, `mean`) are the universal glue
between every audio library. Every audio library returns or consumes numpy arrays.

### librosa
Created by Brian McFee at NYU (2015) for music information retrieval (MIR)
research. Design philosophy: **Pythonic convenience over raw performance**.
`librosa.load()` handles format detection, decoding, resampling, mono conversion,
and float32 normalization in one call. The tradeoff: it loads entire files into
memory (no streaming). Optimized for analysis, not real-time processing.

### webrtcvad
Extracted from Google's WebRTC codebase by John Wiseman (2016). The C code is
Google's production VAD used in Chrome and Android. Design philosophy: **speed
and determinism over accuracy**. Binary yes/no per frame, no confidence score.
The aggressiveness parameter is the only knob. Tradeoff: fast and reliable but
misclassifies music as speech and struggles with low-SNR environments.

### silero_vad
Created by Silero team (Alexander Veysov et al., 2021). Design philosophy:
**accuracy over simplicity**. Uses a small neural network (~2MB) that
dramatically outperforms rule-based VAD in noisy conditions, music backgrounds,
and non-English speech. Tradeoff: requires torch (~800MB), 5ms per frame vs
0.1ms for webrtcvad. The continuous confidence output (0.0-1.0) enables
threshold tuning that binary VAD cannot.

### EOS design decision
Two-tier VAD (Silero primary, webrtcvad fallback) is a deliberate
availability-over-accuracy degradation strategy. The system never refuses to
process audio. It just gets less accurate without torch.

## Problem-Solution Map and Hidden Capabilities

### Silence-gated recording (what EOS does)
Problem: Fixed-time recording chunks waste bandwidth and create awkward cuts.
Solution: SilenceDetectingSink with per-user buffers and configurable threshold.
Not a feature of any single library — it is a composition of py-cord AudioSink +
time-based flush logic.

### Music filtering before transcription
Problem: Background music causes Whisper hallucinations ("Thank you for
watching", lyrics from songs).
Solution: librosa spectral_flatness + zero_crossing_rate → music_score → gate.
Hidden capability: this same score can detect other non-speech audio (typing,
ambient noise) by adjusting the formula weights.

### Continuous VAD confidence for smart gating
Problem: Binary speech/no-speech loses nuance.
Solution: Silero's 0.0-1.0 confidence enables adaptive thresholds.
Hidden capability: Track confidence over time to detect speech onset/offset
with sub-frame precision. Use rolling average to smooth false triggers.

### librosa onset detection for utterance boundaries
Not currently used in EOS but available:
`librosa.onset.onset_detect(y=y, sr=sr)` finds audio event boundaries.
Could improve the silence-threshold approach by detecting actual speech
boundaries instead of relying on silence duration.

### numpy audio manipulation
Hidden capabilities beyond basic conversion:
- `np.correlate(a, b)` — cross-correlation for echo detection
- `np.fft.rfft(audio)` — frequency domain analysis without librosa
- `np.convolve(audio, kernel)` — apply filters (low-pass, high-pass)
- `np.clip(audio, -1.0, 1.0)` — prevent clipping artifacts

## Operational Behavior and Edge Cases

### Discord audio frame timing is not guaranteed
py-cord delivers audio frames via `AudioSink.write()` but timing between
calls varies. Under network congestion, frames arrive in bursts. The
SilenceDetectingSink handles this by using wall-clock time for silence
detection rather than frame count.

### webrtcvad is unreliable below 300ms of audio
Very short audio segments (<300ms) produce inconsistent results with webrtcvad.
The EOS minimum segment threshold (`len(speech_frames) > 20` = ~600ms at 30ms
frames) prevents this.

### librosa.load silently returns empty array for corrupt files
If the audio file is corrupt or zero-length, `librosa.load()` may return
`(np.array([]), sr)` without raising an exception. Always check
`len(y) > 0` after loading.

### Silero VAD accumulates state across calls
The model maintains internal LSTM state between `model(tensor, sr)` calls.
This is correct for streaming (helps with boundary detection) but means
processing files out of order produces wrong results. Call
`model.reset_states()` between separate audio files/conversations.

### 48kHz to 16kHz resampling introduces artifacts
Downsampling by 3x (48000→16000) can introduce aliasing artifacts.
librosa uses high-quality `soxr_hq` resampling by default which minimizes
this, but cheap resampling (linear interpolation) causes audible artifacts
that degrade STT accuracy.

### Zero-length audio files from Discord disconnects
When a user disconnects mid-utterance, the SilenceDetectingSink may flush
an extremely short buffer. The `_listen_loop` guards with
`if not text or len(text.split()) < 2: return` to discard empty/trivial
transcriptions.

## Ecosystem Position and Composition

### Pipeline position
```
[Input Layer]        [Processing Layer]     [Intelligence Layer]
Discord py-cord  →   numpy + librosa    →   Silero/webrtcvad
                     + wave (stdlib)         + Whisper/Groq STT
                                            + speech classification
```

### Natural complements
- **faster-whisper** / **openai-whisper** — downstream STT consumer
- **Groq API** — cloud STT alternative (whisper-large-v3-turbo)
- **torch** — required runtime for Silero VAD
- **soundfile** — librosa's preferred audio I/O backend
- **ffmpeg** — audio format conversion (librosa uses via audioread)
- **pyttsx3** / **espeak** / **Coqui TTS** — TTS output (reverse pipeline)

### Forced integrations to avoid
- **pyaudio** — microphone capture library. EOS gets audio from Discord, not
  local mic. pyaudio adds complexity with no benefit.
- **scipy.signal** — overlaps with librosa for filtering. Pick one.
- **pydub** — audio manipulation wrapper. Adds dependency for things numpy
  already does.

## Trajectory and Evolution

### numpy
Stable foundation. numpy 2.x cleaned up type aliases. No audio-specific
evolution expected. Will remain the universal array layer.

### librosa
Moving toward lazy loading (0.10+) and better streaming support. The
`lazy_loader` dependency enables faster import. Future versions may add
native streaming for large files. The MIR community is active.

### webrtcvad
Effectively abandoned (last release: 2020). The C code is frozen Google
WebRTC from ~2018. Will eventually break on new Python versions when C API
changes. **Plan for replacement.** silero_vad is the successor for new code.
`py-webrtcvad-wheels` extends life with pre-built wheels.

### silero_vad
Active development. Version 6.x added pip install support, ONNX improvements,
and better multi-language support. The ONNX path (`onnx=True`) reduces torch
dependency to just onnxruntime (~50MB vs ~800MB). This is the future direction
for EOS — when memory is constrained, switch to ONNX Silero and drop torch.

### Recommendation for EOS
Monitor silero-vad releases. When ONNX path is fully stable, migrate from
torch.hub loading to `pip install silero-vad` + ONNX. This saves ~750MB RAM
and removes the GitHub download on first load.

## Conceptual Model and Solution Recipes

### Mental model: The Audio Processing Stack
Think of audio processing as four layers, bottom to top:

1. **Transport** — How audio bytes arrive (Discord WebSocket, file upload)
2. **Conversion** — Raw format to normalized arrays (numpy)
3. **Analysis** — What is in the audio (librosa features, VAD)
4. **Decision** — What to do with it (classify, transcribe, respond)

Every operation in the voice pipeline maps to one of these layers.
Never skip a layer — always convert before analyzing.

### Recipe: Add speech energy gating
```python
# Gate on audio energy before expensive VAD
import numpy as np
audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
rms = float(np.sqrt(np.mean(audio ** 2)))
if rms < 0.01:  # silence threshold
    return  # skip VAD entirely — saves 5ms per frame
confidence = silero_model(torch.FloatTensor(audio), 16000).item()
```

### Recipe: Extract and transcribe only speech segments
```python
# Full pipeline: file → VAD → segments → STT
import torch, librosa
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad')
get_speech_timestamps = utils[0]
y, sr = librosa.load(audio_path, sr=16000)
tensor = torch.FloatTensor(y)
timestamps = get_speech_timestamps(tensor, model, sampling_rate=16000)
for ts in timestamps:
    segment = y[ts['start']:ts['end']]
    # save segment and transcribe with Whisper
```

### Recipe: Real-time streaming VAD with adaptive threshold
```python
# Use VADIterator for chunk-by-chunk processing
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad')
VADIterator = utils[3]
vad_iter = VADIterator(model, threshold=0.5, sampling_rate=16000)
for chunk in audio_stream:
    audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
    result = vad_iter(torch.FloatTensor(audio), return_seconds=True)
    if result and 'start' in result:
        print(f"Speech started at {result['start']}s")
    elif result and 'end' in result:
        print(f"Speech ended at {result['end']}s")
```

### Recipe: Music vs speech classifier
```python
# Combine librosa features for robust classification
import librosa, numpy as np
y, sr = librosa.load(path, sr=16000)
flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
# Music: low flatness (tonal), low ZCR, high rolloff
# Speech: medium flatness, high ZCR, medium rolloff
# Noise: high flatness, variable ZCR, variable rolloff
music_score = max(0.0, 1.0 - flatness * 10 - zcr * 5)
```

## Industry Expert and Cutting-Edge Usage

### Two-tier VAD is industry standard
Production voice pipelines (Google Meet, Zoom, Discord itself) use a fast
rule-based VAD for initial gating and a neural model for refined detection.
EOS mirrors this with webrtcvad (fast gate) + Silero (neural refinement).
The key insight: run the cheap detector first to avoid running the expensive
one on silence.

### Silero VAD as Whisper preprocessor
The Whisper team at OpenAI documented that VAD preprocessing before
transcription dramatically reduces hallucinations on silent/noisy segments.
faster-whisper has this built in (`vad_filter=True` uses Silero internally).
EOS uses this in `IntelligentVoiceProcessor.transcribe_fast()`.

### Spectral analysis for content-aware routing
Beyond simple music detection, spectral features enable:
- **Typing detection** — keyboard sounds have distinctive spectral patterns
- **Multiple speaker detection** — spectral variation indicates turn-taking
- **Emotion detection** — pitch contour (librosa.piptrack) correlates with
  speaker emotional state
- **Language detection** — spectral patterns differ across languages

### ONNX migration for edge deployment
The cutting-edge pattern for production VAD is Silero ONNX + numpy only
(no torch). This reduces the runtime from ~800MB to ~50MB while maintaining
95%+ accuracy. The silero-vad 6.x package supports this natively:
```python
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', onnx=True)
```
For EOS, this is the recommended migration path when memory pressure requires
dropping torch.

### Voice activity detection for meeting intelligence
Advanced pattern: use VAD timestamps + speaker diarization to create
structured meeting transcripts with speaker labels and talk-time metrics.
Libraries like `pyannote.audio` build on the same numpy/torch foundation
that Silero uses. EOS already captures meeting notes in `_active_meeting` —
adding speaker diarization would make this production-grade.

---

## EOS Usage Patterns

### Current pipeline (discord_bot.py)
1. `SilenceDetectingSink.write()` — per-user PCM frame accumulation
2. `monitor_silence()` — 300ms poll, 1.5s silence threshold flush
3. WAV write: 2ch/16-bit/48kHz (Discord native)
4. `transcribe_with_groq()` — Groq whisper-large-v3-turbo (cloud STT)
5. `VoiceEngine.should_respond()` — speech classification gate
6. `IntelligentVoiceProcessor.classify_speech()` — text-based classification
7. Context window management (rolling 10 utterances)
8. Response via EOS gateway or local Ollama
9. TTS playback via Coqui/espeak

### Current pipeline (voice_engine.py)
1. `IntelligentVoiceProcessor.is_speech_frame()` — Silero VAD on raw PCM
2. `is_music()` — librosa spectral analysis
3. `transcribe_fast()` — faster-whisper with built-in VAD filter
4. `classify_speech()` — text pattern matching for type classification
5. `VoiceEngine.transcribe_with_vad()` — webrtcvad segment extraction +
   per-segment Whisper transcription (fallback path)

### Key configuration values
- Silence threshold: 1.5s (`SilenceDetectingSink`)
- webrtcvad aggressiveness: 2 (`VADProcessor`)
- webrtcvad frame duration: 30ms
- webrtcvad silence threshold: 10 frames (~300ms)
- webrtcvad minimum segment: 20 frames (~600ms)
- Silero fallback confidence: 0.5 (assume speech on error)
- Context window: 10 utterances (deque maxlen)
- Mid-thought threshold: 1.5s
- End utterance threshold: 2.5s
- Reset threshold: 8.0s

## Gotchas

### webrtcvad frame size crash is the #1 failure mode
Any byte count that does not exactly match `int(sr * duration_ms / 1000) * 2`
causes an immediate crash with an unhelpful `webrtcvad.Error` message. This
has bitten EOS development multiple times. The formula is non-negotiable.

### Silero model download fails in Docker without internet
First call to `torch.hub.load()` needs GitHub access. Docker builds that
cache pip packages but not torch hub models will fail at runtime. Fix: run
the model load during Docker build, or mount the cached model directory.

### librosa import takes ~2 seconds
librosa has heavy dependencies (numba, scipy, scikit-learn). First import
is slow. This does not affect EOS (loaded at service start) but can cause
timeouts in short-lived scripts. Use lazy imports when possible.

### Discord 48kHz stereo vs 16kHz mono expectations
Every downstream consumer (Whisper, Silero, webrtcvad in EOS config) expects
16kHz mono. Discord produces 48kHz stereo. Forgetting to resample is the
second most common failure after webrtcvad frame size errors.

### numpy float32 precision loss in long recordings
float32 has ~7 decimal digits of precision. For very long recordings (>10
minutes), accumulated floating-point error in running statistics can drift.
Process in chunks for long audio. EOS is not affected because utterances
are short (1.5s silence-gated segments).

### webrtcvad was last updated in 2020
No bug fixes, no Python 3.13+ testing. If it breaks on a future Python
version, the fix is to switch entirely to Silero VAD. The two-tier
architecture makes this a configuration change, not a rewrite.
