"""Phase 14.11C — File browser safety + functionality tests.

Tests allowlist enforcement, traversal denial, source environment
labeling, read-only file access, and unavailable state handling.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.file_browser import (
    ALLOWED_ROOTS,
    DENIED_PATTERNS,
    BrowseResult,
    FileEntry,
    FileReadResult,
    browse_directory,
    read_file,
    _is_path_allowed,
    _detect_source_env,
    _detect_language,
    MAX_FILE_SIZE,
)


class TestAllowlist:
    def test_repo_root_is_allowed(self) -> None:
        assert _is_path_allowed("/opt/OS")

    def test_repo_subdir_is_allowed(self) -> None:
        assert _is_path_allowed("/opt/OS/substrate")

    def test_outside_repo_denied(self) -> None:
        assert not _is_path_allowed("/etc/passwd")

    def test_root_denied(self) -> None:
        assert not _is_path_allowed("/")

    def test_tmp_denied(self) -> None:
        assert not _is_path_allowed("/tmp")

    def test_home_denied(self) -> None:
        assert not _is_path_allowed("/root")


class TestTraversalDenial:
    def test_dotdot_traversal_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/../etc/passwd")

    def test_dotdot_within_repo_resolves(self) -> None:
        result = _is_path_allowed("/opt/OS/substrate/../substrate")
        assert result is True

    def test_symlink_outside_repo_denied(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            link = os.path.join(d, "evil_link")
            os.symlink("/etc/passwd", link)
            assert not _is_path_allowed(link)


class TestDeniedPatterns:
    def test_git_objects_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/.git/objects")

    def test_node_modules_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/node_modules/foo")

    def test_pycache_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/__pycache__/file.pyc")

    def test_env_file_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/.env")

    def test_credentials_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/credentials/key.json")

    def test_worktrees_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/.claude/worktrees/foo")

    def test_secrets_denied(self) -> None:
        assert not _is_path_allowed("/opt/OS/secrets/api_key.txt")


class TestBrowseDirectory:
    def test_browse_repo_root(self) -> None:
        result = browse_directory("/opt/OS")
        assert result.ok is True
        assert result.source_env != ""
        assert len(result.entries) > 0
        names = [e.name for e in result.entries]
        assert "substrate" in names

    def test_browse_substrate(self) -> None:
        result = browse_directory("/opt/OS/substrate")
        assert result.ok is True
        names = [e.name for e in result.entries]
        assert "workstation" in names

    def test_browse_denied_path(self) -> None:
        result = browse_directory("/etc")
        assert result.ok is False
        assert "allowlist" in result.error.lower() or "denied" in result.error.lower()

    def test_browse_nonexistent(self) -> None:
        result = browse_directory("/opt/OS/nonexistent_dir_xyz")
        assert result.ok is False

    def test_entries_are_labeled(self) -> None:
        result = browse_directory("/opt/OS/substrate")
        assert result.ok is True
        for entry in result.entries:
            assert entry.source_env != ""
            assert entry.entry_type in ("file", "directory")

    def test_browse_filters_denied_children(self) -> None:
        result = browse_directory("/opt/OS")
        names = [e.name for e in result.entries]
        assert "__pycache__" not in names

    def test_to_dict(self) -> None:
        result = browse_directory("/opt/OS/substrate")
        d = result.to_dict()
        assert d["ok"] is True
        assert isinstance(d["entries"], list)
        if d["entries"]:
            assert "name" in d["entries"][0]
            assert "source_env" in d["entries"][0]


class TestReadFile:
    def test_read_allowed_file(self) -> None:
        result = read_file("/opt/OS/CLAUDE.md")
        assert result.ok is True
        assert len(result.content) > 0
        assert result.language == "markdown"

    def test_read_python_file(self) -> None:
        result = read_file("/opt/OS/substrate/workstation/mode_resolver.py")
        assert result.ok is True
        assert result.language == "python"
        assert "resolve_composite_mode" in result.content

    def test_read_denied_path(self) -> None:
        result = read_file("/etc/passwd")
        assert result.ok is False

    def test_read_nonexistent(self) -> None:
        result = read_file("/opt/OS/nonexistent_file.xyz")
        assert result.ok is False

    def test_read_directory_fails(self) -> None:
        result = read_file("/opt/OS/substrate")
        assert result.ok is False

    def test_to_dict(self) -> None:
        result = read_file("/opt/OS/CLAUDE.md")
        d = result.to_dict()
        assert d["ok"] is True
        assert "content" in d
        assert "language" in d


class TestSourceEnvironment:
    def test_source_env_detected(self) -> None:
        env = _detect_source_env()
        assert env in ("vps", "container", "windows", "macos", "unknown")

    def test_browse_includes_source_env(self) -> None:
        result = browse_directory("/opt/OS")
        assert result.source_env != ""


class TestLanguageDetection:
    def test_python(self) -> None:
        assert _detect_language("foo.py") == "python"

    def test_typescript(self) -> None:
        assert _detect_language("bar.ts") == "typescript"

    def test_tsx(self) -> None:
        assert _detect_language("comp.tsx") == "typescriptreact"

    def test_markdown(self) -> None:
        assert _detect_language("readme.md") == "markdown"

    def test_unknown(self) -> None:
        assert _detect_language("file.xyz") == "plaintext"

    def test_no_extension(self) -> None:
        assert _detect_language("Makefile") == "plaintext"


class TestWindowsUnavailable:
    def test_windows_path_denied(self) -> None:
        result = browse_directory("C:\\Users\\test")
        assert result.ok is False

    def test_windows_file_denied(self) -> None:
        result = read_file("C:\\Users\\test\\file.txt")
        assert result.ok is False


class TestFileEntry:
    def test_entry_creation(self) -> None:
        e = FileEntry(name="test.py", path="/opt/OS/test.py", entry_type="file", size=100, source_env="vps")
        assert e.name == "test.py"
        assert e.to_dict()["type"] == "file"

    def test_browse_result_error(self) -> None:
        r = BrowseResult(ok=False, error="test error")
        assert r.to_dict()["ok"] is False
        assert r.to_dict()["error"] == "test error"
