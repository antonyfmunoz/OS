# video-cut

Use when asked to cut, trim, clip, caption, or repurpose a video/VOD/recording
("cut this down", "make shorts from this", "clip the stream").

## The system
`knowledge/skills/marketing/content/cut/` — transcript-based editing. An edit
is an EDL json (schema in `edl.py`). Full docs in its README.md.

## Workflow
1. `python3 transcribe.py <video> small` → transcript.json + .srt (word timestamps)
2. READ the transcript (and watch the video via multimodal when judgment matters)
3. Write an EDL: version 1, clips = kept [start,end] ranges cut at word
   boundaries, `vertical` for 9:16, `captions` to burn subs
4. `python3 cutter.py <edl.json> <out_dir>` → verify with ffprobe (duration ≈
   sum of clips, dimensions right)
5. Iterate: revise the EDL from feedback, re-run — seconds per revision

## Where to run
- Short clips + transcription: VPS (ffmpeg + faster-whisper installed)
- Long VODs / bulk renders: Beast via ssh (`scripts/beast_remotion_render.sh`
  has the ssh + base64 transfer pattern — scp cannot parse the Beast username)
- Branded motion-graphic wraps: Remotion on Beast (installed, dispatch proven)

## Verification
Always ffprobe the output (duration, WxH) and spot-check a frame
(`ffmpeg -ss <t> -frames:v 1`) before reporting done.

## Gotchas
- ffmpeg concat labels MUST interleave `[v0][a0][v1][a1]` — grouped fails
- whisper `base` garbles synthetic/robotic speech; use `small` for real voice
- Burned captions must be regenerated from KEPT words when cutting — source
  SRT timings are wrong after a cut (Phase 2 plan documents the algorithm)
- CutStudio UI is PLANNED not built: PHASE2_UI_PLAN.md is one-shot executable
