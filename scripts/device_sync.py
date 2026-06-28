#!/usr/bin/env python3
"""Post-commit hook: push to GitHub, pull on Beast.

Runs after every git commit on VPS to keep both devices in sync.
Exits 0 always — sync failures are logged but never block the session.
"""
import subprocess
import sys
import os
import json

REPO = "/opt/OS"
DEVICE_REGISTRY = os.path.join(REPO, "infra/device_registry.json")
LOG = os.path.join(REPO, "logs/device_sync.log")


def log(msg: str) -> None:
    import datetime
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    print(line, file=sys.stderr)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def get_beast_ssh() -> str | None:
    """Resolve Beast SSH target from device registry."""
    try:
        with open(DEVICE_REGISTRY) as f:
            registry = json.load(f)
        nodes = registry if isinstance(registry, list) else registry.get("nodes", [])
        for node in nodes:
            if node.get("role") == "executor":
                ip = node.get("tailscale_ip")
                user = node.get("ssh_user", "")
                if ip and user:
                    return f'"{user}@{ip}"'
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def run(cmd: list[str], timeout: int = 30, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, **kwargs
    )


def push_to_github() -> bool:
    """Push current branch to origin."""
    try:
        result = run(["git", "-C", REPO, "push", "origin", "main"], timeout=30)
        if result.returncode == 0:
            log("push: ok")
            return True
        log(f"push: failed — {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        log("push: timeout (30s)")
    except Exception as e:
        log(f"push: error — {e}")
    return False


def pull_on_beast(ssh_target: str) -> bool:
    """SSH to Beast and git pull. ssh_target includes quotes for spaces."""
    try:
        cmd = f'ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {ssh_target} "cd C:/dev/dev/OS && git pull origin main"'
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "up to date"
            log(f"beast pull: ok — {last_line}")
            return True
        log(f"beast pull: failed — {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        log("beast pull: timeout (30s)")
    except Exception as e:
        log(f"beast pull: error — {e}")
    return False


def main() -> None:
    branch_result = run(["git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

    if branch != "main":
        log(f"skip: branch is {branch}, not main")
        return

    pushed = push_to_github()
    if not pushed:
        log("skip beast pull — push failed")
        return

    beast_ssh = get_beast_ssh()
    if not beast_ssh:
        log("skip beast pull — no executor node in device registry")
        return

    pull_on_beast(beast_ssh)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"fatal: {e}")
    sys.exit(0)
