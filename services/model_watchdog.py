#!/usr/bin/env python3
"""
UMH Model Watchdog — governed model-provenance primitive.

Observes active Claude Code session transcripts for model substitutions
away from the host-wide desired model policy. When a deviation is detected:

1. Records immutable provenance (observed model, desired model, timestamps)
2. Attempts safe remediation via atomic settings.json write
3. Alerts via Discord (observability only — never gates remediation)

The watchdog enforces a DESIRED MODEL POLICY, not a serving guarantee.
Anthropic's server-side routing may substitute models at the API layer.
This daemon ensures the next turn requests the correct model and maintains
a truthful record of what model was actually served.

Policy source: MODEL_WATCHDOG_TARGET env var (authoritative)
Controlled output: ~/.claude/settings.json (hot-reloaded by CC per turn)

Install: bash scripts/install-model-watchdog.sh
Logs:    /opt/OS/logs/model_watchdog.log
State:   /opt/OS/data/runtime/model_watchdog/
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from substrate.execution.cpu_gate import gated_subprocess_run

WATCHDOG_VERSION = "2.1.0"
SOURCE_COMMIT = os.environ.get("UMH_MODEL_WATCHDOG_SOURCE_COMMIT", "")
DEPLOYMENT_ID = os.environ.get("UMH_MODEL_WATCHDOG_DEPLOYMENT_ID", "")

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
LOG_FILE = os.path.join(UMH_ROOT, "logs", "model_watchdog.log")
SETTINGS_FILE = os.path.expanduser("~/.claude/settings.json")
PROJECTS_DIR = os.path.expanduser("~/.claude/projects")

STATE_DIR = os.path.join(UMH_ROOT, "data", "runtime", "model_watchdog")
CURSOR_FILE = os.path.join(STATE_DIR, "cursors.json")
PROVENANCE_FILE = os.path.join(STATE_DIR, "provenance.jsonl")
HEALTH_FILE = os.path.join(STATE_DIR, "health.json")
SETTINGS_LOCK = os.path.join(STATE_DIR, "settings.lock")
PAUSE_FILE = os.path.join(STATE_DIR, "PAUSE")

POLL_INTERVAL = 5
COOLDOWN_BASE = 60
COOLDOWN_MAX = 600
ALERT_BURST_LIMIT = 5
ALERT_BURST_WINDOW = 300

TARGET_MODEL = os.environ.get("MODEL_WATCHDOG_TARGET", "claude-fable-5")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.environ.get(
    "MODEL_WATCHDOG_DISCORD_CHANNEL",
    os.environ.get("DISCORD_NOTIFICATION_CHANNEL_ID", ""),
)

logger = logging.getLogger("model-watchdog")
_running = True


def _setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [model-watchdog] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter("%(asctime)s [model-watchdog] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(logging.INFO)


@dataclass
class ProvenanceEvent:
    schema_version: str = "1"
    timestamp: str = ""
    session_id: str = ""
    project_path: str = ""
    desired_model: str = ""
    observed_model: str = ""
    match: bool = True
    remediation_required: bool = False
    remediation_attempted: bool = False
    remediation_succeeded: bool = False
    source_transcript: str = ""
    watchdog_version: str = WATCHDOG_VERSION


@dataclass
class SessionState:
    last_alert_time: float = 0.0
    consecutive_deviations: int = 0
    cooldown_seconds: float = COOLDOWN_BASE
    total_observed: int = 0
    target_matches: int = 0
    substituted: int = 0
    remediation_attempts: int = 0
    remediation_successes: int = 0
    remediation_failures: int = 0
    models_seen: dict = field(default_factory=dict)


@dataclass
class HealthCounters:
    polls_total: int = 0
    successful_polls: int = 0
    discovery_failures: int = 0
    sessions_seen: int = 0
    transcripts_active: int = 0
    assistant_messages_observed: int = 0
    target_model_messages: int = 0
    substituted_model_messages: int = 0
    remediation_attempts: int = 0
    remediation_successes: int = 0
    remediation_failures: int = 0
    settings_write_failures: int = 0
    transcript_parse_failures: int = 0
    transcript_rotation_events: int = 0
    discord_alert_attempts: int = 0
    discord_alert_failures: int = 0
    last_successful_poll_at: str = ""
    last_observation_at: str = ""
    started_at: str = ""
    watchdog_version: str = WATCHDOG_VERSION
    source_commit: str = SOURCE_COMMIT
    deployment_id: str = DEPLOYMENT_ID
    runtime_path: str = ""
    runtime_sha256: str = ""
    unit_sha256: str = ""


@dataclass
class CursorEntry:
    path: str = ""
    inode: int = 0
    offset: int = 0
    last_updated: str = ""


def _sha256_file(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _deployment_manifest(runtime_path: str) -> dict:
    try:
        manifest_path = os.path.join(os.path.dirname(runtime_path), "MANIFEST.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


class ModelWatchdog:
    def __init__(self) -> None:
        os.makedirs(STATE_DIR, exist_ok=True)
        self._sessions: dict[str, SessionState] = {}
        self._cursors: dict[str, CursorEntry] = {}
        runtime_path = os.path.abspath(__file__)
        manifest = _deployment_manifest(runtime_path)
        self._health = HealthCounters(started_at=self._now())
        self._health.runtime_path = runtime_path
        self._health.runtime_sha256 = _sha256_file(__file__)
        self._health.unit_sha256 = _sha256_file("/etc/systemd/system/umh-model-watchdog.service")
        self._health.source_commit = str(manifest.get("source_commit") or SOURCE_COMMIT)
        self._health.deployment_id = str(manifest.get("deployment_id") or DEPLOYMENT_ID)
        self._global_alerts: list[float] = []
        self._load_cursors()

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    def _load_cursors(self) -> None:
        try:
            if os.path.exists(CURSOR_FILE):
                with open(CURSOR_FILE, "r") as f:
                    data = json.load(f)
                for path, entry in data.items():
                    self._cursors[path] = CursorEntry(**entry)
                logger.info(f"Loaded {len(self._cursors)} cursor(s) from state")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Corrupt cursor file, starting fresh: {e}")
            self._cursors = {}
        except Exception as e:
            logger.warning(f"Failed to load cursors: {e}")
            self._cursors = {}

    def _save_cursors(self) -> None:
        data = {path: asdict(entry) for path, entry in self._cursors.items()}
        self._atomic_write_json(CURSOR_FILE, data)

    def _save_health(self) -> None:
        self._atomic_write_json(HEALTH_FILE, asdict(self._health))

    @staticmethod
    def _atomic_write_json(path: str, data: dict) -> bool:
        try:
            dir_path = os.path.dirname(path)
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
                return True
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"Atomic write failed for {path}: {e}")
            return False

    def _append_provenance(self, event: ProvenanceEvent) -> bool:
        try:
            os.makedirs(os.path.dirname(PROVENANCE_FILE), exist_ok=True)
            with open(PROVENANCE_FILE, "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(asdict(event)) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            return True
        except Exception as e:
            logger.error(f"Provenance write failed: {e}")
            return False

    def _get_active_sessions(self) -> list[dict]:
        try:
            result = gated_subprocess_run(
                ["claude", "agents", "--json"],
                caller="model_watchdog_discovery",
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result is None:
                self._health.discovery_failures += 1
                logger.warning("claude agents skipped by CPU gate")
                return []
            if result.returncode != 0:
                self._health.discovery_failures += 1
                if result.stderr.strip():
                    logger.debug(f"claude agents stderr: {result.stderr.strip()[:200]}")
                return []
            output = result.stdout.strip()
            if not output:
                return []
            sessions = json.loads(output)
            if not isinstance(sessions, list):
                self._health.discovery_failures += 1
                logger.warning("claude agents returned non-list JSON")
                return []
            return [s for s in sessions if isinstance(s, dict) and s.get("sessionId")]
        except subprocess.TimeoutExpired:
            self._health.discovery_failures += 1
            logger.warning("claude agents timed out")
            return []
        except json.JSONDecodeError as e:
            self._health.discovery_failures += 1
            logger.warning(f"claude agents returned invalid JSON: {e}")
            return []
        except FileNotFoundError:
            self._health.discovery_failures += 1
            logger.warning("claude binary not found")
            return []
        except Exception as e:
            self._health.discovery_failures += 1
            logger.warning(f"Session discovery failed: {e}")
            return []

    def _find_transcript(self, session_id: str) -> Optional[str]:
        projects = Path(PROJECTS_DIR)
        if not projects.exists():
            return None
        try:
            for proj_dir in projects.iterdir():
                if not proj_dir.is_dir():
                    continue
                candidate = proj_dir / f"{session_id}.jsonl"
                if candidate.exists():
                    return str(candidate)
        except PermissionError:
            logger.debug(f"Permission denied scanning {PROJECTS_DIR}")
        except Exception as e:
            logger.debug(f"Transcript search error: {e}")
        return None

    def _check_transcript(self, path: str, session_id: str) -> list[tuple[str, str]]:
        """Read new lines from transcript. Returns list of (observed_model, turn_id)."""
        cursor = self._cursors.get(path)
        try:
            stat = os.stat(path)
        except OSError:
            return []

        current_inode = stat.st_ino
        current_size = stat.st_size

        if cursor is None:
            cursor = CursorEntry(path=path, inode=current_inode, offset=current_size)
            self._cursors[path] = cursor
            logger.info(f"New transcript {session_id[:8]}, starting at offset {current_size}")
            return []

        if cursor.inode != current_inode:
            logger.info(
                f"Transcript rotated for {session_id[:8]} (inode {cursor.inode} -> {current_inode})"
            )
            self._health.transcript_rotation_events += 1
            cursor.inode = current_inode
            cursor.offset = 0

        if current_size < cursor.offset:
            logger.info(
                f"Transcript truncated for {session_id[:8]} ({cursor.offset} -> {current_size})"
            )
            cursor.offset = 0

        if current_size <= cursor.offset:
            return []

        observations: list[tuple[str, str]] = []
        try:
            with open(path, "r") as f:
                f.seek(cursor.offset)
                new_data = f.read()
                cursor.offset = f.tell()
                cursor.last_updated = self._now()

            for line in new_data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self._health.transcript_parse_failures += 1
                    continue

                if not isinstance(record, dict):
                    continue
                if record.get("type") != "assistant":
                    continue

                msg = record.get("message")
                if not isinstance(msg, dict):
                    continue

                model = msg.get("model", "")
                if not model or model == "<synthetic>":
                    continue

                turn_id = msg.get("id", "")
                observations.append((model, turn_id))

        except PermissionError:
            logger.warning(f"Permission denied reading {path}")
        except Exception as e:
            logger.warning(f"Error reading transcript {session_id[:8]}: {e}")
            self._health.transcript_parse_failures += 1

        return observations

    def _is_paused(self) -> bool:
        return os.path.exists(PAUSE_FILE)

    def _is_target_model(self, model: str) -> bool:
        return model.startswith(TARGET_MODEL)

    def _ensure_settings_model(self) -> tuple[bool, str]:
        """Atomic read-modify-write of settings.json. Returns (changed, detail)."""
        lock_fd = None
        try:
            lock_fd = os.open(SETTINGS_LOCK, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False, "lock held by another process"

            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                return False, f"settings read failed: {e}"

            if not isinstance(settings, dict):
                return False, "settings is not a JSON object"

            current = settings.get("model", "")
            if self._is_target_model(current):
                return False, "already correct"

            suffix = ""
            if "[" in current:
                suffix = current[current.index("[") :]
            else:
                suffix = "[1m]"

            new_model = TARGET_MODEL + suffix
            settings["model"] = new_model

            settings_dir = os.path.dirname(SETTINGS_FILE)
            fd, tmp_path = tempfile.mkstemp(dir=settings_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(settings, f, indent=4)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())

                orig_stat = os.stat(SETTINGS_FILE)
                os.replace(tmp_path, SETTINGS_FILE)
                try:
                    os.chmod(SETTINGS_FILE, orig_stat.st_mode)
                    os.chown(SETTINGS_FILE, orig_stat.st_uid, orig_stat.st_gid)
                except OSError:
                    pass

                verify_ok = False
                try:
                    with open(SETTINGS_FILE, "r") as f:
                        verify = json.load(f)
                    if verify.get("model") == new_model:
                        verify_ok = True
                except Exception:
                    pass

                if verify_ok:
                    logger.info(f"settings.json corrected: {current} -> {new_model}")
                    return True, f"{current} -> {new_model}"
                else:
                    return False, "post-write verification failed"

            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            self._health.settings_write_failures += 1
            return False, f"settings write failed: {e}"
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except OSError:
                    pass

    def _should_alert(self, session_id: str) -> bool:
        now = time.time()

        self._global_alerts = [t for t in self._global_alerts if now - t < ALERT_BURST_WINDOW]
        if len(self._global_alerts) >= ALERT_BURST_LIMIT:
            return False

        ss = self._sessions.get(session_id)
        if ss is not None and now - ss.last_alert_time < ss.cooldown_seconds:
            return False

        return True

    def _send_discord_alert(self, msg: str) -> bool:
        if not DISCORD_CHANNEL_ID:
            return False

        self._health.discord_alert_attempts += 1

        if self._send_via_docker(msg):
            return True

        if DISCORD_BOT_TOKEN:
            try:
                import urllib.request

                payload = json.dumps({"content": msg[:2000]}).encode("utf-8")
                req = urllib.request.Request(
                    f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    },
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=10)
                if resp.status in (200, 201):
                    return True
            except Exception as e:
                logger.debug(f"Discord HTTP API fallback failed: {e}")

        self._health.discord_alert_failures += 1
        return False

    @staticmethod
    def _send_via_docker(msg: str) -> bool:
        msg_file = os.path.join(STATE_DIR, "discord_msg.txt")
        try:
            with open(msg_file, "w") as f:
                f.write(msg[:1900])
        except Exception:
            return False

        script = (
            "import discord,asyncio,os\n"
            "async def s():\n"
            " intents=discord.Intents.default()\n"
            " c=discord.Client(intents=intents)\n"
            " @c.event\n"
            " async def on_ready():\n"
            f"  ch=c.get_channel({DISCORD_CHANNEL_ID})\n"
            "  if ch:\n"
            "   with open('/app/data/runtime/model_watchdog/discord_msg.txt') as f:\n"
            "    m=f.read()\n"
            "   await ch.send(m)\n"
            "  await c.close()\n"
            " t=os.environ.get('DISCORD_BOT_TOKEN','')\n"
            " if t: await c.start(t)\n"
            "asyncio.run(s())\n"
        )
        try:
            result = gated_subprocess_run(
                ["docker", "exec", "os-discord", "python3", "-c", script],
                caller="model_watchdog_discord_alert",
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result is None:
                self._health.discord_alert_failures += 1
                logger.warning("Discord alert skipped by CPU gate")
                return False
            if result.returncode != 0:
                logger.debug(
                    f"Docker discord send failed: rc={result.returncode} "
                    f"stderr={result.stderr.strip()[:200]}"
                )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.debug("Docker discord send timed out (30s)")
            return False
        except Exception as e:
            logger.debug(f"Docker discord send error: {e}")
            return False
        finally:
            try:
                os.unlink(msg_file)
            except OSError:
                pass

    def _handle_observations(
        self,
        session_id: str,
        transcript_path: str,
        observations: list[tuple[str, str]],
    ) -> None:
        if not observations:
            return

        ss = self._sessions.setdefault(session_id, SessionState())

        deviations_this_batch: list[ProvenanceEvent] = []

        for observed_model, turn_id in observations:
            self._health.assistant_messages_observed += 1
            ss.total_observed += 1
            ss.models_seen[observed_model] = ss.models_seen.get(observed_model, 0) + 1

            is_match = self._is_target_model(observed_model)

            if is_match:
                self._health.target_model_messages += 1
                ss.target_matches += 1
                ss.consecutive_deviations = 0
                ss.cooldown_seconds = COOLDOWN_BASE
            else:
                self._health.substituted_model_messages += 1
                ss.substituted += 1
                ss.consecutive_deviations += 1

            event = ProvenanceEvent(
                timestamp=self._now(),
                session_id=session_id,
                project_path=os.path.dirname(transcript_path),
                desired_model=TARGET_MODEL,
                observed_model=observed_model if observed_model else "UNKNOWN",
                match=is_match,
                remediation_required=not is_match,
                source_transcript=transcript_path,
            )

            if not is_match:
                deviations_this_batch.append(event)
            else:
                self._append_provenance(event)

        if not deviations_this_batch:
            return

        paused = self._is_paused()
        if paused:
            logger.info("PAUSED — recording provenance without remediation")
            for event in deviations_this_batch:
                event.remediation_attempted = False
                event.remediation_succeeded = False
                self._append_provenance(event)
        else:
            changed, detail = self._ensure_settings_model()
            self._health.remediation_attempts += 1
            ss.remediation_attempts += 1

            if changed:
                self._health.remediation_successes += 1
                ss.remediation_successes += 1
            elif "already correct" in detail:
                self._health.remediation_successes += 1
                ss.remediation_successes += 1
            elif "lock held" in detail:
                try:
                    with open(SETTINGS_FILE, "r") as f:
                        current = json.load(f).get("model", "")
                    if self._is_target_model(current):
                        self._health.remediation_successes += 1
                        ss.remediation_successes += 1
                        detail = "already correct (checked after lock contention)"
                    else:
                        self._health.remediation_failures += 1
                        ss.remediation_failures += 1
                except Exception:
                    self._health.remediation_failures += 1
                    ss.remediation_failures += 1
            else:
                self._health.remediation_failures += 1
                ss.remediation_failures += 1

            for event in deviations_this_batch:
                event.remediation_attempted = True
                event.remediation_succeeded = changed or "already correct" in detail
                self._append_provenance(event)

        last_deviation = deviations_this_batch[-1]
        short_id = session_id[:8]
        count = len(deviations_this_batch)
        detail_msg = "PAUSED" if paused else detail

        logger.info(
            f"DEVIATION: session {short_id} | "
            f"{count} turn(s) using {last_deviation.observed_model} "
            f"(target: {TARGET_MODEL}) | remediation: {detail_msg}"
        )

        if not paused and self._should_alert(session_id):
            now = time.time()
            self._global_alerts.append(now)
            ss.last_alert_time = now
            ss.cooldown_seconds = min(ss.cooldown_seconds * 1.5, COOLDOWN_MAX)

            sub_rate = (
                f"{ss.substituted}/{ss.total_observed} "
                f"({100 * ss.substituted / ss.total_observed:.0f}%)"
                if ss.total_observed > 0
                else "N/A"
            )
            msg = (
                f"**Model Watchdog**\n"
                f"Session `{short_id}`: {count} turn(s) served "
                f"`{last_deviation.observed_model}` "
                f"(policy: `{TARGET_MODEL}`)\n"
                f"Substitution rate: {sub_rate}\n"
                f"Remediation: {detail_msg}"
            )
            self._send_discord_alert(msg)

    def _poll(self) -> None:
        self._health.polls_total += 1
        if self._is_paused():
            self._health.sessions_seen = 0
            self._health.transcripts_active = 0
            self._health.successful_polls += 1
            self._health.last_successful_poll_at = self._now()
            return
        sessions = self._get_active_sessions()
        self._health.sessions_seen = len(sessions)

        transcripts_found = 0
        for s in sessions:
            sid = s.get("sessionId", "")
            if not sid:
                continue
            path = self._find_transcript(sid)
            if not path:
                continue
            transcripts_found += 1
            try:
                observations = self._check_transcript(path, sid)
                if observations:
                    self._handle_observations(sid, path, observations)
                    self._save_cursors()
            except Exception as e:
                logger.error(f"Error processing session {sid[:8]}: {e}")

        self._health.transcripts_active = transcripts_found
        self._health.successful_polls += 1
        self._health.last_successful_poll_at = self._now()

        if any(ss.total_observed > 0 for ss in self._sessions.values()):
            self._health.last_observation_at = self._now()

    def run(self) -> None:
        _setup_logging()
        logger.info(
            f"Started v{WATCHDOG_VERSION} | "
            f"target={TARGET_MODEL} | "
            f"poll={POLL_INTERVAL}s | "
            f"cooldown={COOLDOWN_BASE}-{COOLDOWN_MAX}s | "
            f"burst_limit={ALERT_BURST_LIMIT}/{ALERT_BURST_WINDOW}s | "
            f"discord={'configured' if DISCORD_BOT_TOKEN else 'not configured'}"
        )

        if not self._is_paused():
            changed, detail = self._ensure_settings_model()
            if changed:
                logger.info(f"Initial settings correction: {detail}")
        else:
            logger.info("Model watchdog paused at startup — settings correction suppressed")

        save_interval = 30
        last_save = time.time()
        log_quiet_interval = 300
        last_quiet_log = 0.0

        while _running:
            try:
                self._poll()
            except Exception as e:
                logger.error(f"Poll cycle error: {e}")

            now = time.time()
            if now - last_save >= save_interval:
                self._save_cursors()
                self._save_health()
                last_save = now

            if self._health.transcripts_active == 0 and now - last_quiet_log >= log_quiet_interval:
                logger.info("No active transcripts — watching")
                last_quiet_log = now

            time.sleep(POLL_INTERVAL)

        self._save_cursors()
        self._save_health()
        logger.info("Stopped")


def _signal_handler(sig, frame):
    global _running
    logger.info(f"Received signal {sig}, shutting down")
    _running = False


def generate_summary(
    session_id: Optional[str] = None,
    since: Optional[str] = None,
) -> dict:
    """Read-only provenance summarizer."""
    if not os.path.exists(PROVENANCE_FILE):
        return {"error": "No provenance data found"}

    events: list[dict] = []
    try:
        with open(PROVENANCE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if session_id and not event.get("session_id", "").startswith(session_id):
                    continue
                if since and event.get("timestamp", "") < since:
                    continue
                events.append(event)
    except Exception as e:
        return {"error": f"Failed to read provenance: {e}"}

    if not events:
        return {"total_observed": 0, "message": "No matching events"}

    total = len(events)
    matches = sum(1 for e in events if e.get("match", False))
    substituted = total - matches

    model_counts: dict[str, int] = {}
    for e in events:
        m = e.get("observed_model", "UNKNOWN")
        model_counts[m] = model_counts.get(m, 0) + 1

    remediation_attempted = sum(1 for e in events if e.get("remediation_attempted", False))
    remediation_succeeded = sum(1 for e in events if e.get("remediation_succeeded", False))

    timestamps = [e.get("timestamp", "") for e in events if e.get("timestamp")]
    transitions = 0
    prev_model = None
    for e in events:
        m = e.get("observed_model")
        if m and m != prev_model:
            if prev_model is not None:
                transitions += 1
            prev_model = m

    desired = events[0].get("desired_model", TARGET_MODEL) if events else TARGET_MODEL

    return {
        "requested_model": desired,
        "total_observed": total,
        "target_matches": matches,
        "substituted_turns": substituted,
        "substitution_rate": f"{100 * substituted / total:.1f}%" if total > 0 else "0%",
        "observed_models": model_counts,
        "model_transitions": transitions,
        "first_observation": min(timestamps) if timestamps else "UNKNOWN",
        "last_observation": max(timestamps) if timestamps else "UNKNOWN",
        "remediation_attempts": remediation_attempted,
        "remediation_successes": remediation_succeeded,
        "remediation_rate": (
            f"{100 * remediation_succeeded / remediation_attempted:.0f}%"
            if remediation_attempted > 0
            else "N/A"
        ),
        "session_filter": session_id,
        "since_filter": since,
    }


def main() -> None:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        sid = sys.argv[2] if len(sys.argv) > 2 else None
        since = sys.argv[3] if len(sys.argv) > 3 else None
        summary = generate_summary(session_id=sid, since=since)
        print(json.dumps(summary, indent=2))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "health":
        if os.path.exists(HEALTH_FILE):
            with open(HEALTH_FILE, "r") as f:
                data = json.load(f)
            data["paused"] = os.path.exists(PAUSE_FILE)
            print(json.dumps(data, indent=2))
        else:
            print(json.dumps({"status": "no health data", "paused": os.path.exists(PAUSE_FILE)}, indent=2))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "pause":
        with open(PAUSE_FILE, "w") as f:
            f.write(f"Paused at {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
        print(
            "Model watchdog PAUSED — Claude discovery and remediation suppressed. "
            f"Remove {PAUSE_FILE} to resume."
        )
        return

    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        try:
            os.unlink(PAUSE_FILE)
            print("Model watchdog RESUMED — remediation active.")
        except FileNotFoundError:
            print("Model watchdog was not paused.")
        return

    watchdog = ModelWatchdog()
    watchdog.run()


if __name__ == "__main__":
    main()
