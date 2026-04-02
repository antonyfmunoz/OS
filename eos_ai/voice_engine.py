"""
VoiceEngine — intelligent voice layer for Discord.

Handles:
  - Speech-to-text  : faster-whisper (fast, built-in VAD) → OpenAI Whisper fallback
  - Speech detection: Silero VAD (neural) → webrtcvad fallback
  - Speech classify : command / question / conversation / thinking_aloud / singing
  - Text-to-speech  : Coqui TTS → espeak fallback
  - Local LLM       : Qwen2.5:3b via Ollama (free, fast)
  - Query routing   : simple → Ollama | complex → Claude via EOS gateway
  - Meeting context : auto-detects meeting type from natural language cues
  - Context window  : rolling 10-utterance conversation memory

This module is separate from VoiceInterface (which wraps MediaProcessor
for Telegram meeting intelligence). VoiceEngine is Discord-specific —
optimised for real-time voice channel interaction.
"""

import os
import subprocess
import tempfile
import wave
from collections import deque
from datetime import datetime
from pathlib import Path


# ─── Speech classification constants ──────────────────────────────────────────

class SpeechClassification:
    COMMAND          = 'command'
    QUESTION         = 'question'
    CONVERSATION     = 'conversation'
    THINKING_ALOUD   = 'thinking_aloud'
    SINGING          = 'singing'
    MUSIC_BACKGROUND = 'music_background'
    SILENCE          = 'silence'
    MID_THOUGHT      = 'mid_thought'


# ─── Intelligent voice processor ──────────────────────────────────────────────

class IntelligentVoiceProcessor:
    """
    Neural speech understanding layer.

    Silero VAD → faster-whisper → speech classification.
    Filters noise, music, and thinking-aloud from actionable utterances.
    Maintains conversation context window for response continuity.
    Auto-detects meeting contexts from natural language cues.
    """

    def __init__(self, voice_engine=None) -> None:
        self._silero_model = None
        self._utils = None
        self._faster_whisper = None
        self._ve = voice_engine          # ref back to VoiceEngine for transcribe fallback
        self.context_window: deque = deque(maxlen=10)
        self.last_speech_time: datetime | None = None
        self.mid_thought_threshold  = 1.5   # seconds
        self.end_utterance_threshold = 2.5  # seconds
        self.reset_threshold        = 8.0   # seconds

    # ─── Model loading ────────────────────────────────────────────────────────

    def load_silero(self) -> bool:
        """Load Silero VAD model via torch.hub."""
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )
            self._silero_model = model
            self._utils = utils
            print('[Voice] Silero VAD loaded')
            return True
        except Exception as e:
            print(f'[Voice] Silero load failed: {e}')
            return False

    def load_faster_whisper(self, model_size: str = 'base') -> bool:
        """Load faster-whisper model (CTranslate2 — no torch required)."""
        try:
            from faster_whisper import WhisperModel
            self._faster_whisper = WhisperModel(
                model_size,
                device='cpu',
                compute_type='int8',
            )
            print(f'[Voice] faster-whisper {model_size} loaded')
            return True
        except Exception as e:
            print(f'[Voice] faster-whisper failed: {e}')
            return False

    # ─── Speech detection ─────────────────────────────────────────────────────

    def is_speech_frame(
        self,
        audio_chunk: bytes,
        sample_rate: int = 16000,
    ) -> float:
        """Returns confidence 0.0-1.0 that this frame contains speech."""
        if self._silero_model is None:
            self.load_silero()
        if self._silero_model is None:
            return 0.5  # fallback: assume speech

        try:
            import torch
            import numpy as np
            audio_int   = np.frombuffer(audio_chunk, dtype=np.int16)
            audio_float = audio_int.astype(np.float32) / 32768.0
            tensor      = torch.FloatTensor(audio_float)
            confidence  = self._silero_model(tensor, sample_rate).item()
            return confidence
        except Exception:
            return 0.5

    def is_music(self, audio_path: str) -> float:
        """
        Returns 0.0-1.0 music probability via spectral analysis.
        Music has regular periodic patterns; speech has irregular ones.
        """
        try:
            import librosa
            import numpy as np
            y, _sr = librosa.load(audio_path, sr=16000)

            # Spectral flatness: noise=high, tonal=low
            flatness     = librosa.feature.spectral_flatness(y=y)
            avg_flatness = float(np.mean(flatness))

            # Zero crossing rate: music tends to be lower than noise
            zcr     = librosa.feature.zero_crossing_rate(y)
            avg_zcr = float(np.mean(zcr))

            music_score = max(0.0, 1.0 - avg_flatness * 10 - avg_zcr * 5)
            return min(1.0, music_score)
        except Exception:
            return 0.0

    # ─── Transcription ────────────────────────────────────────────────────────

    def transcribe_fast(self, audio_path: str) -> str:
        """
        faster-whisper transcription with built-in VAD filter.
        Falls back to regular Whisper via VoiceEngine reference.
        """
        if self._faster_whisper is None:
            self.load_faster_whisper()

        if self._faster_whisper:
            try:
                segments, _info = self._faster_whisper.transcribe(
                    audio_path,
                    beam_size=1,       # faster, slightly lower accuracy
                    language='en',
                    vad_filter=True,   # built-in silence removal
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                text = ' '.join(seg.text for seg in segments).strip()
                if text:
                    return text
            except Exception as e:
                print(f'[Voice] faster-whisper error: {e}')

        # Fallback to regular whisper via VoiceEngine
        if self._ve:
            return self._ve.transcribe(audio_path)
        return ''

    # ─── Speech classification ────────────────────────────────────────────────

    def classify_speech(
        self,
        text: str,
        audio_confidence: float = 1.0,
    ) -> str:
        """Classify what type of communication this transcribed text is."""
        if not text or len(text.strip()) < 2:
            return SpeechClassification.SILENCE

        text_lower = text.lower().strip()
        words      = text_lower.split()

        # Singing: repetitive rhythm words
        singing_indicators = [
            'la la', 'na na', 'oh oh', 'yeah yeah',
            'mm mm', 'hey hey', 'whoa', 'da da',
        ]
        if any(s in text_lower for s in singing_indicators):
            return SpeechClassification.SINGING

        # Very short utterances starting with filler = mid-thought
        thinking_starters = [
            'uh', 'um', 'hmm', 'hm', 'ah', 'like', 'so',
            'and', 'but', 'i mean', 'you know', 'i think',
            'maybe', 'i wonder', 'interesting',
        ]
        if len(words) <= 4 and any(
            text_lower.startswith(i) for i in thinking_starters
        ):
            return SpeechClassification.THINKING_ALOUD

        # Thinking aloud patterns
        thinking_patterns = [
            'i wonder', 'hmm', 'interesting', 'wow', 'crazy',
            'damn', 'wild', 'no way', 'seriously', 'oh wow',
            'wait what', 'huh',
        ]
        if any(text_lower.startswith(p) for p in thinking_patterns):
            return SpeechClassification.THINKING_ALOUD

        # Command: starts with action verb
        command_starters = {
            'do', 'run', 'start', 'stop', 'show', 'find', 'get',
            'send', 'create', 'build', 'write', 'make', 'generate',
            'pull', 'draft', 'schedule', 'book', 'cancel', 'open',
            'close', 'check',
        }
        if words and words[0] in command_starters:
            return SpeechClassification.COMMAND

        # Question: starts with question word or ends with ?
        question_starters = {
            'what', 'why', 'how', 'when', 'where', 'who', 'which',
            'should', 'can', 'could', 'would', 'is', 'are', 'do',
            'does', 'will', 'was', 'were', 'have', 'has',
        }
        if (words and words[0] in question_starters) or text_lower.endswith('?'):
            return SpeechClassification.QUESTION

        return SpeechClassification.CONVERSATION

    def is_utterance_complete(self, text: str) -> bool:
        """Determines if an utterance is complete or if the speaker is mid-thought."""
        if not text:
            return False

        text_stripped = text.strip()

        # Ends with punctuation = complete
        if text_stripped.endswith(('.', '?', '!', '...')):
            return True

        # Trailing continuation words = incomplete
        continuation_words = {
            'and', 'but', 'so', 'because', 'like', 'the', 'a', 'an',
            'to', 'for', 'of', 'in', 'on', 'at', 'with', 'that', 'i',
        }
        last_word = text_stripped.lower().split()[-1] if text_stripped.split() else ''
        if last_word in continuation_words:
            return False

        # 3+ words without trailing continuation = probably complete
        if len(text_stripped.split()) >= 3:
            return True

        return False

    # ─── Meeting auto-detection ───────────────────────────────────────────────

    def detect_meeting_context(
        self,
        text: str,
        recent_context: list,
    ) -> dict | None:
        """
        Detects meeting situations from natural language cues.
        No explicit trigger phrases needed — infers from conversation content.
        """
        text_lower = text.lower()

        meeting_cues: dict[str, list[str]] = {
            'sales_call': [
                'on the line', 'introduce', 'tell me about', 'what brings you',
                'how can i help', 'the offer', 'what does it cost', 'tell them',
                'ask them', 'the client',
            ],
            'strategy_session': [
                "let's think through", 'strategy', "what's the plan",
                'thinking about', 'direction', 'pivot', 'opportunity',
            ],
            'team_standup': [
                'what did you work on', 'blockers', 'what are you working on today',
                'team update', 'progress',
            ],
        }

        for meeting_type, cues in meeting_cues.items():
            if any(cue in text_lower for cue in cues):
                return {'type': meeting_type, 'confidence': 0.7}

        return None

    # ─── Context window ───────────────────────────────────────────────────────

    def add_to_context(
        self,
        utterance: str,
        classification: str,
        response: str = '',
    ) -> None:
        self.context_window.append({
            'utterance':      utterance,
            'classification': classification,
            'response':       response,
            'timestamp':      datetime.now().isoformat(),
        })

    def get_context_summary(self) -> str:
        """Returns recent conversation context for response continuity."""
        if not self.context_window:
            return ''
        recent = list(self.context_window)[-5:]
        lines  = ['Recent conversation:']
        for item in recent:
            lines.append(f"You: {item['utterance'][:100]}")
            if item['response']:
                lines.append(f"DEX: {item['response'][:100]}")
        return '\n'.join(lines)


# ─── Legacy VAD processor (webrtcvad — kept as fallback) ──────────────────────

class VADProcessor:
    """
    webrtcvad-based Voice Activity Detection.
    Used as fallback when Silero VAD is unavailable.
    """

    def __init__(self, aggressiveness: int = 2) -> None:
        import webrtcvad
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate   = 16000
        self.frame_duration = 30   # ms per frame
        self.frame_size    = int(self.sample_rate * self.frame_duration / 1000) * 2
        self._wav_sample_rate: int = self.sample_rate

    def is_speech(self, audio_chunk: bytes, sample_rate: int | None = None) -> bool:
        try:
            sr = sample_rate if sample_rate is not None else self.sample_rate
            return self.vad.is_speech(audio_chunk, sr)
        except Exception:
            return False

    def extract_speech_segments(self, audio_path: str) -> list[bytes]:
        segments: list[bytes] = []
        try:
            with wave.open(audio_path, 'rb') as wf:
                frames      = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()

            self._wav_sample_rate = sample_rate
            frame_size = int(sample_rate * self.frame_duration / 1000) * 2

            speech_frames: list[bytes] = []
            is_speaking   = False
            silence_count = 0
            silence_threshold = 10

            offset = 0
            while offset + frame_size <= len(frames):
                frame   = frames[offset:offset + frame_size]
                offset += frame_size

                if self.is_speech(frame, sample_rate):
                    speech_frames.append(frame)
                    is_speaking   = True
                    silence_count = 0
                elif is_speaking:
                    silence_count += 1
                    speech_frames.append(frame)
                    if silence_count > silence_threshold:
                        if len(speech_frames) > 20:
                            segments.append(b''.join(speech_frames))
                        speech_frames = []
                        is_speaking   = False
                        silence_count = 0

            if speech_frames and len(speech_frames) > 20:
                segments.append(b''.join(speech_frames))

        except Exception as e:
            print(f'[VAD] Error: {e}')

        return segments

    def save_segment(self, segment: bytes, path: str) -> bool:
        try:
            with wave.open(path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._wav_sample_rate)
                wf.writeframes(segment)
            return True
        except Exception:
            return False


# ─── VoiceEngine ──────────────────────────────────────────────────────────────

class VoiceEngine:

    def __init__(self) -> None:
        self._whisper_model = None
        self._tts_model     = None
        self.ollama_model   = 'qwen2.5:3b'
        self._ollama_url    = 'http://localhost:11434/api/generate'
        self.intelligent    = IntelligentVoiceProcessor(voice_engine=self)
        self.vad            = VADProcessor()

    # ─── Speech to text ───────────────────────────────────────────────────────

    def load_whisper(self, model_size: str = 'base') -> bool:
        """
        Load Whisper model into memory.

        Sizes and trade-offs:
          tiny   — fastest, lower accuracy (~1 GB VRAM)
          base   — good balance, ~1 GB VRAM  ← default
          small  — better accuracy, ~2 GB VRAM
          medium — near-human accuracy, ~5 GB VRAM
          large  — best accuracy, ~10 GB VRAM
        """
        try:
            import whisper
            self._whisper_model = whisper.load_model(model_size)
            print(f'[VoiceEngine] Whisper {model_size} loaded')
            return True
        except Exception as e:
            print(f'[VoiceEngine] Whisper load failed: {e}')
            return False

    def transcribe(self, audio_path: str) -> str:
        """Convert audio file to text. Lazy-loads Whisper on first call."""
        if not self._whisper_model:
            self.load_whisper()
        try:
            result = self._whisper_model.transcribe(audio_path)
            text   = result.get('text', '').strip()
            print(f'[VoiceEngine] Transcribed: {text[:80]!r}')
            return text
        except Exception as e:
            print(f'[VoiceEngine] Transcribe failed: {e}')
            return ''

    def transcribe_with_vad(self, audio_path: str) -> list[str]:
        """
        Transcribes only speech segments (webrtcvad fallback path).
        Returns list of transcribed utterances — silence filtered.
        Prefer intelligent.transcribe_fast() for real-time use.
        """
        segments = self.vad.extract_speech_segments(audio_path)
        if not segments:
            return []

        transcriptions: list[str] = []
        for segment in segments:
            seg_path = tempfile.mktemp(suffix='.wav')
            if self.vad.save_segment(segment, seg_path):
                text = self.transcribe(seg_path)
                if text and len(text.strip()) > 3:
                    transcriptions.append(text.strip())
                try:
                    os.remove(seg_path)
                except Exception:
                    pass

        return transcriptions

    # ─── Smart response gating ────────────────────────────────────────────────

    def should_respond(
        self,
        text: str,
        music_score: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Returns (should_respond, classification).
        Suppresses response for thinking aloud, singing, music, and silence.
        """
        if music_score > 0.6:
            return False, SpeechClassification.MUSIC_BACKGROUND

        classification = self.intelligent.classify_speech(text)

        should = classification not in {
            SpeechClassification.THINKING_ALOUD,
            SpeechClassification.SINGING,
            SpeechClassification.MUSIC_BACKGROUND,
            SpeechClassification.SILENCE,
        }
        return should, classification

    # ─── Text to speech ───────────────────────────────────────────────────────

    def speak(self, text: str, output_path: str | None = None) -> str:
        """
        Convert text to a WAV audio file.

        Tries Coqui TTS first; falls back to espeak (always available).
        Returns path to the generated audio file, or empty string on failure.
        """
        if not output_path:
            output_path = tempfile.mktemp(suffix='.wav')

        text = text[:500]

        # Primary: Coqui TTS (higher quality)
        try:
            from TTS.api import TTS  # type: ignore[import]
            if self._tts_model is None:
                self._tts_model = TTS('tts_models/en/ljspeech/tacotron2-DDC')
            self._tts_model.tts_to_file(text=text, file_path=output_path)
            print(f'[VoiceEngine] Coqui TTS → {output_path}')
            return output_path
        except Exception:
            pass

        # Fallback: espeak
        try:
            result = subprocess.run(
                ['espeak', '-w', output_path, text],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0 and Path(output_path).exists():
                print(f'[VoiceEngine] espeak → {output_path}')
                return output_path
        except FileNotFoundError:
            print('[VoiceEngine] espeak not found — install with: apt-get install espeak')
        except Exception as e:
            print(f'[VoiceEngine] TTS failed: {e}')

        return ''

    # ─── Local LLM (Ollama / Qwen2.5) ────────────────────────────────────────

    def query_local(self, prompt: str, system: str | None = None) -> str:
        """
        Query Qwen2.5:3b locally via Ollama.

        Free and fast — no Anthropic API cost. Use for simple/quick queries.
        Returns empty string if Ollama is not running.
        """
        import requests

        system_msg = system or (
            'You are DEX. Executive Assistant to Antony F. Munoz, '
            'founder of Munoz Conglomerate. '
            'You talk like a sharp always-on operator — not corporate, not formal. '
            'Current stage: Stage 1. Focus: get first sale, $750 Initiate Arena. '
            'ICP: men 18-25, Instagram. North star: $10K/month net. '
            'Never say "Hello, I\'m DEX, your AI business assistant." '
            'Never say "Let\'s schedule a call to discuss." '
            'When greeted, say what matters right now. Short. Direct. '
            'Example response to "hey": '
            '"Stage 1. First sale is the target. What do you need?"'
        )
        payload = {
            'model':  self.ollama_model,
            'prompt': prompt,
            'system': system_msg,
            'stream': False,
        }
        try:
            resp = requests.post(self._ollama_url, json=payload, timeout=30)
            if resp.status_code == 200:
                response = resp.json().get('response', '')
                print(f'[VoiceEngine] Ollama: {response[:80]!r}')
                return response
            else:
                print(f'[VoiceEngine] Ollama HTTP {resp.status_code}')
        except requests.exceptions.ConnectionError:
            print('[VoiceEngine] Ollama not running — start with: ollama serve')
        except Exception as e:
            print(f'[VoiceEngine] Ollama error: {e}')
        return ''

    # ─── Query classification ─────────────────────────────────────────────────

    def is_simple_query(self, text: str) -> bool:
        """Determine if query can be handled locally (Ollama) vs Claude (EOS)."""
        simple_patterns = [
            'what time', 'how many', 'status', 'quick', 'remind me',
            'what is', 'define', 'simple', 'yes or no', 'list',
            'show me', 'count', 'what day', 'when is', 'how do i',
        ]
        text_lower = text.lower()
        if len(text.split()) <= 6:
            return True
        return any(p in text_lower for p in simple_patterns)

    # ─── Smart routing ────────────────────────────────────────────────────────

    def route_query(self, text: str, ctx=None) -> str:
        """Route query to right inference backend."""
        if self.is_simple_query(text):
            local = self.query_local(text)
            if local:
                return local

        if ctx is not None:
            try:
                from eos_ai.gateway import EOSGateway
                gw     = EOSGateway()
                result = gw.handle({'type': 'agent_task', 'prompt': text})
                output = result.get('output') or result.get('brief') or ''
                if output:
                    return output
            except Exception as e:
                print(f'[VoiceEngine] Gateway error: {e}')

        return self.query_local(text)

    # ─── Convenience ─────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        """Check if Ollama is reachable."""
        import requests
        try:
            resp = requests.get('http://localhost:11434/api/tags', timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
