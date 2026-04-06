---
name: voice_pipeline
description: "Use when building or modifying audio capture, voice activity detection, speech preprocessing, or any audio buffer manipulation in the EOS voice pipeline."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/wiseman/py-webrtcvad, https://github.com/snakers4/silero-vad, https://librosa.org, https://numpy.org"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A (local libraries)"
sdk_version: "numpy 2.4.3, librosa 0.11.0, webrtcvad 2.0.10, silero-vad 6.2.1"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Voice Pipeline (numpy + librosa + webrtcvad + silero_vad)

## What This Tool Does

The EOS voice pipeline is a consolidated stack of four tightly coupled audio
libraries that handle every stage between raw Discord audio frames and
Whisper-ready input. The pipeline flow:

```
Discord Voice (48kHz stereo PCM) → SilenceDetectingSink (frame accumulation)
  → VAD filtering (silero primary, webrtcvad fallback)
  → numpy PCM conversion (int16 → float32 normalization)
  → librosa spectral analysis (music detection, resampling)
  → Whisper STT (faster-whisper or OpenAI whisper)
```

### numpy — Audio Buffer Operations
Array operations on raw PCM audio: `frombuffer` to parse byte streams into
typed arrays, `int16→float32` normalization (divide by 32768.0), amplitude
calculations via `mean`. The bridge between raw bytes and every other library.

### librosa — Audio Analysis and Preprocessing
Audio file loading with automatic resampling (`librosa.load(path, sr=16000)`),
spectral flatness for music/speech discrimination, zero-crossing rate analysis.
Used in `IntelligentVoiceProcessor.is_music()` for background music filtering.

### webrtcvad — Rule-Based Voice Activity Detection
Google's WebRTC VAD ported to Python. Operates on fixed-size PCM frames
(10/20/30ms at 8/16/32/48kHz). Three aggressiveness levels (0-3). Fast,
deterministic, zero dependencies. Used as fallback VAD in `VADProcessor` class.

### silero_vad — Neural Voice Activity Detection
ML-based VAD from Silero team. Returns continuous confidence scores (0.0-1.0)
instead of binary speech/no-speech. Loaded via `torch.hub`. More accurate than
webrtcvad especially for noisy environments, music backgrounds, and edge cases.
Primary VAD in `IntelligentVoiceProcessor.is_speech_frame()`.

## EOS Integration

### Primary modules
- `eos_ai/voice_engine.py` — `IntelligentVoiceProcessor` (Silero VAD + librosa
  music detection + numpy PCM conversion), `VADProcessor` (webrtcvad fallback),
  `VoiceEngine` (orchestrator: STT + TTS + routing)
- `services/discord_bot.py` — `SilenceDetectingSink` (AudioSink subclass,
  per-user frame accumulation, silence-threshold flush at 1.5s), `_listen_loop`
  (voice capture → Groq STT → classification → response → TTS playback)
- `eos_ai/media_processor.py` — `MediaProcessor._local_transcribe()` for
  file-based audio transcription (faster-whisper → whisper fallback)

### Audio flow in Discord voice
1. `SilenceDetectingSink.write(data, user)` — receives decoded PCM bytes from
   py-cord, appends to per-user buffer dict keyed by user_id
2. `monitor_silence()` — async loop checks every 300ms, flushes user buffer
   after 1.5s of no new frames
3. Flushed frames written to WAV: 2ch, 16-bit, 48kHz (Discord native format)
4. `on_utterance(user_id, audio_path)` — Groq STT transcribes
5. `VoiceEngine.should_respond()` — classifies speech type, filters noise
6. `IntelligentVoiceProcessor.is_music()` — librosa spectral analysis
7. Response routed through EOS gateway or local Ollama

### numpy usage in EOS
- `voice_engine.py:115` — `np.frombuffer(audio_chunk, dtype=np.int16)` parses
  raw PCM bytes into 16-bit integer array
- `voice_engine.py:116` — `.astype(np.float32) / 32768.0` normalizes to [-1.0, 1.0]
  range required by Silero VAD torch tensor input
- `voice_engine.py:135-139` — `np.mean()` computes average spectral flatness
  and zero-crossing rate for music detection scoring
- `eos_ai/embedder.py` — `np.array`, `np.float32`, `np.frombuffer` for embedding
  vector serialization (separate from voice pipeline)

### librosa usage in EOS
- `voice_engine.py:131` — `librosa.load(audio_path, sr=16000)` loads audio with
  automatic resampling to 16kHz (Whisper-compatible sample rate)
- `voice_engine.py:134` — `librosa.feature.spectral_flatness(y=y)` measures
  tonal vs noise content (music is tonal = low flatness)
- `voice_engine.py:138` — `librosa.feature.zero_crossing_rate(y)` measures
  signal polarity changes (speech has higher ZCR than music)
- Combined into `music_score = max(0.0, 1.0 - avg_flatness * 10 - avg_zcr * 5)`

### webrtcvad usage in EOS
- `voice_engine.py:338` — `webrtcvad.Vad(aggressiveness=2)` initialized at
  medium aggressiveness (0=least aggressive, 3=most)
- `voice_engine.py:344` — `vad.is_speech(audio_chunk, sample_rate)` returns
  bool for each frame
- `voice_engine.py:351-391` — `extract_speech_segments()` walks WAV file in
  30ms frames, accumulates speech regions, flushes after 10 silent frames
- Frame size calculation: `int(sample_rate * frame_duration_ms / 1000) * 2`
  (multiply by 2 for 16-bit = 2 bytes per sample)

### silero_vad usage in EOS
- `voice_engine.py:69-76` — `torch.hub.load('snakers4/silero-vad', 'silero_vad')`
  loads model (downloads ~2MB on first run, cached after)
- `voice_engine.py:101-119` — `is_speech_frame()` converts PCM bytes to numpy
  int16, normalizes to float32, wraps in `torch.FloatTensor`, passes to model
- Returns continuous confidence 0.0-1.0 (vs webrtcvad binary)
- Falls back to 0.5 (assume speech) if model fails to load

## Quick Reference

### PCM bytes to normalized float array (numpy)
```python
import numpy as np
audio_int = np.frombuffer(audio_chunk, dtype=np.int16)
audio_float = audio_int.astype(np.float32) / 32768.0
# audio_float is now [-1.0, 1.0] range, ready for Silero/librosa
```

### Silero VAD speech confidence
```python
import torch
import numpy as np

model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad',
                               force_reload=False, onnx=False)
audio_int = np.frombuffer(pcm_bytes, dtype=np.int16)
audio_float = audio_int.astype(np.float32) / 32768.0
tensor = torch.FloatTensor(audio_float)
confidence = model(tensor, 16000).item()  # 0.0-1.0
```

### webrtcvad frame check
```python
import webrtcvad
vad = webrtcvad.Vad(2)  # aggressiveness 0-3
# Frame must be exactly 10, 20, or 30ms of 16-bit PCM
# at 8000, 16000, 32000, or 48000 Hz
frame_bytes = raw_pcm[:960]  # 30ms at 16kHz = 480 samples * 2 bytes
is_speech = vad.is_speech(frame_bytes, 16000)  # returns bool
```

### librosa music detection
```python
import librosa
import numpy as np
y, sr = librosa.load(audio_path, sr=16000)
flatness = librosa.feature.spectral_flatness(y=y)
zcr = librosa.feature.zero_crossing_rate(y)
music_score = max(0.0, 1.0 - float(np.mean(flatness)) * 10
                            - float(np.mean(zcr)) * 5)
```

### librosa resample for Whisper input
```python
import librosa
# Load any audio format, auto-resample to 16kHz mono
y, sr = librosa.load('input.wav', sr=16000)  # sr=None keeps original
# y is float32 numpy array, sr is sample rate
```

### Write PCM frames to WAV (standard library)
```python
import wave
with wave.open(output_path, 'wb') as wf:
    wf.setnchannels(2)      # stereo (Discord default)
    wf.setsampwidth(2)      # 16-bit = 2 bytes
    wf.setframerate(48000)   # Discord: 48kHz
    wf.writeframes(b''.join(frame_list))
```

### Full pipeline: Discord audio to VAD-filtered transcription
```python
# 1. SilenceDetectingSink accumulates frames per user
# 2. After 1.5s silence, flush to WAV
# 3. Groq STT transcribes (or local faster-whisper)
# 4. VoiceEngine classifies and gates response
text = transcribe_with_groq(audio_path)
should_respond, classification = ve.should_respond(text, 0.0)
if should_respond:
    response = ve.route_query(text)
```

## Conceptual Model

```
Raw Audio Domain              Processing Domain           Intelligence Domain
================              =================           ===================

Discord 48kHz stereo    numpy PCM conversion        Silero VAD (neural)
PCM frames          ->  int16 -> float32 / 32768  ->  confidence 0.0-1.0
  |                       |                            |
  v                       v                            v
SilenceDetectingSink    librosa load + resample     webrtcvad (rule-based)
per-user buffers        48kHz -> 16kHz mono          binary speech/silence
  |                       |                            |
  v                       v                            v
1.5s silence flush      librosa spectral analysis   Speech classification
WAV file output         flatness + ZCR              cmd/question/thinking
  |                       |                            |
  v                       v                            v
Groq/Whisper STT        Music score 0.0-1.0         Response gating
  |                       |                            |
  +-----------+-----------+                            |
              |                                        |
              v                                        v
         Text transcript  ------>  should_respond() decision
                                        |
                                        v
                                   EOS Gateway / Ollama
```

Key principle: **Two-tier VAD**. Silero (neural, ~95% accuracy, needs torch)
is primary. webrtcvad (rule-based, ~85% accuracy, zero deps) is fallback.
The system degrades gracefully — it never fails to process audio, just with
lower accuracy.

See references/best_practices.md for full technical reference, performance
tuning, and anti-patterns.

## Gotchas

### webrtcvad frame size must be exact
webrtcvad raises `Error` if the frame is not exactly 10, 20, or 30ms worth
of 16-bit PCM at a supported sample rate (8/16/32/48kHz). One byte off and
it crashes. Formula: `frame_bytes = int(sample_rate * duration_ms / 1000) * 2`.
At 16kHz/30ms that is exactly 960 bytes. No more, no less.

### Discord sends 48kHz stereo, Whisper wants 16kHz mono
Discord voice is 48kHz 2-channel 16-bit PCM. Whisper and Silero VAD expect
16kHz mono. If you skip resampling, transcription quality drops severely.
librosa.load handles this automatically when you pass `sr=16000`, but if
you feed raw Discord PCM to Silero directly, you must pass `sample_rate=48000`
or resample first.

### Silero VAD first load downloads model from GitHub
`torch.hub.load('snakers4/silero-vad', ...)` hits GitHub on first call.
In Docker containers without internet or behind firewalls, this fails silently.
Use `force_reload=False` and ensure the model is cached in the Docker image
at build time. The EOS code handles this with a try/except that falls back
to 0.5 confidence.

### numpy int16 max is 32767 not 32768
When normalizing `int16 -> float32`, dividing by 32768.0 means the minimum
value (-32768) maps to exactly -1.0 but the maximum (32767) maps to
0.99997. This is standard practice and intentional — do not "fix" by dividing
by 32767 as that breaks the negative range.

### librosa.load returns float32 normalized by default
`librosa.load()` already returns audio as float32 in [-1.0, 1.0]. If you
then normalize again (divide by 32768), you get near-zero values and
silent-seeming audio. Only normalize raw PCM bytes — never librosa output.

### SilenceDetectingSink cleanup must set self.finished
py-cord's AudioSink base class calls `format_audio` on cleanup. If
`self.finished` is not set to `True`, the base class crashes with attribute
errors. The EOS sink explicitly sets `self.finished = True` in `cleanup()`.

### webrtcvad only supports specific sample rates
webrtcvad accepts only 8000, 16000, 32000, or 48000 Hz. Passing 44100 Hz
(CD quality, very common) raises an error. Always resample to 16000 Hz first.

### Silero VAD resets state between calls
Silero VAD maintains internal state for streaming detection. If you call
`model.reset_states()` between utterances, you lose the context that helps
with boundary detection. In EOS, the model is called per-frame without reset,
which is correct for continuous monitoring.
