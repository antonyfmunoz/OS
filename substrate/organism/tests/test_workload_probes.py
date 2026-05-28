"""Tests for WorkloadProbes."""
from __future__ import annotations

import sys

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.workload_probes import (
    DiskProbe,
    DockerProbe,
    MemoryProbe,
    ProcessProbe,
    RepoProbe,
    WorkloadProbes,
)


def test_docker_probe_returns_structure():
    wp = WorkloadProbes()
    result = wp.probe_docker()
    assert isinstance(result, DockerProbe)
    assert result.probed_at > 0


def test_disk_probe():
    wp = WorkloadProbes()
    result = wp.probe_disk()
    assert isinstance(result, DiskProbe)
    assert result.total_gb > 0


def test_memory_probe():
    wp = WorkloadProbes()
    result = wp.probe_memory()
    assert isinstance(result, MemoryProbe)
    assert result.total_mb > 0


def test_repo_probe():
    wp = WorkloadProbes(repo_root="/opt/OS")
    result = wp.probe_repo()
    assert isinstance(result, RepoProbe)
    assert isinstance(result.branch, str)


def test_process_probe():
    wp = WorkloadProbes()
    result = wp.probe_processes()
    assert isinstance(result, ProcessProbe)
    assert result.probed_at > 0


def test_full_probe():
    wp = WorkloadProbes()
    result = wp.full_probe()
    assert "docker" in result
    assert "disk" in result
    assert "memory" in result
    assert "repo" in result
    assert "processes" in result


def test_cache():
    wp = WorkloadProbes()
    assert wp.cached == {}
    wp.full_probe()
    assert wp.cached != {}


def test_disk_probe_serialization():
    probe = DiskProbe(total_gb=50, used_gb=30, free_gb=20, usage_percent=60)
    d = probe.to_dict()
    assert d["total_gb"] == 50
    assert d["pressure"] == "normal"


def test_disk_pressure_levels():
    probe = DiskProbe(usage_percent=85)
    probe.pressure = "high"
    assert probe.pressure == "high"


def test_to_dict():
    wp = WorkloadProbes()
    d = wp.to_dict()
    assert "last_full_probe" in d


if __name__ == "__main__":
    test_docker_probe_returns_structure()
    test_disk_probe()
    test_memory_probe()
    test_repo_probe()
    test_process_probe()
    test_full_probe()
    test_cache()
    test_disk_probe_serialization()
    test_disk_pressure_levels()
    test_to_dict()
    print("ALL WORKLOAD PROBES TESTS PASSED")
