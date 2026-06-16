"""UMH Workstation Translator — Beast payload → canonical ScreenSnapshot.

Phase 34. Translates raw workstation observation payloads from Beast daemon
into Phase 33 ScreenSnapshot objects using existing types. No new type system.

The translator bridges:
  Beast dict payload → FocusedApplication, ActiveWindow, RepositoryContext,
                       FileContext, BrowserContext → ScreenSnapshot

Rich workstation detail (monitors, all windows, terminals) passes through
via ScreenSnapshot.workstation_detail for cockpit display.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from substrate.operator.screen_awareness import (
    ActiveWindow,
    ApplicationCategory,
    BrowserContext,
    FileContext,
    FocusedApplication,
    RepositoryContext,
    ScreenContextStatus,
    ScreenSnapshot,
    ScreenSourceType,
)

logger = logging.getLogger(__name__)

_APP_CATEGORY: dict[str, ApplicationCategory] = {
    "code.exe": ApplicationCategory.IDE,
    "code": ApplicationCategory.IDE,
    "cursor.exe": ApplicationCategory.IDE,
    "cursor": ApplicationCategory.IDE,
    "visual studio code": ApplicationCategory.IDE,
    "jetbrains": ApplicationCategory.IDE,
    "pycharm": ApplicationCategory.IDE,
    "webstorm": ApplicationCategory.IDE,
    "chrome.exe": ApplicationCategory.BROWSER,
    "chrome": ApplicationCategory.BROWSER,
    "msedge.exe": ApplicationCategory.BROWSER,
    "edge": ApplicationCategory.BROWSER,
    "firefox.exe": ApplicationCategory.BROWSER,
    "firefox": ApplicationCategory.BROWSER,
    "brave.exe": ApplicationCategory.BROWSER,
    "brave": ApplicationCategory.BROWSER,
    "windowsterminal.exe": ApplicationCategory.TERMINAL,
    "powershell.exe": ApplicationCategory.TERMINAL,
    "cmd.exe": ApplicationCategory.TERMINAL,
    "wt.exe": ApplicationCategory.TERMINAL,
    "alacritty.exe": ApplicationCategory.TERMINAL,
    "discord.exe": ApplicationCategory.COMMUNICATION,
    "discord": ApplicationCategory.COMMUNICATION,
    "slack.exe": ApplicationCategory.COMMUNICATION,
    "slack": ApplicationCategory.COMMUNICATION,
    "teams.exe": ApplicationCategory.COMMUNICATION,
    "figma.exe": ApplicationCategory.DESIGN,
    "figma": ApplicationCategory.DESIGN,
    "photoshop.exe": ApplicationCategory.DESIGN,
}


def classify_application(app_name: str) -> ApplicationCategory:
    """Classify app name to ApplicationCategory. Deterministic lookup, no LLM."""
    if not app_name:
        return ApplicationCategory.OTHER
    key = app_name.lower().strip()
    if key in _APP_CATEGORY:
        return _APP_CATEGORY[key]
    for pattern, cat in _APP_CATEGORY.items():
        if pattern in key:
            return cat
    return ApplicationCategory.OTHER


class WorkstationTranslator:
    """Translates Beast workstation payload → canonical ScreenSnapshot.

    No new types — uses Phase 33 FocusedApplication, ActiveWindow,
    RepositoryContext, FileContext, BrowserContext, ScreenSnapshot.
    """

    def translate(self, node_id: str, payload: dict[str, Any]) -> ScreenSnapshot:
        """Convert Beast workstation state dict into a ScreenSnapshot."""
        windows = payload.get("windows", [])
        focused_id = str(payload.get("active_window_id", ""))

        focused = self._find_focused(windows, focused_id)

        active_app = self._to_focused_application(focused) if focused else None
        active_window = self._to_active_window(focused) if focused else None
        applications = [
            self._to_focused_application(w) for w in windows if w.get("is_visible", False)
        ]

        editor = payload.get("editor_context")
        file_ctx = self._editor_to_file_context(editor) if editor else None
        repo_ctx = self._editor_to_repo_context(editor) if editor else None

        tabs = payload.get("browser_tabs", [])
        browser_ctx = self._tabs_to_browser_context(tabs)

        return ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_node_id=node_id,
            source_device_id=payload.get("device_id", ""),
            source_device_role="workstation",
            source_confidence=0.9,
            active_application=active_app,
            active_window=active_window,
            repository_context=repo_ctx,
            file_context=file_ctx,
            browser_context=browser_ctx,
            applications=applications,
            workstation_detail={
                "monitors": payload.get("monitors", []),
                "all_windows": windows,
                "editor_context": editor,
                "browser_tabs": tabs,
                "terminal_sessions": payload.get("terminal_sessions", []),
            },
            generated_at=payload.get("collected_at", time.time()),
        )

    def _find_focused(
        self, windows: list[dict[str, Any]], focused_id: str
    ) -> dict[str, Any] | None:
        if focused_id:
            for w in windows:
                if str(w.get("window_id", "")) == focused_id:
                    return w
        for w in windows:
            if w.get("is_focused", False):
                return w
        return None

    def _to_focused_application(self, win: dict[str, Any]) -> FocusedApplication:
        app_name = win.get("app_name", "") or win.get("application", "")
        category = classify_application(app_name)
        cat_raw = win.get("category", "")
        if cat_raw:
            try:
                category = ApplicationCategory(cat_raw)
            except ValueError:
                pass

        return FocusedApplication(
            app_name=app_name,
            category=category,
            pid=win.get("pid", 0),
            window_title=win.get("title", ""),
            is_focused=win.get("is_focused", False),
        )

    def _to_active_window(self, win: dict[str, Any]) -> ActiveWindow:
        return ActiveWindow(
            window_id=str(win.get("window_id", "")),
            title=win.get("title", ""),
            application=win.get("app_name", "") or win.get("application", ""),
            is_active=win.get("is_focused", True),
        )

    def _editor_to_file_context(self, editor: dict[str, Any]) -> FileContext | None:
        active_file = editor.get("active_file", "")
        if not active_file:
            return None
        name = os.path.basename(active_file)
        ext = os.path.splitext(name)[1].lstrip(".")
        return FileContext(
            file_path=active_file,
            file_name=name,
            repo_name=editor.get("workspace_name", ""),
            language=ext,
        )

    def _editor_to_repo_context(self, editor: dict[str, Any]) -> RepositoryContext | None:
        workspace = editor.get("workspace_name", "")
        project_path = editor.get("project_path", "")
        if not workspace and not project_path:
            return None
        return RepositoryContext(
            repo_name=workspace,
            repo_path=project_path,
            branch=editor.get("git_branch", ""),
            active_file=editor.get("active_file", ""),
        )

    def _tabs_to_browser_context(self, tabs: list[dict[str, Any]]) -> BrowserContext | None:
        active = None
        for t in tabs:
            if t.get("is_active", False):
                active = t
                break
        if active is None and tabs:
            active = tabs[0]
        if active is None:
            return None
        return BrowserContext(
            url=active.get("url", ""),
            title=active.get("title", ""),
            domain=active.get("domain", ""),
        )
