# yt-dlp -- Creator-Level Best Practices
Source: https://github.com/yt-dlp/yt-dlp
API Version: N/A (CLI + Python library, no REST API)
SDK Version: 2026.3.17
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## Authentication

yt-dlp does not use API keys, OAuth, or tokens. Authentication methods:

**No auth (default):** Public content on all 1871 supported sites requires zero credentials.

**Cookie-based auth (age-restricted / private content):**
```bash
# Export from browser (requires browser on same machine)
yt-dlp --cookies-from-browser chrome URL
yt-dlp --cookies-from-browser firefox:profile_name URL

# From Netscape-format cookie file (server-side)
yt-dlp --cookies /path/to/cookies.txt URL
```
Cookie file format (Netscape/wget):
```
# domain	flag	path	secure	expiry	name	value
.youtube.com	TRUE	/	TRUE	0	SID	value_here
```
Export cookies with browser extensions (e.g., "Get cookies.txt LOCALLY") or
`yt-dlp --cookies-from-browser chrome --cookies export.txt` to dump.

**Site-specific login (non-YouTube):**
```bash
yt-dlp -u USERNAME -p PASSWORD URL
yt-dlp --netrc URL                    # reads ~/.netrc
yt-dlp --netrc-location /path/.netrc URL
```

**EOS auth:** None. All EOS usage is public content. No cookies or credentials stored.
If age-restricted content is needed in future, export cookies to `/opt/OS/secrets/youtube_cookies.txt`
and add `--cookies` flag to subprocess calls.

---

## Core Operations with Exact Signatures

### CLI operations

**Download video (default best quality):**
```bash
yt-dlp URL
# Output: downloads to current dir as {title}.{ext}
```

**Download audio only:**
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 URL
# -x = extract audio (requires ffmpeg)
# --audio-format = target codec: best|aac|alac|flac|m4a|mp3|opus|vorbis|wav
# --audio-quality = 0 (best VBR) to 10 (worst VBR), or "128K" for CBR
```

**Extract metadata (no download):**
```bash
yt-dlp --dump-json URL
# Returns: JSON object with ~100 fields per video
# Key fields: id, title, upload_date (YYYYMMDD), view_count, like_count,
#   comment_count, duration, channel, uploader, description, formats[], thumbnails[]
```

**Search YouTube:**
```bash
yt-dlp "ytsearch10:search terms" --dump-json --no-download
# ytsearchN: = search YouTube, return N results
# ytsearchdateN: = search sorted by upload date
# Output: one JSON object per line (JSONL format)
```

**Fetch subtitles only:**
```bash
yt-dlp --write-auto-subs --sub-lang en --sub-format vtt --skip-download -o "%(id)s" URL
# --write-auto-subs = auto-generated captions
# --write-subs = manually uploaded captions
# --sub-lang = language code(s), supports regex: "en.*,ja"
# --sub-format = vtt|srt|ass|lrc (vtt is most common for auto-subs)
# Output: {id}.en.vtt file in current directory
```

**Format selection:**
```bash
yt-dlp -f FORMAT URL
# FORMAT syntax:
#   bestaudio          -- best audio-only stream
#   bestvideo          -- best video-only stream
#   bestvideo+bestaudio -- merge best of each (requires ffmpeg)
#   "bestvideo[height<=720]+bestaudio" -- constrained selection
#   best               -- best single-file format (may be lower quality)
#
# -S SORTORDER for format sorting:
#   -S "ext:mp4,res:720"     -- prefer mp4 container, prefer 720p
#   -S "aext:m4a,abr"        -- prefer m4a audio, sort by audio bitrate
```

**List available formats:**
```bash
yt-dlp -F URL
# Output: table of format codes, extensions, resolutions, codecs, filesizes
```

### Python API

```python
import yt_dlp

# Initialize with options dict
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': '/tmp/%(id)s.%(ext)s',
}

# Context manager pattern (recommended)
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    # Extract info without downloading
    info = ydl.extract_info(url, download=False)
    # Returns: dict with same fields as --dump-json

    # Download
    ydl.download([url])  # accepts list of URLs

    # Search
    results = ydl.extract_info("ytsearch5:topic", download=False)
    # results['entries'] = list of info dicts
```

**Key Python option mappings (CLI -> Python dict key):**
| CLI Flag | Python Key | Type |
|---|---|---|
| `--format` | `'format'` | str |
| `--output` | `'outtmpl'` | str or dict |
| `--extract-audio` | `'extractaudio'` | bool |
| `--audio-format` | `'audioformat'` | str |
| `--quiet` | `'quiet'` | bool |
| `--no-warnings` | `'no_warnings'` | bool |
| `--dump-json` | (use `extract_info(download=False)`) | -- |
| `--cookies` | `'cookiefile'` | str (path) |
| `--cookies-from-browser` | `'cookiesfrombrowser'` | tuple |
| `--dateafter` | `'dateafter'` | str (YYYYMMDD) |
| `--match-filters` | `'match_filter'` | callable or str |
| `--download-archive` | `'download_archive'` | str (path) |
| `--max-downloads` | `'max_downloads'` | int |
| `--write-auto-subs` | `'writeautomaticsub'` | bool |
| `--sub-lang` | `'subtitleslangs'` | list[str] |
| `--sub-format` | `'subtitlesformat'` | str |
| `--skip-download` | `'skip_download'` | bool |
| `--ignore-errors` | `'ignoreerrors'` | bool or 'only_download' |
| `--flat-playlist` | `'extract_flat'` | bool or 'in_playlist' |
| `--sleep-requests` | `'sleep_interval_requests'` | float |
| `--sleep-interval` | `'sleep_interval'` | float |
| `--limit-rate` | `'ratelimit'` | int (bytes/sec) |
| `--retries` | `'retries'` | int |
| `--socket-timeout` | `'socket_timeout'` | float |

**Postprocessor pattern (Python):**
```python
opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '0',  # 0=best VBR
    }],
}
```

Available postprocessor keys: `FFmpegExtractAudio`, `FFmpegVideoRemuxer`,
`FFmpegVideoConvertor`, `FFmpegMetadata`, `FFmpegEmbedSubtitle`,
`EmbedThumbnail`, `FFmpegSplitChapters`, `ModifyChapters`.

---

## Pagination Patterns

yt-dlp does not use cursor/offset pagination in the REST API sense.
Pagination is handled internally by extractors.

**Playlist/channel pagination:** Automatic. yt-dlp follows YouTube's continuation
tokens internally. No user action needed.

**Search result pagination:**
```bash
# Get first 50 results
yt-dlp "ytsearch50:topic" --dump-json --no-download
```
The number after `ytsearch` controls result count. Maximum practical limit
is ~100-200 before YouTube stops returning results.

**Batch processing pattern:**
```bash
# Process URLs from file
yt-dlp -a urls.txt --download-archive done.txt
# --download-archive skips already-processed URLs
```

**Python "fetch all" for playlists:**
```python
with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
    playlist = ydl.extract_info(playlist_url, download=False)
    all_entries = playlist.get('entries', [])
    # entries is a generator for large playlists when lazy_playlist=True
    for entry in all_entries:
        print(entry['url'])
```

---

## Rate Limits

yt-dlp itself has no rate limits -- it is a client tool. Rate limits come from
the target sites, primarily YouTube.

**YouTube-specific throttling:**
- Datacenter/VPS IPs are heavily throttled (download speeds drop to 50-100 KB/s)
- Residential IPs get full speed (~10 MB/s+)
- Too many rapid requests -> temporary IP ban (HTTP 429)
- Metadata-only requests (`--dump-json`) are much less likely to trigger throttling

**Built-in rate control options:**
```bash
--sleep-requests SECONDS      # Sleep between HTTP requests during extraction
--sleep-interval SECONDS      # Sleep before each download
--max-sleep-interval SECONDS  # Random sleep between min and max
--limit-rate 1M               # Cap download speed (bytes/sec, K/M suffix)
--throttled-rate 100K         # Re-extract if speed drops below this
--retries 10                  # Retry count (default 10)
--retry-sleep linear=1::2     # Retry backoff: linear 1s start, 2s step
--retry-sleep exp=1:20        # Retry backoff: exponential 1s start, 20s cap
```

**EOS rate control strategy:**
- Search operations: no rate limiting needed (single request per search)
- Transcript fetch: 5 parallel workers (youtube_yt.py) -- no explicit sleep,
  relies on sequential nature of VTT download per video
- Audio download: 60-second timeout per video (apify_scraper.py)
- For batch operations: add `--sleep-requests 1` to avoid 429s

**429 recovery:**
No `Retry-After` header from YouTube. Wait 5-30 minutes, or switch IP.
yt-dlp's built-in `--retries` with `--retry-sleep exp=1:20` handles transient 429s.

---

## Error Codes and Recovery

yt-dlp uses exit codes and stderr messages (no HTTP status codes for the user --
those are handled internally).

**Exit codes:**
| Code | Meaning | Recovery |
|---|---|---|
| 0 | Success | -- |
| 1 | General error (unspecified) | Check stderr |
| 2 | Error in user options / configuration | Fix arguments |
| 100 | yt-dlp must restart (after self-update) | Re-run command |
| 101 | Download cancelled by --max-downloads | Expected behavior |

**Common error patterns (stderr):**
| Error Message | Cause | Recovery |
|---|---|---|
| `ERROR: [youtube] ... Sign in to confirm` | Age-restricted | Add `--cookies` |
| `ERROR: ... HTTP Error 429` | Rate limited | Wait 5-30 min, add sleep |
| `ERROR: ... Video unavailable` | Deleted/private | Skip, use `--ignore-errors` |
| `ERROR: ... This video is not available` | Geo-restricted | Use `--geo-verification-proxy` |
| `WARNING: ... Throttled` | Download speed throttled | `--throttled-rate` triggers re-extract |
| `ERROR: Postprocessing` | ffmpeg missing/failed | Install ffmpeg, check codec support |
| `ERROR: ... No video formats` | No downloadable formats | Use `--ignore-no-formats-error` for metadata |

**Python error handling:**
```python
import yt_dlp

try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
except yt_dlp.utils.DownloadError as e:
    # Most common: video unavailable, age-restricted, geo-blocked
    print(f"Download error: {e}")
except yt_dlp.utils.ExtractorError as e:
    # Extractor-specific failure
    print(f"Extractor error: {e}")
except yt_dlp.utils.PostProcessingError as e:
    # ffmpeg or post-processing failure
    print(f"Post-processing error: {e}")
```

**Retryable vs non-retryable:**
- Retryable: 429, network timeout, throttled download, fragment errors
- Non-retryable: video unavailable, age-restricted (needs cookies), geo-blocked (needs proxy),
  invalid URL, missing ffmpeg

---

## SDK Idioms

**Package:** `yt-dlp` (PyPI). Import: `import yt_dlp` (underscore, not hyphen).

**Initialization -- always use context manager:**
```python
# CORRECT
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)

# WRONG -- leaks resources
ydl = yt_dlp.YoutubeDL(opts)
info = ydl.extract_info(url, download=False)
```

**Async support:** None native. yt-dlp is synchronous. Wrap in threads:
```python
from concurrent.futures import ThreadPoolExecutor

def extract(url):
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        return ydl.extract_info(url, download=False)

with ThreadPoolExecutor(max_workers=5) as pool:
    futures = {pool.submit(extract, url): url for url in urls}
```
This is exactly what EOS does in `fetch_transcripts_parallel()`.

**Progress hooks:**
```python
def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"Progress: {d.get('_percent_str', '?')}")
    elif d['status'] == 'finished':
        print(f"Done: {d['filename']}")

opts = {'progress_hooks': [progress_hook]}
```

**Custom logger:**
```python
class MyLogger:
    def debug(self, msg): pass      # --verbose output
    def info(self, msg): pass       # Normal output
    def warning(self, msg): pass    # Warnings
    def error(self, msg): print(f"ERROR: {msg}")

opts = {'logger': MyLogger()}
```

**Match filter (Python callable):**
```python
def filter_short(info, *, incomplete):
    duration = info.get('duration')
    if duration and duration < 60:
        return 'Video too short'  # returning string = skip reason

opts = {'match_filter': filter_short}
```

---

## Anti-Patterns

### 1. Using subprocess when Python API works
```python
# WRONG
result = subprocess.run(['yt-dlp', '--dump-json', url], capture_output=True)
info = json.loads(result.stdout)

# RIGHT
with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
    info = ydl.extract_info(url, download=False)
```
Exception: EOS uses subprocess intentionally in youtube_yt.py because it needs process
group control (`os.setsid` + `os.killpg`) for reliable timeout killing. The Python API
has no built-in timeout on `extract_info()`. This is a valid reason to use subprocess.

### 2. Using --flat-playlist when you need metadata
```python
# WRONG -- upload_date, view_count are None
ydl.extract_info(url, download=False)  # with extract_flat=True

# RIGHT -- full metadata but slower
ydl.extract_info(url, download=False)  # with extract_flat=False (default)
```

### 3. Hardcoding format codes
```bash
# WRONG -- format 22 might not exist
yt-dlp -f 22 URL

# RIGHT -- use format selectors
yt-dlp -f "bestvideo[height<=720]+bestaudio" URL
```

### 4. Not handling missing ffmpeg
```python
# WRONG -- silently fails
opts = {'postprocessors': [{'key': 'FFmpegExtractAudio', ...}]}

# RIGHT -- check first
import shutil
if not shutil.which('ffmpeg'):
    raise RuntimeError("ffmpeg required for audio extraction")
```

### 5. Using `best` instead of `bestvideo+bestaudio`
```bash
# WRONG -- gets best single file (often 720p)
yt-dlp -f best URL

# RIGHT -- merges best video + best audio (often 1080p+)
yt-dlp -f "bestvideo+bestaudio" URL
```

### 6. Not killing process group on timeout
```python
# WRONG -- leaves ffmpeg orphans
proc = subprocess.Popen(['yt-dlp', ...])
proc.kill()  # only kills yt-dlp, not ffmpeg child

# RIGHT
proc = subprocess.Popen(['yt-dlp', ...], preexec_fn=os.setsid)
os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
```

### 7. Ignoring upload_date format
```python
# WRONG
date_str = info['upload_date']  # "20260315" -- NOT ISO format

# RIGHT
raw = info['upload_date']  # "20260315"
iso = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"  # "2026-03-15"
```

---

## Data Model

**info_dict** -- the core data structure returned by extractors:
```
info_dict
  |-- id: str             # Video ID (e.g., "dQw4w9WgXcQ")
  |-- title: str          # Video title
  |-- description: str    # Full description text
  |-- upload_date: str    # "YYYYMMDD" format
  |-- uploader: str       # Channel display name
  |-- channel: str        # Channel name
  |-- channel_id: str     # Channel ID
  |-- channel_url: str    # Channel URL
  |-- duration: int       # Duration in seconds
  |-- view_count: int     # Total views
  |-- like_count: int     # Likes (None if hidden)
  |-- comment_count: int  # Comments (None if disabled)
  |-- age_limit: int      # 0=all, 18=adult
  |-- webpage_url: str    # Original URL
  |-- thumbnail: str      # Best thumbnail URL
  |-- thumbnails: list    # All thumbnail URLs with sizes
  |-- categories: list    # Video categories
  |-- tags: list          # Video tags
  |-- formats: list       # Available download formats
  |     |-- format_id: str
  |     |-- ext: str
  |     |-- resolution: str
  |     |-- vcodec: str
  |     |-- acodec: str
  |     |-- filesize: int (bytes, may be None)
  |     |-- tbr: float (total bitrate kbps)
  |     +-- url: str (direct download URL)
  |-- subtitles: dict     # Manual subs {lang: [{url, ext}]}
  |-- automatic_captions: dict  # Auto subs {lang: [{url, ext}]}
  |-- chapters: list      # Chapter markers [{title, start_time, end_time}]
  +-- playlist_*          # Present when part of playlist
```

**Playlist info_dict:**
```
playlist_info
  |-- id: str             # Playlist ID
  |-- title: str          # Playlist title
  |-- entries: list       # List of video info_dicts (or generators)
  |-- playlist_count: int # Total entries
  +-- webpage_url: str    # Playlist URL
```

Fields that may be None: `like_count` (hidden by uploader), `comment_count` (disabled),
`filesize` (not always pre-computed), `duration` (live streams).

---

## Webhooks and Events

N/A. yt-dlp is a client-side tool with no webhook or server-side event system.

For post-download automation, use:
- `--exec` flag: execute command after download
  ```bash
  yt-dlp --exec "echo Downloaded: {}" URL
  yt-dlp --exec "after_move:mv {} /archive/" URL
  ```
- Python `progress_hooks`: callback on download progress/completion
- Python postprocessors: custom processing pipeline

---

## Limits

**YouTube search limits:**
- `ytsearchN:` practical max: ~100-200 results per query
- YouTube API-less search returns relevance-sorted, not exhaustive

**Download limits:**
- `--max-filesize 10M` -- abort if file exceeds size (EOS uses this)
- `--max-downloads N` -- stop after N successful downloads
- `--playlist-items 1:10` -- download only items 1-10 of playlist

**Subtitle limits:**
- Auto-generated captions: only available for videos with enough speech
- Language availability varies per video
- VTT files can be large for long videos (10+ MB for 2-hour video)

**Output template field length:**
- `%(title)s` can be 100+ chars -- use `--trim-filenames 200` for safety
- `--restrict-filenames` limits to ASCII, replaces spaces with underscores

**Concurrent limits:**
- `-N` (concurrent fragments): helps with DASH/HLS, not regular downloads
- No built-in concurrent video download -- use external parallelism (ThreadPoolExecutor)

**Process limits (EOS-specific):**
- youtube_yt.py: 120s timeout on search, 30s timeout on subtitle fetch
- apify_scraper.py: 60s timeout on audio download
- ThreadPoolExecutor: max 5 workers for parallel transcript fetch

---

## Cost Model

**yt-dlp itself:** Free, open source (Unlicense). No API keys, no credits, no billing.

**Indirect costs:**
- **Bandwidth:** Video downloads consume significant bandwidth. A 1080p 10-minute
  video is ~100-500 MB. Audio-only is ~5-15 MB. Metadata-only is ~5 KB.
- **Storage:** Downloaded media needs disk space. EOS uses temp directories and
  cleans up after processing.
- **CPU:** Audio extraction (-x) requires ffmpeg re-encoding. MP3 conversion of
  a 10-minute video takes ~5-10 seconds.
- **VPS costs:** yt-dlp operations on VPS cost bandwidth from the VPS provider.
  Metadata-only operations are negligible.

**Cost optimization for EOS:**
- Prefer `--dump-json --no-download` for metadata (near-zero cost)
- Prefer `--write-auto-subs --skip-download` for transcripts (minimal bandwidth)
- Use `--max-filesize 10m` to cap audio downloads
- Use `--audio-quality 0` (VBR) not CBR for smaller files at same quality
- Clean up temp files immediately after processing

---

## Version Pinning

**Current versions (EOS VPS):**
- CLI: `2026.03.17` (`yt-dlp --version`)
- Python package: `2026.3.17` (`pip show yt-dlp`)
- Extractors: 1871 sites supported

**Versioning scheme:** `YYYY.MM.DD[.N]` -- date-based releases, roughly weekly.

**How to pin:**
```bash
pip install yt-dlp==2026.3.17    # Exact version
pip install yt-dlp>=2026.3.0     # Minimum version
```

**Update policy:** yt-dlp must be updated frequently because site extractors break
when YouTube/etc change their frontends. A version more than 2-3 months old will
likely fail on some sites.

**Breaking changes:** Rare for CLI interface. Mostly extractor fixes. Python API
is less stable -- option names occasionally change between major versions.
Always test after updating.

**Known deprecations:**
- `youtube-dl` -- the original project is effectively abandoned. Never use it.
- `--get-url`, `--get-title`, etc. -- deprecated in favor of `--print`
- `--prefer-avconv` -- avconv support removed, ffmpeg only

---

# Tier 2 -- Creator Intelligence

## Design Intent and Tradeoffs

yt-dlp was forked from youtube-dl by pukkandan in 2021 because youtube-dl's
development had stagnated -- DMCA takedown, slow merges, broken extractors.

**Design philosophy:**
- **Extractor-per-site architecture:** Each website gets a dedicated extractor that
  normalizes output into a common `info_dict`. This is why yt-dlp supports 1871 sites
  with a consistent interface.
- **CLI-first, library-second:** The Python API mirrors CLI flags as dict keys. This
  means the API is powerful but not always Pythonic (e.g., `'outtmpl'` not `'output_template'`).
- **Correctness over speed:** yt-dlp fetches full metadata by default (no `--flat-playlist`).
  This is slower but means dates, view counts, and other fields are real, not estimated.
- **User control over magic:** Format selection, output templates, and postprocessors
  give granular control. The tool avoids "smart defaults" that hide behavior.

**What yt-dlp is NOT:**
- Not a streaming service (downloads, doesn't stream)
- Not a media player (no playback)
- Not a transcoding tool (delegates to ffmpeg)
- Not a search engine (searches via site-specific extractors, not its own index)

**Key tradeoff:** yt-dlp prioritizes download reliability over speed. It will retry,
re-extract, and fall back to lower quality formats rather than fail. This is why
`--retries 10` is the default.

---

## Problem-Solution Map and Hidden Capabilities

**Problem: Need video metadata without downloading anything**
Solution: `--dump-json --no-download` or Python `extract_info(download=False)`.
Returns 100+ fields including engagement metrics, thumbnails, chapters.

**Problem: Need to search YouTube without an API key**
Solution: `ytsearchN:query` pseudo-URL. No quotas, no billing, no key management.
Also works: `ytsearchdateN:query` for date-sorted results.

**Problem: Need only a clip from a long video**
Solution: `--download-sections "*10:00-15:00"` downloads only the 10:00-15:00 segment.
Needs ffmpeg. Can combine with `-x` for audio-only clips.

**Problem: Need to monitor a channel for new uploads**
Solution: `--download-archive archive.txt` + channel URL. Re-running the command
only downloads new videos not in the archive file.

**Hidden capability: Browser impersonation**
`--impersonate chrome` makes yt-dlp's HTTP requests look like Chrome. Bypasses
some bot detection. `--impersonate ""` auto-selects best impersonation.

**Hidden capability: Custom output templates with conditionals**
```bash
yt-dlp -o "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s" URL
# Outputs: "2026-03-15 - Video Title.mp4"
```

**Hidden capability: Chapter-based splitting**
`--split-chapters` splits a video into separate files per chapter marker.
Combined with `--download-sections "chapter_name"` for targeted extraction.

**Hidden capability: Match filters for smart batch processing**
```bash
# Only download videos with >10000 views and duration > 60s
yt-dlp --match-filters "view_count>10000 & duration>60" PLAYLIST_URL
```

**Hidden capability: Preset aliases**
```bash
yt-dlp --preset-alias mp3 URL    # Auto-configures for best MP3 extraction
yt-dlp --preset-alias mp4 URL    # Auto-configures for MP4 download
```

---

## Operational Behavior and Edge Cases

**YouTube throttling on VPS/datacenter IPs:**
YouTube identifies datacenter IP ranges and throttles downloads to 50-100 KB/s.
This does NOT affect metadata extraction (`--dump-json`) or subtitle downloads.
Only actual media downloads are throttled. The `--throttled-rate` option detects
this and re-extracts with a different format/CDN.

**Subtitle filename unpredictability:**
Auto-generated subs may be saved as `{id}.en.vtt`, `{id}.en-orig.vtt`, or
`{id}.en.{uuid}.vtt` depending on the YouTube response. Always glob for
`{id}*.vtt` rather than assuming exact filename.

**Live stream behavior:**
`--dump-json` on a live stream returns metadata but `duration` is None and
`is_live` is True. Download attempts on live streams are ongoing (use
`--live-from-start` or `--wait-for-video` for scheduled streams).

**Deleted/private video in playlist:**
yt-dlp skips unavailable videos by default (`--no-abort-on-error`).
The `info_dict` for unavailable entries may have only `id` and `title` fields.

**Unicode in titles:**
Some video titles contain emoji, CJK characters, or RTL text. Use
`--restrict-filenames` for filesystem safety, or handle encoding in Python.

**Age-restricted content without cookies:**
Returns `DownloadError` with "Sign in to confirm your age". No workaround
except providing valid cookies from an age-verified Google account.

**Concurrent writes to download archive:**
`--download-archive` is NOT thread-safe. If running multiple yt-dlp instances
writing to the same archive file, entries may be lost or duplicated.
Use separate archive files per worker.

---

## Ecosystem Position and Composition

**Position:** Client-side media acquisition layer. yt-dlp is the first step in
any media processing pipeline -- it gets the content, then hands off to
specialized tools.

**Natural complements in EOS:**
- **ffmpeg** -- required dependency for format conversion, audio extraction,
  video merging. yt-dlp shells out to ffmpeg for all post-processing.
- **Whisper / Groq STT** -- transcription of downloaded audio. EOS pipeline:
  yt-dlp downloads audio -> Whisper transcribes -> LLM analyzes.
- **Apify** -- web scraping complement. yt-dlp handles video sites, Apify
  handles general web content. Both feed into EOS research pipelines.

**Forced integration anti-patterns:**
- Don't use yt-dlp as a web scraper (use Apify/requests instead)
- Don't use yt-dlp for real-time streaming (use streamlink)
- Don't store yt-dlp output URLs for later use -- direct URLs expire quickly

**Data handoff patterns:**
- yt-dlp JSON metadata -> Python dict -> Neon database (research pipeline)
- yt-dlp audio file -> Whisper model -> transcript text (transcription pipeline)
- yt-dlp VTT subtitle -> regex cleanup -> plaintext (caption pipeline)

---

## Trajectory and Evolution

**Active development:** yt-dlp releases roughly weekly. The project has 80K+ GitHub
stars and is the de facto standard for media downloading.

**Recent trajectory (2025-2026):**
- JavaScript runtime support added (Deno, Node, QuickJS) for sites requiring JS execution
- `--impersonate` for browser-like requests (anti-bot bypass)
- `--preset-alias` for common download patterns (mp3, mp4, etc.)
- External JavaScript component system (`--remote-components`)
- Continued extractor updates as sites change their frontends

**Deprecation signals:**
- `youtube-dl` compatibility mode (`--compat-options`) suggests eventual removal
  of legacy behaviors
- Old-style `--get-url`, `--get-title` replaced by `--print` template system
- Python API option names gradually being cleaned up (but slowly)

**What to watch:**
- Site-specific extractor breakage after YouTube frontend updates (most common issue)
- Potential legal challenges (DMCA history with youtube-dl)
- Growing anti-bot measures from platforms requiring more sophisticated impersonation

---

## Conceptual Model and Solution Recipes

**Mental model:** Think of yt-dlp as a universal media metadata API + downloader.
The primitives are: Extract (get info) -> Select (choose format) -> Download (fetch media)
-> Process (convert/embed). Each step is independently usable.

**Recipe 1: Competitor content research pipeline**
```
1. yt-dlp "ytsearch20:{competitor} {topic}" --dump-json --no-download
2. Parse JSON lines -> filter by date and view_count
3. For top 5: yt-dlp --write-auto-subs --skip-download
4. Clean VTT to plaintext
5. Feed transcripts to LLM for analysis
```
This is exactly what EOS `search_and_transcribe()` does.

**Recipe 2: Audio content library builder**
```
1. yt-dlp CHANNEL_URL --download-archive done.txt -f bestaudio
   -x --audio-format mp3 --audio-quality 0
   -o "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"
2. Re-run periodically -- archive file skips already-downloaded
3. --match-filters "duration>300" to skip shorts
```

**Recipe 3: Trending topic monitor**
```
1. yt-dlp "ytsearchdate10:{topic}" --dump-json --no-download
2. Compare view_count growth rate across runs
3. Flag videos with unusual engagement velocity
4. Fetch transcripts of flagged videos for content analysis
```

**Recipe 4: Media asset extractor for content creation**
```
1. yt-dlp --write-thumbnail --skip-download URL  # Get thumbnail
2. yt-dlp --download-sections "*0:00-0:10" URL   # Get intro clip
3. yt-dlp -x --audio-format wav URL              # Get lossless audio
4. Use extracted assets in own content production
```

**Recipe 5: Batch channel audit**
```
1. yt-dlp CHANNEL_URL --dump-json --no-download --flat-playlist
   (fast: get video IDs and titles only)
2. For interesting videos: extract full metadata
3. Aggregate: avg views, posting frequency, top performing content
4. Feed to LLM for competitive analysis report
```

---

## Industry Expert and Cutting-Edge Usage

**AI-powered content analysis pipeline:**
The frontier pattern is: yt-dlp (acquisition) -> Whisper (transcription) ->
LLM (analysis). This eliminates the need for YouTube Data API quotas and
provides deeper analysis than metadata alone. EOS already implements this.

**Browser impersonation for anti-bot bypass:**
`--impersonate chrome` is the cutting-edge approach to bypassing increasingly
aggressive bot detection. Combined with `--cookies-from-browser`, this makes
yt-dlp requests indistinguishable from browser traffic.

**Selective chapter download for research:**
Instead of downloading full 2-hour podcasts, use `--download-sections` with
chapter titles to extract only relevant segments. Saves bandwidth and processing
time on VPS.

**Archive-based incremental processing:**
Power users run yt-dlp on a cron schedule with `--download-archive` against
channels and playlists. Combined with `--exec` for post-download automation,
this creates fully automated content monitoring pipelines.

**Format sorting for quality optimization:**
Instead of `-f best`, experts use `-S` for nuanced quality control:
```bash
# Prefer VP9 codec (better quality per bit), then resolution
yt-dlp -S "vcodec:vp9,res:1080" URL
# Prefer Opus audio (best quality for a given bitrate)
yt-dlp -f ba -S "acodec:opus" URL
```

**Parallel extraction at scale:**
For large-scale research (hundreds of videos), wrap yt-dlp in Python
ThreadPoolExecutor with separate temp directories per worker. Use
`--socket-timeout 30` and `--retries 3` to fail fast on problematic videos
rather than blocking the entire batch.

---

## EOS Usage Patterns

**Primary usage: YouTube research via last30days skill**
- File: `.agents/skills/last30days/scripts/lib/youtube_yt.py`
- Pattern: subprocess-based (for process group timeout control)
- Operations: search (`ytsearch`), subtitle fetch (`--write-auto-subs`)
- Depth tiers: quick (10/3), default (20/5), deep (40/8)
- Date handling: soft filter in Python, not `--dateafter`

**Secondary usage: Audio transcription via apify_scraper**
- File: `services/apify_scraper.py`
- Pattern: subprocess with `--extract-audio --audio-format mp3`
- Feeds into Whisper `small` model for transcription
- 60-second timeout, 10MB max file size

**Environment check:**
- `is_ytdlp_installed()` gates all YouTube features
- Binary at `/usr/local/bin/yt-dlp`
- Python package at `/usr/local/lib/python3.12/dist-packages`

---

## Gotchas

**VPS IP throttling confirmed:** YouTube downloads from this VPS are throttled.
Metadata and subtitle operations are unaffected. Audio downloads work within
the 60-second timeout for most videos under 10 minutes.

**Process group kill required:** EOS subprocess calls use `os.setsid` +
`os.killpg` pattern. This is critical -- without it, ffmpeg child processes
become orphans on timeout.

**upload_date YYYYMMDD format:** Every EOS integration must convert to ISO format.
Forgetting this causes date comparison bugs.

**--flat-playlist intentionally avoided:** EOS needs real upload_date and view_count.
The performance cost of full extraction is accepted.

**Soft date filtering over --dateafter:** YouTube search for evergreen topics returns
0 results with strict date filtering. EOS filters in Python with a fallback to
keep all results if fewer than 3 match the date range.
