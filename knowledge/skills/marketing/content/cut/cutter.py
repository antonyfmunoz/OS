"""Execute an EDL with ffmpeg: trim, concat, optional aspect crop and
burned captions. Local mode (VPS ffmpeg, fine for short clips) or Beast
mode (heavy VODs — same commands over ssh; see scripts/beast_remotion_render.sh
for the transfer pattern).

The filter graph re-encodes once: trims are frame-accurate, audio stays in
sync, concat is seamless.

Phase 2 adds four keyword arguments to `cut()` — `srt_path`, `aspect`,
`caption_style`, and `clean_audio`. Their defaults reproduce Phase 1
behaviour exactly, so an EDL written before Phase 2 renders identically.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from edl import duration, load, validate  # noqa: F401  (module-local import)

# Aspect filter chains. "source" keeps the input geometry untouched.
ASPECT_FILTERS = {
    "source": None,
    "9:16": "crop=ih*9/16:ih,scale=1080:1920",
    "1:1": "crop=ih:ih,scale=1080:1080",
    "16:9": (
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    ),
}

# Burned-caption presets: 1 clean lower-third, 2 bold centered "shorts", 3 minimal.
CAPTION_STYLES = {
    1: "FontSize=16,Outline=1",
    2: "FontSize=24,Bold=1,Alignment=2,MarginV=60,Outline=2",
    3: "FontSize=12,Outline=0",
}

# Denoise + broadcast loudness normalization (A8).
CLEAN_AUDIO_CHAIN = "afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11"


def _escape_srt(path: str) -> str:
    return path.replace(":", r"\:").replace("'", r"\'")


def build_filter(
    edl: dict,
    srt_path: str | None,
    aspect: str = "source",
    caption_style: int = 1,
    clean_audio: bool = False,
) -> tuple:
    """Build the -filter_complex graph for the EDL. Returns (graph, maps).

    `edl["vertical"]` remains honoured for Phase 1 EDLs: it is treated as
    aspect "9:16" unless an explicit non-source aspect is passed.
    """
    parts, v_labels, a_labels = [], [], []
    for i, c in enumerate(edl["clips"]):
        parts.append(
            "[0:v]trim=start=%(s)s:end=%(e)s,setpts=PTS-STARTPTS[v%(i)d];"
            "[0:a]atrim=start=%(s)s:end=%(e)s,asetpts=PTS-STARTPTS[a%(i)d]"
            % {"s": c["start"], "e": c["end"], "i": i}
        )
        v_labels.append("[v%d]" % i)
        a_labels.append("[a%d]" % i)
    n = len(edl["clips"])
    # concat requires interleaved pairs: [v0][a0][v1][a1]...
    interleaved = "".join(v + a for v, a in zip(v_labels, a_labels))
    concat = "%sconcat=n=%d:v=1:a=1[vc][ac]" % (interleaved, n)

    if aspect == "source" and edl.get("vertical"):
        aspect = "9:16"
    chain = []
    aspect_filter = ASPECT_FILTERS.get(aspect)
    if aspect_filter:
        chain.append(aspect_filter)
    if edl.get("captions") and srt_path:
        style = CAPTION_STYLES.get(int(caption_style), CAPTION_STYLES[1])
        chain.append("subtitles=%s:force_style='%s'" % (_escape_srt(srt_path), style))

    segments = [";".join(parts), concat]
    if chain:
        segments.append("[vc]%s[vout]" % ",".join(chain))
        vmap = "[vout]"
    else:
        vmap = "[vc]"
    if clean_audio:
        segments.append("[ac]%s[aout]" % CLEAN_AUDIO_CHAIN)
        amap = "[aout]"
    else:
        amap = "[ac]"
    return ";".join(segments), (vmap, amap)


def cut(
    edl_path: str,
    out_dir: str = ".",
    srt_path: str | None = None,
    aspect: str = "source",
    caption_style: int = 1,
    clean_audio: bool = False,
) -> Path:
    """Render an EDL to `out_dir`.

    `srt_path` overrides the Phase 1 sidecar lookup — Phase 2 passes a
    caption file regenerated from the KEPT words, which is the only correct
    subtitle track for a cut timeline.
    """
    edl = load(edl_path)
    src = edl["source"]
    if not Path(src).exists():
        raise FileNotFoundError(src)
    srt = srt_path
    if edl["captions"] and srt is None:
        candidate = Path(src).with_suffix(".srt")
        if candidate.exists():
            srt = str(candidate)
    graph, (vmap, amap) = build_filter(edl, srt, aspect, caption_style, clean_audio)
    out = Path(out_dir) / edl["output"]
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src,
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
        str(out),
    ]
    print("[cut] %d clips, %.1fs total -> %s" % (len(edl["clips"]), duration(edl), out))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr[-2000:])
        raise RuntimeError("ffmpeg failed (%d)" % result.returncode)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: cutter.py <edl.json> [out_dir]")
    cut(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
