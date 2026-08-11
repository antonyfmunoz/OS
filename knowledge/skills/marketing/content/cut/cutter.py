"""Execute an EDL with ffmpeg: trim, concat, optional vertical crop and
burned captions. Local mode (VPS ffmpeg, fine for short clips) or Beast
mode (heavy VODs — same commands over ssh; see scripts/beast_remotion_render.sh
for the transfer pattern).

The filter graph re-encodes once: trims are frame-accurate, audio stays in
sync, concat is seamless.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

from edl import duration, load, validate  # noqa: F401  (module-local import)


def build_filter(edl: dict, srt_path: str | None) -> tuple:
    """Build the -filter_complex graph for the EDL. Returns (graph, maps)."""
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
    post = "[vc]"
    chain = []
    if edl["vertical"]:
        chain.append("crop=ih*9/16:ih,scale=1080:1920")
    if edl["captions"] and srt_path:
        chain.append("subtitles=%s:force_style='FontSize=16,Outline=1'"
                     % srt_path.replace(":", r"\:").replace("'", r"\'"))
    if chain:
        graph = ";".join(parts) + ";" + concat + ";[vc]%s[vout]" % ",".join(chain)
        maps = ("[vout]", "[ac]")
    else:
        graph = ";".join(parts) + ";" + concat
        maps = ("[vc]", "[ac]")
    return graph, maps


def cut(edl_path: str, out_dir: str = ".") -> Path:
    edl = load(edl_path)
    src = edl["source"]
    if not Path(src).exists():
        raise FileNotFoundError(src)
    srt = None
    if edl["captions"]:
        candidate = Path(src).with_suffix(".srt")
        if candidate.exists():
            srt = str(candidate)
    graph, (vmap, amap) = build_filter(edl, srt)
    out = Path(out_dir) / edl["output"]
    cmd = [
        "ffmpeg", "-y", "-i", src, "-filter_complex", graph,
        "-map", vmap, "-map", amap,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", str(out),
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
