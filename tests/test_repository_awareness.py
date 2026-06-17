"""Tests for Campaign 6.1 — Repository Awareness Runtime."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.repository_awareness_runtime import (
    FileCategory,
    FileEntry,
    RepositoryAwarenessRuntime,
    RepositorySnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def runtime():
    return RepositoryAwarenessRuntime()


@pytest.fixture
def mock_repo(tmp_path):
    """Create a mock repository structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.ts").write_text("export {}")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "CLAUDE.md").write_text("# Dev Agent")
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11")
    (tmp_path / "pyproject.toml").write_text("[project]")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "seed.csv").write_text("a,b")
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra" / "main.tf").write_text("resource {}")
    (tmp_path / ".env.example").write_text("KEY=value")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_bytes(b"\x00")
    return tmp_path


# ── FileCategory Tests ────────────────────────────────────────────────────


class TestFileCategory:
    def test_enum_values(self):
        assert FileCategory.SOURCE_CODE.value == "source_code"
        assert FileCategory.TEST.value == "test"
        assert FileCategory.CONFIGURATION.value == "configuration"
        assert FileCategory.DOCUMENTATION.value == "documentation"
        assert FileCategory.BUILD.value == "build"
        assert FileCategory.DATA.value == "data"
        assert FileCategory.INFRASTRUCTURE.value == "infrastructure"
        assert FileCategory.UNKNOWN.value == "unknown"

    def test_is_str_enum(self):
        assert isinstance(FileCategory.SOURCE_CODE, str)
        assert FileCategory.SOURCE_CODE == "source_code"


# ── FileEntry Tests ───────────────────────────────────────────────────────


class TestFileEntry:
    def test_to_dict(self):
        entry = FileEntry(
            path="src/main.py",
            category=FileCategory.SOURCE_CODE.value,
            size_bytes=100,
            last_modified=1000.0,
            entity_refs=["proj-umh"],
        )
        d = entry.to_dict()
        assert d["path"] == "src/main.py"
        assert d["category"] == "source_code"
        assert d["entity_refs"] == ["proj-umh"]

    def test_default_entity_refs(self):
        entry = FileEntry(path="a.py", category="source_code", size_bytes=0, last_modified=0)
        assert entry.entity_refs == []

    def test_default_factory_isolation(self):
        e1 = FileEntry(path="a.py", category="source_code", size_bytes=0, last_modified=0)
        e2 = FileEntry(path="b.py", category="source_code", size_bytes=0, last_modified=0)
        e1.entity_refs.append("proj-x")
        assert "proj-x" not in e2.entity_refs


# ── RepositorySnapshot Tests ─────────────────────────────────────────────


class TestRepositorySnapshot:
    def test_to_dict(self):
        snap = RepositorySnapshot(
            repository_id="repo-test",
            name="test",
            root_path="/tmp/test",
            branch="main",
            file_count=5,
            files_by_category={"source_code": 3, "test": 2},
            important_files=[
                FileEntry(path="README.md", category="documentation", size_bytes=50, last_modified=1000.0),
            ],
            recent_changes=[{"hash": "abc123", "message": "init"}],
            detected_at=1000.0,
        )
        d = snap.to_dict()
        assert d["repository_id"] == "repo-test"
        assert d["file_count"] == 5
        assert len(d["important_files"]) == 1
        assert d["important_files"][0]["path"] == "README.md"

    def test_default_factory_isolation(self):
        s1 = RepositorySnapshot(
            repository_id="a", name="a", root_path="/a", branch="main", file_count=0
        )
        s2 = RepositorySnapshot(
            repository_id="b", name="b", root_path="/b", branch="main", file_count=0
        )
        s1.files_by_category["x"] = 1
        assert "x" not in s2.files_by_category


# ── Categorization Tests ─────────────────────────────────────────────────


class TestCategorization:
    def test_python_source(self, runtime):
        assert runtime.categorize_file("src/main.py") == "source_code"

    def test_typescript_source(self, runtime):
        assert runtime.categorize_file("components/App.tsx") == "source_code"

    def test_javascript_source(self, runtime):
        assert runtime.categorize_file("index.js") == "source_code"

    def test_go_source(self, runtime):
        assert runtime.categorize_file("main.go") == "source_code"

    def test_rust_source(self, runtime):
        assert runtime.categorize_file("lib.rs") == "source_code"

    def test_test_file_prefix(self, runtime):
        assert runtime.categorize_file("test_main.py") == "test"

    def test_test_file_suffix(self, runtime):
        assert runtime.categorize_file("main_test.go") == "test"

    def test_test_file_dot_test(self, runtime):
        assert runtime.categorize_file("App.test.tsx") == "test"

    def test_test_file_dot_spec(self, runtime):
        assert runtime.categorize_file("utils.spec.ts") == "test"

    def test_test_in_tests_dir(self, runtime):
        assert runtime.categorize_file("tests/conftest.py") == "test"

    def test_json_config(self, runtime):
        assert runtime.categorize_file("config.json") == "configuration"

    def test_yaml_config(self, runtime):
        assert runtime.categorize_file("docker-compose.yaml") == "configuration"

    def test_toml_config(self, runtime):
        assert runtime.categorize_file("pyproject.toml") == "configuration"

    def test_env_file(self, runtime):
        assert runtime.categorize_file(".env.example") == "configuration"

    def test_markdown_doc(self, runtime):
        assert runtime.categorize_file("README.md") == "documentation"

    def test_txt_doc(self, runtime):
        assert runtime.categorize_file("notes.txt") == "documentation"

    def test_dockerfile_build(self, runtime):
        assert runtime.categorize_file("Dockerfile") == "build"

    def test_dockerfile_variant_build(self, runtime):
        assert runtime.categorize_file("Dockerfile.prod") == "build"

    def test_makefile_build(self, runtime):
        assert runtime.categorize_file("Makefile") == "build"

    def test_shell_build(self, runtime):
        assert runtime.categorize_file("deploy.sh") == "build"

    def test_csv_data(self, runtime):
        assert runtime.categorize_file("data/seed.csv") == "data"

    def test_sql_data(self, runtime):
        assert runtime.categorize_file("migrations/001.sql") == "data"

    def test_terraform_infra(self, runtime):
        assert runtime.categorize_file("infra/main.tf") == "infrastructure"

    def test_unknown_extension(self, runtime):
        assert runtime.categorize_file("binary.exe") == "unknown"

    def test_no_extension(self, runtime):
        assert runtime.categorize_file("LICENSE") == "unknown"


# ── Important File Detection Tests ────────────────────────────────────────


class TestImportantFiles:
    def test_detects_readme(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        names = [f.path for f in files]
        assert "README.md" in names

    def test_detects_claude_md(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        names = [f.path for f in files]
        assert "CLAUDE.md" in names

    def test_detects_package_json(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        names = [f.path for f in files]
        assert "package.json" in names

    def test_detects_dockerfile(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        names = [f.path for f in files]
        assert "Dockerfile" in names

    def test_detects_env_example(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        names = [f.path for f in files]
        assert ".env.example" in names

    def test_includes_size(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        for f in files:
            assert f.size_bytes >= 0

    def test_includes_category(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        for f in files:
            assert f.category in [c.value for c in FileCategory]

    def test_empty_dir(self, runtime, tmp_path):
        files = runtime.detect_important_files(str(tmp_path))
        assert files == []

    def test_nonexistent_dir(self, runtime):
        files = runtime.detect_important_files("/nonexistent/path")
        assert files == []

    def test_no_duplicates(self, runtime, mock_repo):
        files = runtime.detect_important_files(str(mock_repo))
        paths = [f.path for f in files]
        assert len(paths) == len(set(paths))


# ── Repository Scan Tests ─────────────────────────────────────────────────


class TestRepositoryScan:
    def test_scan_counts_files(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        assert snap.file_count > 0

    def test_scan_excludes_git(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        assert snap.file_count > 0
        for f in snap.important_files:
            assert ".git" not in f.path

    def test_scan_excludes_pycache(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        all_cats = snap.files_by_category
        total = sum(all_cats.values())
        assert total == snap.file_count

    def test_scan_categorizes(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        assert "source_code" in snap.files_by_category
        assert snap.files_by_category["source_code"] >= 2

    def test_scan_sets_metadata(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        assert snap.name == mock_repo.name
        assert snap.root_path == str(mock_repo)
        assert snap.detected_at > 0

    def test_scan_finds_important_files(self, runtime, mock_repo):
        snap = runtime.scan_repository(str(mock_repo))
        names = [f.path for f in snap.important_files]
        assert "README.md" in names

    def test_scan_empty_repo(self, runtime, tmp_path):
        snap = runtime.scan_repository(str(tmp_path))
        assert snap.file_count == 0
        assert snap.files_by_category == {}


# ── Snapshot Tests ────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_empty_without_scan(self, runtime):
        assert runtime.snapshot() == {}

    def test_snapshot_returns_last_scan(self, runtime, mock_repo):
        runtime.scan_repository(str(mock_repo))
        s = runtime.snapshot()
        assert s["name"] == mock_repo.name
        assert s["file_count"] > 0


# ── Entity File Mapping Tests ─────────────────────────────────────────────


class TestEntityFileMapping:
    def test_no_graph_returns_empty(self, runtime, mock_repo):
        runtime.scan_repository(str(mock_repo))
        assert runtime.find_files_for_entity("proj-test") == []

    def test_no_scan_returns_empty(self):
        class MockGraph:
            def get(self, eid):
                return None
        rt = RepositoryAwarenessRuntime(reality_graph=MockGraph())
        assert rt.find_files_for_entity("proj-test") == []

    def test_finds_matching_files(self, mock_repo):
        class MockEntity:
            name = "README"

        class MockGraph:
            def get(self, eid):
                if eid == "doc-readme":
                    return MockEntity()
                return None

        rt = RepositoryAwarenessRuntime(reality_graph=MockGraph())
        rt.scan_repository(str(mock_repo))
        found = rt.find_files_for_entity("doc-readme")
        assert len(found) >= 1
        assert any("README" in f.path for f in found)
