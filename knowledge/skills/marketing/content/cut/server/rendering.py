"""Rendering — caption regeneration (A4), the render job, CMX3600 export.

The render worker builds the ffmpeg command through `cutter.build_filter`
(one filter-graph definition, shared with the Phase 1 CLI) but executes it
via `gated_subprocess_run`: the CPU Gate Law forbids raw subprocess in
service code, and `cutter.cut` is the un-gated CLI path.

Caption correctness is the subtle part. The source SRT describes the
UNCUT timeline; after cutting, every cue must be re-timed to the OUTPUT
timeline. A4 does that from the kept words, which is why captions stay
locked to speech no matter how much is removed.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from substrate.execution.cpu_gate import gated_subprocess_run

from .registry import gate_failure_detail

logger = logging.getLogger("cutstudio.rendering")

MAX_CUE_WORDS = 7
MAX_CUE_SECONDS = 2.8
RENDER_TIMEOUT = 1800

VALID_ASPECTS = ("source", "9:16", "1:1", "16:9")

_cut_pkg_dir = Path(__file__).resolve().parent.parent


def _load_sibling(name: str):
    """Import a Phase 1 module by path.

    `cutter.py` and `edl.py` do `from edl import ...` — a module-local import
    that only resolves when the cut directory is on sys.path. Loading them by
    spec (with the directory injected) keeps that Phase 1 idiom working
    without permanently polluting the service's import path.
    """
    import sys

    if str(_cut_pkg_dir) not in sys.path:
        sys.path.insert(0, str(_cut_pkg_dir))
    spec = importlib.util.spec_from_file_location(
        "cutstudio_%s" % name, _cut_pkg_dir / ("%s.py" % name)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def get_cutter():
    return _load_sibling("cutter")


def get_edl_module():
    return _load_sibling("edl")


# ── A4: SRT regeneration from kept words ─────────────────────────────────
def _fmt_ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def regenerate_srt(edl: dict, words: list[dict], dest: Path) -> Path | None:
    """Write an SRT timed to the OUTPUT timeline of `edl`.

    For each clip, take the words inside it and shift them by the offset
    between where the clip sits in the source and where it lands in the
    output. Cues break at 7 words or 2.8 seconds, whichever comes first.
    """
    cues: list[tuple[float, float, str]] = []
    elapsed = 0.0
    for clip in edl.get("clips") or []:
        c_start, c_end = float(clip["start"]), float(clip["end"])
        shift = elapsed - c_start
        inside = [w for w in words if c_start <= float(w["start"]) < c_end]
        group: list[dict] = []
        for w in inside:
            if group:
                span = float(w["end"]) - float(group[0]["start"])
                if len(group) >= MAX_CUE_WORDS or span > MAX_CUE_SECONDS:
                    cues.append(_make_cue(group, shift))
                    group = []
            group.append(w)
        if group:
            cues.append(_make_cue(group, shift))
        elapsed += c_end - c_start

    if not cues:
        return None
    lines: list[str] = []
    for i, (start, end, text) in enumerate(cues, 1):
        lines += [str(i), "%s --> %s" % (_fmt_ts(start), _fmt_ts(end)), text, ""]
    dest.write_text("\n".join(lines))
    return dest


def _make_cue(group: list[dict], shift: float) -> tuple[float, float, str]:
    text = " ".join((w.get("word") or "").strip() for w in group).strip()
    return (float(group[0]["start"]) + shift, float(group[-1]["end"]) + shift, text)


# ── render job ───────────────────────────────────────────────────────────
def build_render_edl(
    edl: dict, source: Path, output_name: str, captions: bool, clip: dict | None
) -> dict:
    """Produce the EDL actually handed to ffmpeg.

    `clip` (a highlight candidate) replaces the timeline with that single
    range — the same code path renders a full cut and a 45-second short.
    """
    render_edl = dict(edl)
    render_edl["source"] = str(source)
    render_edl["output"] = output_name
    render_edl["captions"] = bool(captions)
    if clip:
        render_edl["clips"] = [
            {
                "start": round(float(clip["start"]), 3),
                "end": round(float(clip["end"]), 3),
                "label": str(clip.get("label") or "highlight")[:60],
            }
        ]
    return render_edl


def render(
    edl: dict,
    source: Path,
    out_dir: Path,
    output_name: str,
    words: list[dict],
    aspect: str = "source",
    captions: bool = False,
    caption_style: int = 1,
    clean_audio: bool = False,
    clip: dict | None = None,
    job=None,
) -> dict:
    """Render an EDL to `out_dir/output_name`. Returns artifact metadata."""
    if aspect not in VALID_ASPECTS:
        raise ValueError("unsupported aspect: %s" % aspect)
    cutter = get_cutter()
    edl_module = get_edl_module()

    render_edl = build_render_edl(edl, source, output_name, captions, clip)
    render_edl = edl_module.validate(render_edl)

    srt_path = None
    if captions and words:
        srt_path = regenerate_srt(render_edl, words, out_dir / (Path(output_name).stem + ".srt"))

    graph, (vmap, amap) = cutter.build_filter(
        render_edl,
        str(srt_path) if srt_path else None,
        aspect,
        caption_style,
        clean_audio,
    )
    out_path = out_dir / output_name
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        graph,
        "-map",
        vmap,
        "-map",
        amap,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(out_path),
    ]
    if job is not None:
        job.progress = 0.1
    result = gated_subprocess_run(cmd, caller="cutstudio.render", timeout=RENDER_TIMEOUT)
    if result is None:
        raise RuntimeError(gate_failure_detail("cutstudio.render"))
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed (%d): %s" % (result.returncode, (result.stderr or "")[-400:])
        )

    return {
        "output": output_name,
        "path": str(out_path),
        "srt": str(srt_path) if srt_path else None,
        "aspect": aspect,
        "captions": bool(captions),
        "caption_style": int(caption_style),
        "clean_audio": bool(clean_audio),
        "duration": round(sum(float(c["end"]) - float(c["start"]) for c in render_edl["clips"]), 3),
        "size": out_path.stat().st_size if out_path.exists() else 0,
    }


# ── CMX3600 export (feature 10b) ─────────────────────────────────────────
def _tc(seconds: float, fps: float) -> str:
    """Seconds -> HH:MM:SS:FF at `fps` (non-drop)."""
    fps = fps if fps and fps > 0 else 30.0
    total_frames = int(round(max(0.0, seconds) * fps))
    frames_per_hour = int(round(fps * 3600))
    frames_per_min = int(round(fps * 60))
    frames_per_sec = int(round(fps))
    h, rem = divmod(total_frames, frames_per_hour)
    m, rem = divmod(rem, frames_per_min)
    s, f = divmod(rem, frames_per_sec)
    return "%02d:%02d:%02d:%02d" % (h, m, s, f)


def to_cmx3600(edl: dict, project_name: str, fps: float) -> str:
    """Serialize an EDL as a CMX3600 list — the NLE escape hatch.

    One `AX V C` event per clip: source in/out from the EDL, record in/out
    accumulating along the output timeline, so Premiere or Resolve opens the
    cut with every clip already in order.
    """
    lines = ["TITLE: %s" % (project_name or "CutStudio")[:70], "FCM: NON-DROP FRAME", ""]
    record = 0.0
    for i, clip in enumerate(edl.get("clips") or [], 1):
        start, end = float(clip["start"]), float(clip["end"])
        length = end - start
        lines.append(
            "%03d  AX       V     C        %s %s %s %s"
            % (
                i,
                _tc(start, fps),
                _tc(end, fps),
                _tc(record, fps),
                _tc(record + length, fps),
            )
        )
        label = clip.get("label")
        if label:
            lines.append("* FROM CLIP NAME: %s" % str(label)[:60])
        record += length
    return "\n".join(lines) + "\n"


# ── Beast dispatch hook (v2) ─────────────────────────────────────────────
def beast_available() -> bool:
    """Whether heavy renders can be dispatched to the GPU node.

    v1 always renders locally; the toggle exists so the UI contract is
    stable when the dispatch lands (scripts/beast_remotion_render.sh is the
    transfer pattern to follow).
    """
    return False
