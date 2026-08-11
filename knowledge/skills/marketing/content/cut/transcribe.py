"""Transcribe a video/audio file with word-level timestamps.

Uses faster-whisper (already deployed on the VPS for voice). Output:
  <stem>.transcript.json  — segments + words with start/end times
  <stem>.srt              — subtitles for caption burning

Short clips run fine on the VPS. For long VODs, extract audio first
(ffmpeg -vn) and consider the Beast — transcription is the heavy stage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def transcribe(media_path: str, model_size: str = "base") -> dict:
    """Run faster-whisper. Returns the transcript dict (also written to disk)."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(media_path, word_timestamps=True)

    segments = []
    for seg in segments_iter:
        segments.append({
            "start": round(seg.start, 3), "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": [
                {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word}
                for w in (seg.words or [])
            ],
        })

    transcript = {
        "media": media_path,
        "language": info.language,
        "duration": round(info.duration, 3),
        "segments": segments,
    }

    stem = Path(media_path).with_suffix("")
    json_path = Path(str(stem) + ".transcript.json")
    json_path.write_text(json.dumps(transcript, indent=1))

    srt_lines = []
    for i, seg in enumerate(segments, 1):
        srt_lines += [str(i), "%s --> %s" % (_fmt_ts(seg["start"]), _fmt_ts(seg["end"])),
                      seg["text"], ""]
    srt_path = Path(str(stem) + ".srt")
    srt_path.write_text("\n".join(srt_lines))

    print("transcript -> %s\nsrt        -> %s" % (json_path, srt_path))
    return transcript


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: transcribe.py <media> [model_size]")
    transcribe(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "base")
