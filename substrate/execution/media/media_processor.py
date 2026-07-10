"""
MediaProcessor — unified multimodal file handler.

Routes files to the right backend:
  - voice/audio  → faster-whisper (local, always)
  - image        → Gemini 2.0 Flash (requires GEMINI_API_KEY)
  - video        → Gemini 2.0 Flash (requires GEMINI_API_KEY)
  - document     → Gemini 2.0 Flash (requires GEMINI_API_KEY)

Video intelligence (v2):
  - URL download via yt-dlp (YouTube, TikTok, X, Instagram, direct)
  - Intelligent frame extraction (scene-change, keyframe, targeted)
  - Transcript extraction (captions + Whisper fallback)
  - Combined analysis: Gemini vision + transcript + key frames

Embeddings: Google Text Embedding 004 (768-dim) when key available.
"""

from __future__ import annotations

import glob as _glob_mod
import json as _json
import logging
import re as _re
import shutil
from pathlib import Path
from dotenv import load_dotenv as _load_dotenv

_ROOT = Path(__file__).parent.parent
_load_dotenv(_ROOT / "services" / ".env")
_load_dotenv(_ROOT / "runtime" / ".env", override=False)
from substrate.execution.cpu_gate import gated_subprocess_run, gated_popen

try:
    import google.genai as genai
    from google.genai import types as genai_types

    _GENAI_NEW = True
except ImportError:
    import google.generativeai as genai  # type: ignore[no-redef]

    genai_types = None
    _GENAI_NEW = False

import os, tempfile, subprocess, base64

_logger = logging.getLogger(__name__)

_VIDEO_TMP_DIR = "/tmp/umh_video"

SUPPORTED = {
    "video": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp", ".flv"],
    "audio": [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus"],
    "document": [".pdf", ".txt", ".md", ".docx", ".csv", ".html", ".rtf"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"],
}

MIME_MAP = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".csv": "text/csv",
    ".html": "text/html",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

DEFAULT_PROMPTS = {
    "video": (
        "Watch this video carefully. Identify: "
        "(1) what is happening, "
        "(2) any competitor content or tactics, "
        "(3) ICP signals or language patterns, "
        "(4) actionable insights for the business. "
        "Be specific."
    ),
    "image": (
        "Analyze this image. Identify anything "
        "relevant to the businesses — competitor "
        "content, market signals, design patterns, "
        "performance data, or actionable insights."
    ),
    "document": (
        "Read this document completely. Provide: "
        "1) concise summary, "
        "2) key facts and data points, "
        "3) actionable insights relevant to the "
        "businesses, "
        "4) any risks or opportunities."
    ),
    "audio": "Transcribe this audio accurately.",
    "voice": "Transcribe this voice message.",
}


class MediaProcessor:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        if key:
            if _GENAI_NEW:
                self._client = genai.Client(api_key=key)
                self.model = "gemini-2.0-flash"
            else:
                genai.configure(api_key=key)
                self._client = None
                self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.available = True
        else:
            self.available = False
            self._client = None
            self.model = None

    def detect_modality(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        for modality, exts in SUPPORTED.items():
            if ext in exts:
                return modality
        return "unknown"

    def process(
        self,
        file_path: str,
        modality: str | None = None,
        user_prompt: str = "",
        business_context: str = "",
    ) -> str:

        downloaded_path: str | None = None
        url_metadata: dict = {}

        if file_path.startswith(("http://", "https://")):
            try:
                downloaded_path, url_metadata = self.download_from_url(
                    file_path,
                )
                file_path = downloaded_path
                if not modality:
                    modality = "video"
            except Exception as exc:
                _logger.warning("URL download failed: %s", exc)
                return f"Failed to download video from URL: {exc}"

        if not modality:
            modality = self.detect_modality(file_path)

        if modality == "unknown":
            return f"Unsupported file type: {Path(file_path).suffix}"

        # voice/audio: always use local Whisper even if Gemini available
        if modality in ("voice", "audio"):
            transcript = self._local_transcribe(file_path)
            if user_prompt and "transcri" not in user_prompt.lower():
                # user wants analysis not just transcript
                full = f"Transcript: {transcript}\n\n{user_prompt}"
                from substrate.sockets.intelligence_port import call_with_fallback

                _routing = call_with_fallback(prompt=full, task_type="fast_response")
                _analysis = _routing.output if _routing else ""
                return f'Transcript: "{transcript}"\n\nAnalysis: {_analysis}'
            return transcript

        if not self.available:
            return (
                "GEMINI_API_KEY not set. "
                "Add to .env to enable "
                "image, video, and document processing."
            )

        prompt = user_prompt or DEFAULT_PROMPTS.get(modality, "Analyze this content.")
        if business_context:
            prompt = f"Business context: {business_context[:300]}\n\n{prompt}"

        try:
            if modality == "image":
                return self._process_image(file_path, prompt)
            elif modality == "video":
                return self._process_video(
                    file_path,
                    prompt,
                    url_metadata=url_metadata,
                )
            elif modality == "document":
                return self._process_document(file_path, prompt)
        finally:
            if downloaded_path:
                self._cleanup_download(downloaded_path)

        return "Could not process file"

    def _process_image(self, path: str, prompt: str) -> str:
        import PIL.Image

        img = PIL.Image.open(path)
        if _GENAI_NEW:
            resp = self._client.models.generate_content(model=self.model, contents=[img, prompt])
        else:
            resp = self.model.generate_content([img, prompt])
        return resp.text

    # ── Video intelligence pipeline ──────────────────────────────────

    def download_from_url(self, url: str) -> tuple[str, dict]:
        """Download a video from a URL via yt-dlp (or urllib for direct links).

        Returns (local_path, metadata_dict).
        """
        os.makedirs(_VIDEO_TMP_DIR, exist_ok=True)
        out_template = os.path.join(
            _VIDEO_TMP_DIR,
            "%(id)s.%(ext)s",
        )

        meta: dict = {}
        meta_result = gated_subprocess_run(
            [
                "yt-dlp",
                "--skip-download",
                "--print-json",
                "--no-warnings",
                url,
            ],
            capture_output=True,
            timeout=30,
            caller="media_processor.download_meta",
        )
        if meta_result and meta_result.returncode == 0:
            try:
                meta = _json.loads(meta_result.stdout)
            except (ValueError, TypeError):
                pass

        dl_result = gated_subprocess_run(
            [
                "yt-dlp",
                "-f",
                "bv*[height<=720]+ba/b[height<=720]/best",
                "-N",
                "4",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang",
                "en",
                "--convert-subs",
                "vtt",
                "--no-playlist",
                "-o",
                out_template,
                url,
            ],
            capture_output=True,
            timeout=300,
            caller="media_processor.download_video",
        )

        if dl_result is None:
            raise RuntimeError("CPU gate blocked video download")

        if dl_result.returncode != 0:
            stderr = (dl_result.stderr or b"").decode(errors="replace")
            if "Unsupported URL" in stderr or "is not a valid URL" in stderr:
                return self._download_direct(url), meta
            raise RuntimeError(f"yt-dlp failed (rc={dl_result.returncode}): {stderr[:300]}")

        video_id = meta.get("id", "")
        found = _glob_mod.glob(os.path.join(_VIDEO_TMP_DIR, f"{video_id}.*"))
        video_files = [f for f in found if not f.endswith((".vtt", ".srt", ".json"))]
        if video_files:
            return video_files[0], meta

        all_files = sorted(
            Path(_VIDEO_TMP_DIR).iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for f in all_files:
            if f.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}:
                return str(f), meta

        raise RuntimeError("yt-dlp succeeded but no video file found")

    def _download_direct(self, url: str) -> str:
        """Fallback for direct video URLs (not social platforms)."""
        import urllib.request

        os.makedirs(_VIDEO_TMP_DIR, exist_ok=True)
        ext = Path(url.split("?")[0]).suffix or ".mp4"
        tmp = tempfile.mktemp(dir=_VIDEO_TMP_DIR, suffix=ext)
        urllib.request.urlretrieve(url, tmp)
        return tmp

    def _cleanup_download(self, path: str) -> None:
        """Remove downloaded video and its sidecar files."""
        try:
            stem = Path(path).stem
            parent = Path(path).parent
            Path(path).unlink(missing_ok=True)
            for sidecar in parent.glob(f"{stem}.*"):
                if sidecar.suffix.lower() in {".vtt", ".srt", ".json"}:
                    sidecar.unlink(missing_ok=True)
        except Exception as exc:
            _logger.debug("cleanup failed: %s", exc)

    def get_video_metadata(self, video_path: str) -> dict:
        """Extract metadata from a local video file via ffprobe."""
        result = gated_subprocess_run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ],
            capture_output=True,
            timeout=30,
            caller="media_processor.ffprobe",
        )
        if result is None or result.returncode != 0:
            return {}

        try:
            data = _json.loads(result.stdout)
        except (ValueError, TypeError):
            return {}

        fmt = data.get("format", {})
        streams = data.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        return {
            "duration": float(fmt.get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "codec": video_stream.get("codec_name", ""),
            "has_audio": has_audio,
            "title": fmt.get("tags", {}).get("title", ""),
        }

    def _extract_transcript(self, video_path: str) -> str:
        """Extract transcript: prefer captions sidecar, fall back to Whisper."""
        stem = Path(video_path).stem
        parent = Path(video_path).parent

        for ext in (".en.vtt", ".vtt", ".en.srt", ".srt"):
            sub_path = parent / f"{stem}{ext}"
            if sub_path.exists():
                return self._parse_subtitle_file(str(sub_path))

        sub_candidates = list(parent.glob(f"{stem}*.vtt")) + list(parent.glob(f"{stem}*.srt"))
        if sub_candidates:
            return self._parse_subtitle_file(str(sub_candidates[0]))

        audio_tmp = tempfile.mktemp(suffix=".wav", dir=_VIDEO_TMP_DIR)
        try:
            result = gated_subprocess_run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    audio_tmp,
                ],
                capture_output=True,
                timeout=120,
                caller="media_processor.extract_audio",
            )
            if result is None or result.returncode != 0:
                return ""
            return self._local_transcribe(audio_tmp)
        finally:
            Path(audio_tmp).unlink(missing_ok=True)

    def _parse_subtitle_file(self, path: str) -> str:
        """Parse VTT/SRT into timestamped text, deduplicating rolling subs."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        is_vtt = path.endswith(".vtt")
        lines_out: list[str] = []
        seen_text: set[str] = set()

        if is_vtt:
            blocks = content.split("\n\n")
            for block in blocks:
                block_lines = block.strip().split("\n")
                timestamp = ""
                text_parts: list[str] = []
                for line in block_lines:
                    if "-->" in line:
                        match = _re.match(
                            r"(\d+:?\d+:\d+)",
                            line.strip(),
                        )
                        if match:
                            timestamp = match.group(1)
                    elif line.strip() and "WEBVTT" not in line:
                        cleaned = _re.sub(r"<[^>]+>", "", line.strip())
                        if cleaned:
                            text_parts.append(cleaned)
                text = " ".join(text_parts)
                if text and text not in seen_text:
                    seen_text.add(text)
                    if timestamp:
                        ts_parts = timestamp.split(":")
                        if len(ts_parts) == 3:
                            m = int(ts_parts[0]) * 60 + int(ts_parts[1])
                            s = int(ts_parts[2].split(".")[0])
                            timestamp = f"{m}:{s:02d}"
                        lines_out.append(f"[{timestamp}] {text}")
                    else:
                        lines_out.append(text)
        else:
            blocks = _re.split(r"\n\s*\n", content)
            for block in blocks:
                block_lines = block.strip().split("\n")
                timestamp = ""
                text_parts = []
                for line in block_lines:
                    if "-->" in line:
                        match = _re.match(
                            r"(\d+:\d+:\d+)",
                            line.strip(),
                        )
                        if match:
                            timestamp = match.group(1)
                    elif line.strip() and not line.strip().isdigit():
                        text_parts.append(line.strip())
                text = " ".join(text_parts)
                if text and text not in seen_text:
                    seen_text.add(text)
                    if timestamp:
                        ts_parts = timestamp.split(":")
                        m = int(ts_parts[0]) * 60 + int(ts_parts[1])
                        s = int(ts_parts[2].split(",")[0])
                        lines_out.append(f"[{m}:{s:02d}] {text}")
                    else:
                        lines_out.append(text)

        return "\n".join(lines_out)

    def extract_frames(
        self,
        video_path: str,
        mode: str = "balanced",
        timestamps: list[float] | None = None,
    ) -> list[str]:
        """Extract key frames from video.

        Modes:
          keyframe  — I-frames only (fast, max 50)
          balanced  — scene-change detection (max auto-scaled by duration)
          targeted  — specific timestamps
        """
        frames_dir = tempfile.mkdtemp(
            prefix="frames_",
            dir=_VIDEO_TMP_DIR,
        )

        if mode == "targeted" and timestamps:
            return self._extract_targeted_frames(
                video_path,
                timestamps,
                frames_dir,
            )

        meta = self.get_video_metadata(video_path)
        duration = meta.get("duration", 0)

        if mode == "keyframe":
            budget = 50
            result = gated_subprocess_run(
                [
                    "ffmpeg",
                    "-y",
                    "-skip_frame",
                    "nokey",
                    "-i",
                    video_path,
                    "-vf",
                    "scale=512:-2",
                    "-qscale:v",
                    "4",
                    "-vsync",
                    "vfr",
                    os.path.join(frames_dir, "%04d.jpg"),
                ],
                capture_output=True,
                timeout=120,
                caller="media_processor.keyframes",
            )
            if result is None or result.returncode != 0:
                return []
            frames = sorted(
                Path(frames_dir).glob("*.jpg"),
            )[:budget]
            return [str(f) for f in frames]

        budget = self._frame_budget(duration)
        result = gated_subprocess_run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vf",
                "select='gt(scene\\,0.20)',scale=512:-2",
                "-qscale:v",
                "4",
                "-vsync",
                "vfr",
                os.path.join(frames_dir, "%04d.jpg"),
            ],
            capture_output=True,
            timeout=180,
            caller="media_processor.scene_detect",
        )
        if result is None or result.returncode != 0:
            return []

        frames = sorted(Path(frames_dir).glob("*.jpg"))

        if len(frames) < 8 and duration > 0:
            shutil.rmtree(frames_dir, ignore_errors=True)
            frames_dir = tempfile.mkdtemp(
                prefix="frames_uniform_",
                dir=_VIDEO_TMP_DIR,
            )
            interval = max(duration / budget, 0.5)
            result = gated_subprocess_run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-vf",
                    f"fps=1/{interval:.2f},scale=512:-2",
                    "-qscale:v",
                    "4",
                    os.path.join(frames_dir, "%04d.jpg"),
                ],
                capture_output=True,
                timeout=180,
                caller="media_processor.uniform_frames",
            )
            if result is None or result.returncode != 0:
                return []
            frames = sorted(Path(frames_dir).glob("*.jpg"))

        deduped = self._dedup_frames([str(f) for f in frames])
        return deduped[:budget]

    def _extract_targeted_frames(
        self,
        video_path: str,
        timestamps: list[float],
        frames_dir: str,
    ) -> list[str]:
        """Extract single frames at specific timestamps."""
        paths: list[str] = []
        for i, ts in enumerate(timestamps):
            out = os.path.join(frames_dir, f"target_{i:04d}.jpg")
            result = gated_subprocess_run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(ts),
                    "-i",
                    video_path,
                    "-vf",
                    "scale=512:-2",
                    "-frames:v",
                    "1",
                    "-qscale:v",
                    "4",
                    out,
                ],
                capture_output=True,
                timeout=30,
                caller="media_processor.targeted_frame",
            )
            if result and result.returncode == 0 and os.path.exists(out):
                paths.append(out)
        return paths

    @staticmethod
    def _frame_budget(duration: float) -> int:
        if duration <= 30:
            return 30
        if duration <= 60:
            return 40
        if duration <= 180:
            return 60
        if duration <= 600:
            return 80
        return 100

    @staticmethod
    def _dedup_frames(paths: list[str]) -> list[str]:
        """Drop near-duplicate frames using 16x16 grayscale thumbnails."""
        try:
            import PIL.Image
            import numpy as np
        except ImportError:
            return paths

        kept: list[str] = []
        last_thumb: "np.ndarray | None" = None

        for p in paths:
            try:
                img = PIL.Image.open(p).convert("L").resize((16, 16))
                thumb = np.array(img, dtype=float)
            except Exception:
                kept.append(p)
                continue

            if last_thumb is not None:
                diff = float(np.mean(np.abs(thumb - last_thumb)))
                if diff <= 2.0:
                    continue

            kept.append(p)
            last_thumb = thumb

        return kept

    def _process_video(
        self,
        path: str,
        prompt: str,
        url_metadata: dict | None = None,
    ) -> str:
        """Enhanced video pipeline: metadata + transcript + frames + Gemini."""
        import time

        meta = url_metadata or {}
        local_meta = self.get_video_metadata(path)
        if local_meta:
            meta = {**meta, **local_meta}

        sections: list[str] = []

        duration = meta.get("duration", 0)
        if meta:
            header_parts = []
            if meta.get("title"):
                header_parts.append(f"Title: {meta['title']}")
            if meta.get("uploader"):
                header_parts.append(f"Creator: {meta['uploader']}")
            if duration:
                mins, secs = divmod(int(duration), 60)
                header_parts.append(f"Duration: {mins}:{secs:02d}")
            if meta.get("width") and meta.get("height"):
                header_parts.append(f"Resolution: {meta['width']}x{meta['height']}")
            if header_parts:
                sections.append("## Video Metadata\n" + "\n".join(header_parts))

        transcript = ""
        try:
            transcript = self._extract_transcript(path)
        except Exception as exc:
            _logger.warning("transcript extraction failed: %s", exc)

        if transcript:
            preview = transcript[:3000]
            if len(transcript) > 3000:
                preview += "\n[...transcript truncated...]"
            sections.append(f"## Transcript\n{preview}")

        frame_paths: list[str] = []
        try:
            frame_paths = self.extract_frames(path, mode="balanced")
        except Exception as exc:
            _logger.warning("frame extraction failed: %s", exc)

        gemini_analysis = ""
        if self.available:
            try:
                gemini_analysis = self._gemini_video_analysis(
                    path,
                    prompt,
                )
            except Exception as exc:
                _logger.warning("Gemini video analysis failed: %s", exc)

        if gemini_analysis:
            sections.append(f"## Visual Analysis\n{gemini_analysis}")

        if frame_paths:
            sections.append(
                f"## Key Frames\n{len(frame_paths)} frames extracted"
                f" to {Path(frame_paths[0]).parent}"
            )

        if not sections:
            return "Could not extract any information from this video."

        return "\n\n".join(sections)

    def _gemini_video_analysis(self, path: str, prompt: str) -> str:
        """Send video to Gemini for visual analysis (original pipeline)."""
        import time

        mime = MIME_MAP.get(Path(path).suffix.lower(), "video/mp4")
        size = os.path.getsize(path)
        if size > 20 * 1024 * 1024:
            if _GENAI_NEW:
                video_file = self._client.files.upload(
                    path=path,
                    config={"mime_type": mime},
                )
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = self._client.files.get(
                        name=video_file.name,
                    )
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=[video_file, prompt],
                )
            else:
                video_file = genai.upload_file(
                    path=path,
                    mime_type=mime,
                )
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = genai.get_file(video_file.name)
                resp = self.model.generate_content(
                    [video_file, prompt],
                )
        else:
            with open(path, "rb") as f:
                data = f.read()
            inline = {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(data).decode(),
                }
            }
            if _GENAI_NEW:
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=[inline, prompt],
                )
            else:
                resp = self.model.generate_content([inline, prompt])
        return resp.text

    def _process_document(self, path: str, prompt: str) -> str:
        import time

        mime = MIME_MAP.get(Path(path).suffix.lower(), "application/pdf")
        if _GENAI_NEW:
            doc_file = self._client.files.upload(
                path=path,
                config={"mime_type": mime},
            )
            while doc_file.state.name == "PROCESSING":
                time.sleep(2)
                doc_file = self._client.files.get(name=doc_file.name)
            resp = self._client.models.generate_content(
                model=self.model, contents=[doc_file, prompt]
            )
        else:
            doc_file = genai.upload_file(path=path, mime_type=mime)
            while doc_file.state.name == "PROCESSING":
                time.sleep(2)
                doc_file = genai.get_file(doc_file.name)
            resp = self.model.generate_content([doc_file, prompt])
        return resp.text

    def _local_transcribe(self, audio_path: str) -> str:
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path)
            return " ".join(s.text for s in segments).strip()
        except ImportError:
            pass
        try:
            import whisper

            m = whisper.load_model("small")
            return m.transcribe(audio_path)["text"].strip()
        except ImportError:
            return "[install faster-whisper: pip install faster-whisper --break-system-packages]"

    def synthesize_speech(
        self,
        text: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Convert text to speech locally.
        Cleans markdown before synthesis.
        Returns path to audio file or None on failure.
        """
        import re

        # clean markdown
        clean = text
        clean = re.sub(r"\*+", "", clean)
        clean = re.sub(r"#+\s*", "", clean)
        clean = re.sub(r"`+[^`]*`+", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"[-•]\s+", "", clean)
        clean = re.sub(r"\n+", " ", clean)
        clean = clean.strip()

        # truncate to reasonable voice length (~500 chars)
        if len(clean) > 500:
            cutoff = clean[:500].rfind(".")
            if cutoff > 200:
                clean = clean[: cutoff + 1]
            else:
                clean = clean[:500] + "..."

        if not output_path:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

        # try pyttsx3 (local, free)
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 0.9)
            voices = engine.getProperty("voices")
            if voices:
                engine.setProperty("voice", voices[0].id)
            engine.save_to_file(clean, output_path)
            engine.runAndWait()
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            print(f"[MediaProcessor] pyttsx3 failed: {e}")

        # fallback: espeak directly via subprocess
        try:
            result = gated_subprocess_run(
                ["espeak", "-w", output_path, "-s", "150", clean],
                capture_output=True,
                timeout=30,
            )
            if (
                result.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                return output_path
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"[MediaProcessor] espeak failed: {e}")

        return None

    def generate_embedding(self, text: str) -> list[float]:
        """
        Google Text Embedding 004 — 768 dimensions.
        Used for semantic memory storage.
        """
        if not self.available:
            return []
        if _GENAI_NEW:
            result = self._client.models.embed_content(
                model="models/text-embedding-004",
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type="retrieval_document",
                ),
            )
            return list(result.embeddings[0].values)
        else:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
