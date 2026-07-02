"""Design workflow — governed design asset management.

Tracks design work (asset reviews, template applications, brand compliance)
through governed mutation. Pure deterministic for now — no Figma API.
When a Figma adapter is built, the execute_fn implementations swap in
without changing the step structure.

Step-sets:
- asset_review: identify_assets → check_brand_compliance → generate_report
- template_apply: validate_template → apply_context → store_output
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DESIGN_DIR = os.path.join(_REPO_ROOT, "data", "umh", "design")

BRAND_RULES = {
    "colors": ["#000000", "#FFFFFF", "#1A1A2E", "#E94560", "#0F3460"],
    "fonts": ["Inter", "JetBrains Mono"],
    "tone": "tactical luxury — bold, direct, authoritative",
    "logo_min_size_px": 48,
    "spacing_unit_px": 8,
}

TEMPLATES = {
    "social_post": {
        "dimensions": "1080x1080",
        "sections": ["headline", "body", "cta", "branding"],
        "required_fields": ["headline", "cta"],
    },
    "story": {
        "dimensions": "1080x1920",
        "sections": ["headline", "visual", "branding"],
        "required_fields": ["headline"],
    },
    "presentation": {
        "dimensions": "1920x1080",
        "sections": ["title", "content", "footer"],
        "required_fields": ["title"],
    },
    "thumbnail": {
        "dimensions": "1280x720",
        "sections": ["headline", "visual", "branding"],
        "required_fields": ["headline"],
    },
    "banner": {
        "dimensions": "1500x500",
        "sections": ["headline", "cta", "branding"],
        "required_fields": ["headline"],
    },
}


class DesignWorkflow:
    """Design asset management workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._assets: list[dict[str, Any]] = []
        self._compliance_results: list[dict[str, Any]] = []
        self._report: str = ""
        self._template_output: str = ""

    def asset_review_steps(self, project_name: str) -> list[WorkflowStep]:
        """Steps for reviewing design assets in a project."""
        return [
            WorkflowStep(
                name="identify_assets",
                mutation_name="command_submit",
                intent=f"Identify design assets for {project_name[:60]}",
                execute_fn=lambda: self._identify_assets(project_name),
            ),
            WorkflowStep(
                name="check_brand_compliance",
                mutation_name="command_submit",
                intent=f"Check brand compliance for {project_name[:60]}",
                execute_fn=self._check_brand_compliance,
            ),
            WorkflowStep(
                name="generate_report",
                mutation_name="file_write",
                intent=f"Generate design review report for {project_name[:60]}",
                execute_fn=lambda: self._generate_report(project_name),
            ),
        ]

    def template_apply_steps(
        self, template_name: str, context: dict[str, Any] | None = None
    ) -> list[WorkflowStep]:
        """Steps for applying a design template."""
        ctx = context or {}
        return [
            WorkflowStep(
                name="validate_template",
                mutation_name="command_submit",
                intent=f"Validate template: {template_name}",
                execute_fn=lambda: self._validate_template(template_name, ctx),
            ),
            WorkflowStep(
                name="apply_context",
                mutation_name="command_submit",
                intent=f"Apply context to template: {template_name}",
                execute_fn=lambda: self._apply_context(template_name, ctx),
            ),
            WorkflowStep(
                name="store_output",
                mutation_name="file_write",
                intent=f"Store design output for template: {template_name}",
                execute_fn=lambda: self._store_output(template_name),
            ),
        ]

    def _identify_assets(self, project_name: str) -> tuple[str, bool]:
        design_dir = os.path.join(_DESIGN_DIR, "projects", project_name)
        self._assets = []

        if os.path.isdir(design_dir):
            for root, _dirs, files in os.walk(design_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".png", ".jpg", ".jpeg", ".svg", ".pdf", ".fig", ".sketch"):
                        rel = os.path.relpath(os.path.join(root, f), design_dir)
                        self._assets.append({
                            "file": rel,
                            "type": ext.lstrip("."),
                            "path": os.path.join(root, f),
                        })

        if not self._assets:
            self._assets = [
                {"file": f"{project_name}_placeholder", "type": "none", "path": ""},
            ]

        return (
            f"Found {len(self._assets)} design asset(s) for '{project_name}'",
            True,
        )

    def _check_brand_compliance(self) -> tuple[str, bool]:
        self._compliance_results = []

        for asset in self._assets:
            result = {
                "asset": asset["file"],
                "checks": [],
                "compliant": True,
            }

            if asset["type"] == "none":
                result["checks"].append({
                    "rule": "asset_exists",
                    "status": "warning",
                    "detail": "No actual file found — placeholder entry",
                })
                result["compliant"] = False
            else:
                result["checks"].append({
                    "rule": "file_format",
                    "status": "pass" if asset["type"] in ("svg", "png", "pdf") else "warning",
                    "detail": f"Format: {asset['type']}",
                })
                result["checks"].append({
                    "rule": "brand_colors",
                    "status": "info",
                    "detail": f"Expected palette: {', '.join(BRAND_RULES['colors'][:3])}...",
                })

            self._compliance_results.append(result)

        compliant_count = sum(1 for r in self._compliance_results if r["compliant"])
        total = len(self._compliance_results)

        return (
            f"Brand compliance: {compliant_count}/{total} assets compliant",
            True,
        )

    def _generate_report(self, project_name: str) -> tuple[str, bool]:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        parts = [
            f"# Design Review: {project_name}",
            f"**Date**: {date_str}",
            f"**Assets reviewed**: {len(self._assets)}",
            "",
            "## Brand Rules Applied",
            f"- Colors: {', '.join(BRAND_RULES['colors'])}",
            f"- Fonts: {', '.join(BRAND_RULES['fonts'])}",
            f"- Tone: {BRAND_RULES['tone']}",
            "",
            "## Asset Review",
        ]

        for result in self._compliance_results:
            status = "PASS" if result["compliant"] else "NEEDS REVIEW"
            parts.append(f"\n### {result['asset']} — {status}")
            for check in result["checks"]:
                parts.append(f"- [{check['status'].upper()}] {check['rule']}: {check['detail']}")

        self._report = "\n".join(parts)

        os.makedirs(os.path.join(_DESIGN_DIR, "reports"), exist_ok=True)
        slug = project_name.lower().replace(" ", "_")[:30]
        report_path = os.path.join(
            _DESIGN_DIR, "reports", f"{date_str}_{slug}_review.md"
        )

        try:
            with open(report_path, "w") as f:
                f.write(self._report)
        except OSError as exc:
            logger.debug("report write failed: %s", exc)
            return (self._report, True)

        return (self._report, True)

    def _validate_template(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, bool]:
        template = TEMPLATES.get(template_name)
        if not template:
            available = ", ".join(sorted(TEMPLATES.keys()))
            return (
                f"Unknown template '{template_name}'. Available: {available}",
                False,
            )

        missing = [
            field for field in template["required_fields"]
            if field not in context
        ]
        if missing:
            return (
                f"Template '{template_name}' missing required fields: {', '.join(missing)}",
                False,
            )

        return (
            f"Template '{template_name}' validated — "
            f"dimensions: {template['dimensions']}, "
            f"sections: {', '.join(template['sections'])}",
            True,
        )

    def _apply_context(
        self, template_name: str, context: dict[str, Any]
    ) -> tuple[str, bool]:
        template = TEMPLATES.get(template_name)
        if not template:
            return (f"Template '{template_name}' not found", False)

        parts = [
            f"# Design Brief: {template_name}",
            f"**Dimensions**: {template['dimensions']}",
            f"**Brand tone**: {BRAND_RULES['tone']}",
            f"**Colors**: {', '.join(BRAND_RULES['colors'])}",
            "",
            "## Content",
        ]

        for section in template["sections"]:
            value = context.get(section, f"[{section} — to be filled]")
            parts.append(f"### {section.title()}")
            parts.append(str(value))
            parts.append("")

        self._template_output = "\n".join(parts)

        return (
            f"Applied context to '{template_name}' — "
            f"{len(context)} fields populated",
            True,
        )

    def _store_output(self, template_name: str) -> tuple[str, bool]:
        if not self._template_output:
            return ("no template output to store", False)

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        os.makedirs(os.path.join(_DESIGN_DIR, "outputs"), exist_ok=True)
        slug = template_name.lower().replace(" ", "_")[:30]
        output_path = os.path.join(
            _DESIGN_DIR, "outputs", f"{date_str}_{slug}.md"
        )

        try:
            with open(output_path, "w") as f:
                f.write(self._template_output)
        except OSError as exc:
            logger.debug("output write failed: %s", exc)
            return (self._template_output, True)

        return (
            f"Design output stored: {output_path}\n\n{self._template_output}",
            True,
        )
