---
name: yt_dlp
description: "Use when downloading audio/video from URLs, extracting metadata from YouTube or other sites, fetching transcripts/subtitles, searching YouTube programmatically, or building media processing pipelines."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/yt-dlp/yt-dlp"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A (CLI + Python library)"
sdk_version: "2026.3.17"
speed_category: slow
trigger: both
effort: medium
context: fork
---

# Tool: yt-dlp

## What This Tool Does

yt-dlp is a feature-rich command-line and Python library for downloading audio/video
from 1800+ websites. It is a maintained fork of youtube-dl with active development,
better performance, and modern site support.

Core capabilities used by EOS:
- **YouTube search** -- search YouTube without an API key via `ytsearchN:query` syntax
- **Metadata extraction** -- `--dump-json` returns full video metadata (title, date, views,
  likes, comments, duration, channel) without downloading
- **Audio extraction** -- `--extract-audio` + `--audio-format mp3` converts video to audio
  for transcription pipelines (Whisper, Groq STT)
- **Subtitle/transcript fetch** -- `--write-auto-subs --sub-lang en --sub-format vtt --skip-download`
  retrieves auto-generated captions without downloading video
- **Format selection** -- `-f bestaudio` or `-f bestvideo+bestaudio` for precise quality control
- **Playlist handling** -- download entire playlists, channels, or search results
- **Cookie auth** -- `--cookies` or `--cookies-from-browser` for age-restricted or private content
- **Rate control** -- `--sleep-requests`, `--limit-rate`, `--sleep-interval` to avoid bans

## EOS Integration

### YouTube research pipeline (last30days skill)
`.agents/skills/last30days/scripts/lib/youtube_yt.py` -- primary integration.
- `search_youtube()` -- runs `yt-dlp ytsearchN:topic --dump-json --no-warnings --no-download`
  via subprocess. Returns parsed video metadata (id, title, url, channel, date, engagement).
- `fetch_transcript()` -- runs `yt-dlp --write-auto-subs --sub-lang en --sub-format vtt --skip-download`
  to get VTT captions, then cleans with `_clean_vtt()` regex pipeline.
- `fetch_transcripts_parallel()` -- ThreadPoolExecutor with max 5 workers for batch transcript fetch.
- `search_and_transcribe()` -- full pipeline: search -> fetch top N transcripts -> attach to results.
- `is_ytdlp_installed()` -- `shutil.which("yt-dlp")` check, gates YouTube source in research runs.

Depth configs control search volume:
```
quick:   10 search / 3 transcripts
default: 20 search / 5 transcripts
deep:    40 search / 8 transcripts
```

### Audio transcription pipeline (apify_scraper.py)
`services/apify_scraper.py:transcribe_video()` -- downloads audio from any video URL:
```python
subprocess.run([
    "yt-dlp", "--quiet", "--extract-audio",
    "--audio-format", "mp3", "--audio-quality", "0",
    "--max-filesize", "10m", "-o", audio_path, video_url,
], capture_output=True, timeout=60)
```
Then feeds to Whisper `small` model for transcription. Used for competitor content analysis.

### Environment detection
`.agents/skills/last30days/scripts/lib/env.py:is_ytdlp_available()` -- auto-detects yt-dlp
in PATH. If missing, YouTube source is skipped with message "yt-dlp not installed".

## Authentication

### No auth required for public content
Public YouTube videos, channels, playlists, and search results need no authentication.
This is how EOS currently uses yt-dlp -- zero API keys, zero tokens.

### Cookie auth for restricted content
Age-restricted or private videos require cookies:
```bash
# From browser cookies (headless servers: export first)
yt-dlp --cookies-from-browser chrome URL

# From exported Netscape cookie file
yt-dlp --cookies /path/to/cookies.txt URL
```
Supported browsers: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale.

### Site-specific login
For sites requiring login (not YouTube -- use cookies for YouTube):
```bash
yt-dlp -u USERNAME -p PASSWORD URL
yt-dlp --netrc URL  # reads ~/.netrc
```

### EOS env vars
None required. yt-dlp is a standalone binary. No API keys in any .env file.

## Quick Reference

### Search YouTube (no API key)
```bash
# Search and dump metadata as JSON lines
yt-dlp "ytsearch20:AI automation 2026" --dump-json --no-download --no-warnings

# Search with date filter
yt-dlp "ytsearch10:topic" --dump-json --no-download --dateafter 20260101
```

### Extract audio for transcription
```bash
# Best quality MP3
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" URL

# Best quality, any format (fastest -- no re-encode)
yt-dlp -f bestaudio -o "%(id)s.%(ext)s" URL
```

### Fetch subtitles/transcripts only
```bash
# Auto-generated English captions
yt-dlp --write-auto-subs --sub-lang en --sub-format vtt --skip-download -o "%(id)s" URL

# All available subtitle languages
yt-dlp --list-subs URL
```

### Get metadata without downloading
```bash
# Full JSON metadata
yt-dlp --dump-json URL

# Specific fields
yt-dlp --print "%(title)s | %(view_count)s views | %(upload_date)s" URL
```

### Python API usage
```python
import yt_dlp

# Extract metadata only
with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
    info = ydl.extract_info(url, download=False)
    print(info['title'], info['view_count'])

# Download best audio
opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '/tmp/%(id)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '0',
    }],
}
with yt_dlp.YoutubeDL(opts) as ydl:
    ydl.download([url])

# Search YouTube
with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
    results = ydl.extract_info(f"ytsearch5:topic", download=False)
    for entry in results['entries']:
        print(entry['title'], entry['url'])
```

### Format selection cheat sheet
```bash
-f bestaudio                    # Best audio only
-f bestvideo+bestaudio          # Best video + best audio (merged)
-f "bestvideo[height<=720]+bestaudio"  # 720p max + best audio
-S "ext:mp4,res:720"            # Prefer mp4, prefer 720p
-f ba -x --audio-format mp3     # Best audio -> convert to mp3
```

## Conceptual Model

```
yt-dlp
  |
  +-- Extractors (1871 sites)
  |     |-- Each site has a dedicated extractor
  |     |-- Extractor returns info_dict with normalized fields
  |     +-- Search extractors: ytsearch, ytsearchdate, etc.
  |
  +-- Format Selection (-f / -S)
  |     |-- Formats ranked by quality, codec, container
  |     |-- Merge: video-only + audio-only via ffmpeg
  |     +-- bestaudio/bestvideo are smart defaults
  |
  +-- Download Engine
  |     |-- HTTP, HLS (m3u8), DASH, RTMP support
  |     |-- Fragment-based with resume capability
  |     |-- Concurrent fragments: -N flag
  |     +-- External downloaders: aria2c, curl, wget
  |
  +-- Post-Processors (require ffmpeg)
  |     |-- ExtractAudio: video -> audio conversion
  |     |-- EmbedSubtitle: burn subs into video
  |     |-- EmbedThumbnail: cover art into audio files
  |     |-- Metadata: embed title/artist/date
  |     +-- SplitChapters: split by chapter markers
  |
  +-- Output Templates
        |-- %(title)s, %(id)s, %(upload_date)s, etc.
        |-- Filesystem-safe: --restrict-filenames
        +-- Nested: %(playlist_title)s/%(title)s.%(ext)s
```

See references/best_practices.md for rate limits, error handling, and anti-patterns.

## Gotchas

### YouTube throttling on VPS IPs
YouTube heavily throttles downloads from datacenter/VPS IP ranges. Downloads that
take 5 seconds locally can take 5 minutes from a VPS. Use `--limit-rate 1M` to avoid
triggering harsher throttling. For metadata-only operations (`--dump-json`, `--skip-download`)
this is not an issue.

### Upload date format is YYYYMMDD not YYYY-MM-DD
`upload_date` in yt-dlp JSON output is `"20260315"` not `"2026-03-15"`. EOS converts
this in `youtube_yt.py` line 172. Always convert when interfacing with date-aware code.

### --dateafter kills search results for evergreen topics
YouTube search returns relevance-sorted results. Adding `--dateafter` causes yt-dlp to
skip videos that don't match, resulting in 0 results for evergreen topics. EOS uses
soft date filtering in Python instead (youtube_yt.py line 191).

### VTT subtitle filenames are unpredictable
yt-dlp may save auto-subs as `{id}.en.vtt`, `{id}.en-orig.vtt`, or other variants.
Always glob for `{id}*.vtt` as fallback (youtube_yt.py line 273).

### subprocess timeout requires process group kill
yt-dlp spawns child processes (ffmpeg). `proc.kill()` only kills the parent.
Use `os.setsid` + `os.killpg` to kill the entire process group (youtube_yt.py line 139).

### --extract-audio requires ffmpeg
The `-x` flag needs ffmpeg installed. Without it, yt-dlp silently fails or errors.
Verify with `which ffmpeg` before using audio extraction features.

### Python API option names differ from CLI flags
CLI: `--extract-audio` -> Python: `'extractaudio': True` (no hyphen).
CLI: `--audio-format mp3` -> Python: `'audioformat': 'mp3'`.
CLI: `--audio-quality 0` -> Python: postprocessor arg, not top-level option.
Always check the source or use postprocessors dict for audio conversion.

### --flat-playlist skips metadata
Using `--flat-playlist` for speed means `upload_date`, `view_count`, and other
fields are missing or None. EOS intentionally does NOT use flat-playlist in
youtube_yt.py to get real dates (line 113 comment).
