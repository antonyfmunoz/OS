"""Transcription worker (D5) — CutStudio's OWN whisper instance.

Deliberately NOT the voice warm singleton: that engine is tuned for short
conversational turns (`base`, beam_size=1, language pinned) and holds no
transcription lock, so a 40-minute VOD sharing it would block live voice.
CutStudio loads its own model, lazily, and the registry's transcribe lane
(1 worker) is what serializes access to it.

Audio is extracted to 16kHz mono wav first — whisper resamples anyway, and
decoding a small wav is much faster than seeking a large container.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from substrate.execution.cpu_gate import gated_subprocess_run

from .registry import gate_failure_detail

logger = logging.getLogger("cutstudio.transcription")

_model = None
_model_name: str | None = None
_model_lock = threading.Lock()


def _fmt_ts(seconds: float) -> str:
    """SRT timestamp — same formatter as Phase 1 transcribe.py."""
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def get_model(model_size: str):
    """Load (once) and return the CutStudio WhisperModel."""
    global _model, _model_name
    with _model_lock:
        if _model is None or _model_name != model_size:
            from faster_whisper import WhisperModel

            logger.info("loading whisper model %s (cpu/int8)", model_size)
            _model = WhisperModel(model_size, device="cpu", compute_type="int8")
            _model_name = model_size
        return _model


def extract_audio(media: Path, dest: Path) -> None:
    """Gated ffmpeg audio extraction to 16kHz mono wav."""
    result = gated_subprocess_run(
        ["ffmpeg", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(dest)],
        caller="cutstudio.extract_audio",
        timeout=1800,
    )
    if result is None:
        raise RuntimeError(gate_failure_detail("cutstudio.extract_audio"))
    if result.returncode != 0:
        raise RuntimeError("audio extraction failed: %s" % (result.stderr or "")[-400:])


def transcribe_project(
    media: Path, out_dir: Path, model_size: str, duration: float, job=None
) -> dict:
    """Transcribe `media`, writing transcript.json and <media>.srt into
    `out_dir`. Returns the transcript dict.

    Shapes match Phase 1 transcribe.py exactly so edl.py, cutter.py, and any
    existing consumer read them without a translation layer.
    """
    audio = out_dir / "audio_16k.wav"
    extract_audio(media, audio)
    try:
        model = get_model(model_size)
        segments_iter, info = model.transcribe(
            str(audio),
            beam_size=5,
            language=None,
            word_timestamps=True,
            vad_filter=True,
        )

        total = duration or float(getattr(info, "duration", 0.0) or 0.0)
        segments = []
        for seg in segments_iter:
            segments.append(
                {
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": (seg.text or "").strip(),
                    "words": [
                        {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word}
                        for w in (seg.words or [])
                    ],
                }
            )
            if job is not None and total > 0:
                job.progress = min(0.99, round(seg.end / total, 3))

        transcript = {
            "media": str(media),
            "language": getattr(info, "language", "") or "",
            "duration": round(float(getattr(info, "duration", 0.0) or total), 3),
            "segments": segments,
        }
    finally:
        audio.unlink(missing_ok=True)

    (out_dir / "transcript.json").write_text(json.dumps(transcript, indent=1))
    write_srt(transcript["segments"], out_dir / (media.stem + ".srt"))
    logger.info("transcribed %s: %d segments", media.name, len(transcript["segments"]))
    return transcript


def write_srt(segments: list[dict], path: Path) -> Path:
    """Write segment-level SRT (the caption source for un-cut renders)."""
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        lines += [
            str(i),
            "%s --> %s" % (_fmt_ts(seg["start"]), _fmt_ts(seg["end"])),
            seg.get("text", ""),
            "",
        ]
    path.write_text("\n".join(lines))
    return path


def all_words(transcript: dict) -> list[dict]:
    """Flatten every word across segments, carrying its segment index."""
    words: list[dict] = []
    for si, seg in enumerate(transcript.get("segments") or []):
        for w in seg.get("words") or []:
            words.append(
                {
                    "seg": si,
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0)),
                    "word": w.get("word", ""),
                }
            )
    words.sort(key=lambda w: w["start"])
    return words
