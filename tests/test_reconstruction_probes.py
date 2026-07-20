"""Tests for the reconstruction runtime-probes acquisition module."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction.provenance import content_hash
from substrate.understanding.reconstruction.runtime_probes import (
    PROBES,
    ProbeCollection,
    ProbeSpec,
    collect_runtime_observations,
    redact,
)


class _FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestRedaction:
    def test_redacts_env_assignment(self):
        out, applied = redact("ANTHROPIC_API_KEY=sk-abcdefghijklmnopqrstuvwxyz012345")
        assert applied is True
        assert "sk-abcdef" not in out
        assert "[REDACTED]" in out
        # the key NAME is preserved
        assert "ANTHROPIC_API_KEY" in out

    def test_redacts_bearer_token(self):
        out, applied = redact("Authorization: Bearer abc.def.ghijklmnop")
        assert applied is True
        assert "[REDACTED]" in out
        assert "abc.def.ghi" not in out

    def test_redacts_op_uri(self):
        out, applied = redact("secret at op://vault/item/field here")
        assert applied is True
        assert "op://vault/item/field" not in out
        assert "[REDACTED]" in out

    def test_redacts_long_hex_run(self):
        token = "a" * 40
        out, applied = redact(f"hash {token} done")
        assert applied is True
        assert token not in out

    def test_clean_text_untouched(self):
        out, applied = redact("nothing secret here just words")
        assert applied is False
        assert out == "nothing secret here just words"


class TestTruncation:
    def test_truncation_marker_applied(self):
        big_line = "word " * 100  # 500 bytes, survives redaction (no >=32 run)
        spec = ProbeSpec(
            name="git_status",
            command=("git", "status", "--porcelain"),
            timeout_seconds=1.0,
            max_output_bytes=100,
            description="t",
        )

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=big_line)

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        assert coll.probe_results[0]["truncated"] is True


class TestProbeUnavailability:
    def test_gate_none_marks_unavailable(self):
        spec = PROBES[0]

        def fake_runner(s, root):
            return None  # simulate CPU-gate block / missing binary

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        assert coll.probe_results[0]["available"] is False
        # explicit unavailable observation, does not raise
        unavail = [o for o in coll.observations if o.predicate == "probe_unavailable"]
        assert len(unavail) == 1
        # V4.1 correction 13: probe_status kind, NO maturity facet asserted
        assert unavail[0].observation_kind == "probe_status"
        assert unavail[0].maturity_facet is None
        # the probe ATTEMPT is recorded as one derived source (marked unavailable)
        assert len(coll.sources) == 1
        assert coll.sources[0].metadata.get("available") is False
        assert coll.sources[0].source_content_hash == ""  # nothing was acquired
        assert coll.sources[0].derivation_key  # attempt identity, not content
        assert unavail[0].source_id == coll.sources[0].id

    def test_runner_exception_does_not_crash(self):
        spec = PROBES[0]

        def boom(s, root):
            raise RuntimeError("kaboom")

        coll = collect_runtime_observations("R", "A", runner=boom, probes=(spec,), now="N")
        assert coll.probe_results[0]["available"] is False
        assert "runner_error" in (coll.probe_results[0]["error"] or "")

    def test_nonzero_exit_is_unavailable(self):
        spec = PROBES[0]

        def fake_runner(s, root):
            return _FakeProc(returncode=1, stdout="", stderr="fatal: not a git repo")

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        assert coll.probe_results[0]["available"] is False
        assert "nonzero_exit:1" in (coll.probe_results[0]["error"] or "")


class TestDockerFacetMapping:
    def test_up_line_parses_to_running_observation(self):
        spec = ProbeSpec(
            name="docker_services",
            command=("docker", "ps", "--format", "{{.Names}}\t{{.Status}}"),
            timeout_seconds=1.0,
            max_output_bytes=4096,
            description="t",
        )
        fixture = "os-discord\tUp 3 hours\nos-scraper\tExited (0) 2 minutes ago\n"

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=fixture)

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        running = [
            o
            for o in coll.observations
            if o.subject == "service:os-discord" and o.maturity_facet == "running"
        ]
        assert len(running) == 1
        # exited container is NOT asserted running
        exited = [o for o in coll.observations if o.subject == "service:os-scraper"]
        assert exited and all(o.maturity_facet != "running" for o in exited)

    def test_probe_source_hashes_actual_output(self):
        spec = ProbeSpec(
            name="docker_services",
            command=("docker", "ps", "--format", "{{.Names}}\t{{.Status}}"),
            timeout_seconds=1.0,
            max_output_bytes=4096,
            description="t",
        )
        fixture = "os-discord\tUp 3 hours\n"

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=fixture)

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        # the source hash is the hash of the REAL (redacted) captured output
        assert coll.sources[0].source_content_hash == content_hash(fixture)

    def test_listening_ports_not_reachable_facet(self):
        spec = ProbeSpec(
            name="listening_ports",
            command=("ss", "-tln"),
            timeout_seconds=1.0,
            max_output_bytes=4096,
            description="t",
        )
        fixture = (
            "State  Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
            "LISTEN 0      4096   127.0.0.1:8094     0.0.0.0:*\n"
        )

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=fixture)

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        ports = [o for o in coll.observations if o.predicate == "listening_ports"]
        assert len(ports) == 1
        assert ports[0].maturity_facet == "running"  # never 'reachable'
        assert "127.0.0.1:8094" in ports[0].value


class TestImportCheckFacet:
    def test_import_ok_maps_to_importable(self):
        spec = ProbeSpec(
            name="python_import_check",
            command=("python3", "-c", "print('IMPORT_OK')"),
            timeout_seconds=1.0,
            max_output_bytes=4096,
            description="t",
        )

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout="IMPORT_OK\n")

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        imp = [o for o in coll.observations if o.predicate == "import_check"]
        assert len(imp) == 1
        assert imp[0].maturity_facet == "importable"
        assert imp[0].value is True


class TestRepositoryStateKind:
    def test_git_head_is_repository_state_not_maturity(self):
        """A HEAD sha describes repository state, not component maturity —
        observation_kind='repository_state', maturity_facet=None."""
        git_head_spec = next(p for p in PROBES if p.name == "git_head")
        sha = "e3be2b9c86e5801582e7933682ab45263421ba34"

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=sha + "\n")

        coll = collect_runtime_observations(
            "R", "A", runner=fake_runner, probes=(git_head_spec,), now="N"
        )
        head_obs = [o for o in coll.observations if o.predicate == "head_commit"]
        assert len(head_obs) == 1
        assert head_obs[0].observation_kind == "repository_state"
        assert head_obs[0].maturity_facet is None


class TestCollectionShape:
    def test_returns_probe_collection(self):
        def fake_runner(s, root):
            return None

        coll = collect_runtime_observations("R", "A", runner=fake_runner, now="N")
        assert isinstance(coll, ProbeCollection)
        # one probe_result per allowlisted probe
        assert len(coll.probe_results) == len(PROBES)

    def test_source_redaction_status_reflects_redaction(self):
        spec = ProbeSpec(
            name="git_status",
            command=("git", "status", "--porcelain"),
            timeout_seconds=1.0,
            max_output_bytes=4096,
            description="t",
        )

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout="TOKEN=secretsecretsecretsecretsecret12\n")

        coll = collect_runtime_observations("R", "A", runner=fake_runner, probes=(spec,), now="N")
        assert coll.probe_results[0]["redaction_applied"] is True
        assert coll.sources and coll.sources[0].redaction_status == "partial"


class TestGitHeadShaSurvivesRedaction:
    def test_git_head_sha_not_redacted_but_secrets_still_are(self):
        git_head_spec = next(p for p in PROBES if p.name == "git_head")
        assert git_head_spec.redact_long_runs is False
        sha = "e3be2b9c86e5801582e7933682ab45263421ba34"

        def fake_runner(s, root):
            return _FakeProc(returncode=0, stdout=sha + "\n")

        coll = collect_runtime_observations(
            "R", "A", runner=fake_runner, probes=(git_head_spec,), now="N"
        )
        head_obs = [o for o in coll.observations if o.predicate == "head_commit"]
        assert len(head_obs) == 1
        assert head_obs[0].value == sha  # real sha survives, not [REDACTED]

    def test_long_run_still_redacted_for_default_probes(self):
        out, applied = redact("plainhash " + ("a" * 40))
        assert applied is True and "[REDACTED]" in out
        # but skipping long-run leaves it (structured secrets would still go)
        out2, _ = redact("plainhash " + ("a" * 40), redact_long_runs=False)
        assert ("a" * 40) in out2
