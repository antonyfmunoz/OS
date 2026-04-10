"""
App launch allow-list for LAUNCH_APP actions.

The substrate's trust boundary forbids raw executable paths and arbitrary
shell. The daemon is only allowed to launch apps whose `app_id` appears in
this allow-list, and only by probing the declared candidate binaries with
`shutil.which`. No shell interpretation, no user-supplied paths, no args
beyond what callers pass as a list.

To add a new app:
  1. Add a new entry to APP_ALLOWLIST with a clear `app_id` slug.
  2. Provide the platform-appropriate candidate binaries in preference order.
  3. (Optional) Add default_args as a list of strings.

This file is deliberately small. Widening is a deliberate, reviewable change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AllowedApp:
    app_id: str
    candidates: tuple[str, ...]          # binary names probed via shutil.which
    default_args: tuple[str, ...] = ()   # always-applied args, never user-supplied
    description: str = ""


APP_ALLOWLIST: dict[str, AllowedApp] = {
    "vscode": AllowedApp(
        app_id="vscode",
        candidates=("code", "code-insiders"),
        description="Visual Studio Code editor",
    ),
    "chrome": AllowedApp(
        app_id="chrome",
        candidates=("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
        description="Chromium-family browser",
    ),
    "firefox": AllowedApp(
        app_id="firefox",
        candidates=("firefox",),
        description="Firefox browser",
    ),
    "terminal": AllowedApp(
        app_id="terminal",
        candidates=("gnome-terminal", "konsole", "xterm"),
        description="Default terminal emulator",
    ),
    "notion": AllowedApp(
        app_id="notion",
        candidates=("notion-app", "notion"),
        description="Notion desktop client",
    ),
    "discord": AllowedApp(
        app_id="discord",
        candidates=("discord",),
        description="Discord desktop client",
    ),
}


def resolve_app(app_id: str) -> AllowedApp | None:
    return APP_ALLOWLIST.get(app_id)


def is_allowed(app_id: str) -> bool:
    return app_id in APP_ALLOWLIST
