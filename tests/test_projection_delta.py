"""Tests for projection delta engine."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from substrate.organism.self_use.projection_delta import (
    CapabilityState,
    DeltaReport,
    ProjectionCapability,
    ProjectionDelta,
    ProjectionDeltaEngine,
)


def test_capability_state():
    c = ProjectionCapability(name="Auth", desired=True, implemented=True, operational=True)
    assert c.state == CapabilityState.OPERATIONAL

    c2 = ProjectionCapability(name="Analytics", desired=True, implemented=True, operational=False)
    assert c2.state == CapabilityState.IMPLEMENTED

    c3 = ProjectionCapability(name="Mobile", desired=True, implemented=False, operational=False)
    assert c3.state == CapabilityState.DESIRED

    c4 = ProjectionCapability(name="Nothing", desired=False, implemented=False, operational=False)
    assert c4.state == CapabilityState.MISSING


def test_projection_delta_counts():
    delta = ProjectionDelta(
        projection_name="CreatorOS",
        capabilities=[
            ProjectionCapability(name="Auth", desired=True, implemented=True, operational=True),
            ProjectionCapability(
                name="Analytics", desired=True, implemented=True, operational=False
            ),
            ProjectionCapability(
                name="Content", desired=True, implemented=False, operational=False
            ),
            ProjectionCapability(
                name="Portfolio", desired=True, implemented=False, operational=False
            ),
        ],
    )
    assert delta.desired_count == 4
    assert delta.implemented_count == 2
    assert delta.operational_count == 1
    assert delta.missing_count == 3


def test_delta_report_markdown():
    report = DeltaReport(
        label="C27 Baseline",
        projections=[
            ProjectionDelta(
                projection_name="CreatorOS",
                capabilities=[
                    ProjectionCapability(
                        name="Auth", desired=True, implemented=True, operational=True
                    ),
                    ProjectionCapability(
                        name="Content", desired=True, implemented=False, operational=False
                    ),
                ],
            ),
            ProjectionDelta(
                projection_name="EntrepreneurOS",
                capabilities=[
                    ProjectionCapability(
                        name="Ventures", desired=True, implemented=True, operational=True
                    ),
                ],
            ),
        ],
    )
    md = report.to_markdown()
    assert "CreatorOS" in md
    assert "EntrepreneurOS" in md
    assert "C27 Baseline" in md


def test_engine_compare():
    engine = ProjectionDeltaEngine()

    baseline = DeltaReport(
        report_id="dr-baseline",
        label="Baseline",
        projections=[
            ProjectionDelta(
                projection_name="COS",
                capabilities=[
                    ProjectionCapability(
                        name="Auth", desired=True, implemented=True, operational=True
                    ),
                    ProjectionCapability(
                        name="Content", desired=True, implemented=False, operational=False
                    ),
                ],
            ),
        ],
    )
    engine.add_report(baseline)

    current = DeltaReport(
        report_id="dr-current",
        label="Post-C27",
        projections=[
            ProjectionDelta(
                projection_name="COS",
                capabilities=[
                    ProjectionCapability(
                        name="Auth", desired=True, implemented=True, operational=True
                    ),
                    ProjectionCapability(
                        name="Content", desired=True, implemented=True, operational=True
                    ),
                ],
            ),
        ],
    )
    engine.add_report(current)

    comparison = engine.compare("dr-baseline", "dr-current")
    assert comparison["comparisons"][0]["delta"] == 1
    assert comparison["comparisons"][0]["operational_before"] == 1
    assert comparison["comparisons"][0]["operational_after"] == 2


def test_engine_json_roundtrip():
    engine = ProjectionDeltaEngine()
    engine.add_report(
        DeltaReport(
            report_id="dr-test",
            label="Test",
            projections=[
                ProjectionDelta(
                    projection_name="COS",
                    capabilities=[
                        ProjectionCapability(
                            name="Auth", desired=True, implemented=True, operational=False
                        ),
                    ],
                ),
            ],
        )
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        engine.save(path)
        restored = ProjectionDeltaEngine.load(path)
        assert len(restored.reports) == 1
        report = restored.reports[0]
        assert report.projections[0].projection_name == "COS"
        assert report.projections[0].implemented_count == 1
        assert report.projections[0].operational_count == 0
    finally:
        os.unlink(path)


def test_engine_missing_report():
    engine = ProjectionDeltaEngine()
    result = engine.compare("nonexistent", "also-not-there")
    assert "error" in result


def test_capability_to_dict():
    c = ProjectionCapability(
        name="Publishing",
        description="Publish content",
        desired=True,
        implemented=True,
        operational=False,
        source="Drive doc",
    )
    d = c.to_dict()
    assert d["name"] == "Publishing"
    assert d["state"] == "implemented"
    assert d["source"] == "Drive doc"


def test_delta_report_to_dict():
    report = DeltaReport(
        label="Test",
        projections=[
            ProjectionDelta(
                projection_name="EOS",
                capabilities=[
                    ProjectionCapability(
                        name="Offers", desired=True, implemented=True, operational=True
                    ),
                ],
            ),
        ],
    )
    d = report.to_dict()
    assert d["label"] == "Test"
    assert d["projections"][0]["desired"] == 1
    assert d["projections"][0]["operational"] == 1
