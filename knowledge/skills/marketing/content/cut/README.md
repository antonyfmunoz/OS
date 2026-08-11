# CUT — transcript-based video editing pipeline

An edit is a text file. Everything speaks **EDL** (`edl.py`): Claude writes
one from a transcript, the Phase 2 UI edits one on a timeline, `cutter.py`
executes one with ffmpeg. Versionable, diffable, regenerable.

## Phase 1 (BUILT, proven 2026-08-10)

```
video in ──> transcribe.py ──> transcript.json + .srt
                                     │
        editor (Claude or human) ────┤  writes EDL json
                                     ▼
             cutter.py <edl.json> ──> cut mp4 (concat, vertical, captions)
```

- `transcribe.py <media> [model]` — faster-whisper, word timestamps, SRT
- `edl.py` — schema v1 + validation (THE contract; Phase 2 UI speaks this)
- `cutter.py <edl.json> [out_dir]` — single-pass ffmpeg filter graph:
  frame-accurate trims → interleaved concat → optional 9:16 crop → burned subs

Proof: `tests/` — 16s espeak VOD → 2-clip EDL → 8.67s 1080×1920 captioned cut.

## Where things run (node roles)
- Short clips + transcription: VPS (faster-whisper + ffmpeg installed)
- Long VODs + renders at scale: Beast (`scripts/beast_remotion_render.sh`
  shows the ssh + base64 transfer pattern; scp cannot parse the Beast username)
- Remotion (installed on Beast) wraps cuts in branded shells when needed

## The editing workflow (chat mode, today)
1. `python3 transcribe.py vod.mp4`
2. Ask Claude: "cut this down to the 3 strongest segments, vertical, captions"
   — Claude reads the transcript, writes the EDL, runs cutter
3. Review, say what to change; the EDL is revised and re-rendered in seconds

## Phase 2 (PLANNED — see PHASE2_UI_PLAN.md)
CutStudio: browser UI for team members — strike text to cut video,
timeline strip, preview, chat-to-edit. Execution = application of the plan.

## Gotchas
- ffmpeg concat requires INTERLEAVED pair labels `[v0][a0][v1][a1]` —
  grouped labels fail with "Media type mismatch" (hit and fixed in v0)
- espeak + whisper `base` garbles robotic speech; real voice transcribes far
  better. Use `small` model when accuracy matters
- `subtitles=` filter path needs `:` escaped; style via `force_style`
- EDL `output` is a bare filename by design — the executor owns directories
