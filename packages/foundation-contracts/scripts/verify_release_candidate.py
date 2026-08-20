#!/usr/bin/env python3
"""Verify the foundation contract release candidate without network access."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SCOPE = [
    "Identity / CRM",
    "Messages",
    "Docs",
    "Files",
    "Databases",
    "Forms",
    "Calendar",
    "Finance",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schemas() -> list[dict[str, Any]]:
    return [load_json(path) for path in sorted((ROOT / "schemas").rglob("*.schema.json"))]


def refs_in(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        if "$ref" in value:
            refs.add(str(value["$ref"]))
        for child in value.values():
            refs.update(refs_in(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(refs_in(child))
    return refs


def fail(errors: list[str]) -> None:
    if errors:
        for error in errors:
            print(f"VERIFY_RELEASE_CANDIDATE_FAIL: {error}", file=sys.stderr)
        sys.exit(1)
    print("foundation release candidate verification PASS")


def main() -> None:
    errors: list[str] = []
    package_json = load_json(ROOT / "package.json")
    artifact = load_json(ROOT / "generated" / "artifact-manifest.v1.json")
    qualification = load_json(ROOT / "generated" / "qualification.v1.json")
    release = load_json(ROOT / "release" / "consumption.v1.json")
    commands = load_json(ROOT / "registry" / "commands.v1.json")
    events = load_json(ROOT / "registry" / "events.v1.json")
    aliases = load_json(ROOT / "registry" / "legacy-aliases.v1.json")

    if package_json["name"] != qualification["packageName"] or package_json["name"] != release["packageName"]:
        errors.append("package name mismatch")
    if package_json["version"] != qualification["packageVersion"] or package_json["version"] != release["packageVersion"]:
        errors.append("package version mismatch")
    if artifact["contractPackageVersion"] != package_json["version"]:
        errors.append("artifact manifest package version mismatch")
    if qualification["qualificationStatus"] != "QUALIFIED":
        errors.append("qualification status is not QUALIFIED")
    if qualification["qualificationScope"] != REQUIRED_SCOPE or release["qualifiedScope"] != REQUIRED_SCOPE:
        errors.append("qualified scope mismatch")
    if release["standaloneVendoringAllowed"] is not True:
        errors.append("standalone vendoring must be allowed")
    if release["consumerRequirements"]["gitSubmoduleDependency"] is not False:
        errors.append("git submodule dependency must be false")

    all_schemas = schemas()
    schema_ids = [schema["$id"] for schema in all_schemas]
    schema_titles = [schema["title"] for schema in all_schemas]
    if len(schema_ids) != len(set(schema_ids)):
        errors.append("duplicate schema id")
    if len(schema_titles) != len(set(schema_titles)):
        errors.append("duplicate schema title")
    schema_id_set = set(schema_ids)
    for schema in all_schemas:
        for ref in refs_in(schema):
            if ref not in schema_id_set:
                errors.append(f"unresolved schema ref: {ref}")

    commands_by_type = {command["commandType"]: command for command in commands["commands"]}
    events_by_type = {event["eventType"]: event for event in events["events"]}
    if len(commands_by_type) != len(commands["commands"]):
        errors.append("duplicate command type")
    if len(events_by_type) != len(events["events"]):
        errors.append("duplicate event type")

    schemas_by_id = {schema["$id"]: schema for schema in all_schemas}
    for command_type, command in commands_by_type.items():
        if command["envelopeSchema"] not in schemas_by_id:
            errors.append(f"command envelope ref unresolved: {command_type}")
        payload = schemas_by_id.get(command["payloadSchema"])
        if not payload:
            errors.append(f"command payload ref unresolved: {command_type}")
        elif payload.get("x-umh", {}).get("commandType") != command_type:
            errors.append(f"command payload type drift: {command_type}")
        for event_type in command["expectedEventTypes"]:
            if event_type not in events_by_type:
                errors.append(f"expected event missing: {command_type}->{event_type}")

    for event_type, event in events_by_type.items():
        if event["envelopeSchema"] not in schemas_by_id:
            errors.append(f"event envelope ref unresolved: {event_type}")
        payload = schemas_by_id.get(event["payloadSchema"])
        if not payload:
            errors.append(f"event payload ref unresolved: {event_type}")
        elif payload.get("x-umh", {}).get("eventType") != event_type:
            errors.append(f"event payload type drift: {event_type}")

    canonical_targets = set(commands_by_type) | set(events_by_type) | set(schema_titles)
    canonical_targets.update(schema.get("x-umh", {}).get("canonicalName") for schema in all_schemas)
    for alias in aliases["aliases"]:
        if alias["status"] != "migration-alias-only":
            errors.append(f"alias is not migration-only: {alias['legacyName']}")
        if alias["canonicalName"] not in canonical_targets:
            errors.append(f"alias target unresolved: {alias['legacyName']}")

    actual_digests = {
        "artifactManifest": sha256_file(ROOT / "generated" / "artifact-manifest.v1.json"),
        "commandRegistry": sha256_file(ROOT / "registry" / "commands.v1.json"),
        "eventRegistry": sha256_file(ROOT / "registry" / "events.v1.json"),
        "aliasRegistry": sha256_file(ROOT / "registry" / "legacy-aliases.v1.json"),
        "compatibilityRegistry": sha256_file(ROOT / "registry" / "compatibility.v1.json"),
        "generatorSource": sha256_file(ROOT / "scripts" / "generate_bindings.py"),
        "generatedPythonModels": sha256_file(ROOT / "generated" / "python" / "foundation_contracts" / "models.py"),
        "generatedPythonInit": sha256_file(ROOT / "generated" / "python" / "foundation_contracts" / "__init__.py"),
        "generatedTypeScriptSource": sha256_file(ROOT / "generated" / "typescript" / "index.ts"),
        "generatedTypeScriptRuntime": sha256_file(ROOT / "generated" / "typescript" / "index.mjs"),
    }
    for key, digest in actual_digests.items():
        if qualification["digests"].get(key) != digest:
            errors.append(f"qualification digest mismatch: {key}")

    artifact_generated = artifact["generatedArtifacts"]
    if artifact_generated["pythonModels"] != actual_digests["generatedPythonModels"]:
        errors.append("artifact manifest python model digest mismatch")
    if artifact_generated["pythonInit"] != actual_digests["generatedPythonInit"]:
        errors.append("artifact manifest python init digest mismatch")
    if artifact_generated["typescriptSource"] != actual_digests["generatedTypeScriptSource"]:
        errors.append("artifact manifest TypeScript source digest mismatch")
    if artifact_generated["typescriptRuntime"] != actual_digests["generatedTypeScriptRuntime"]:
        errors.append("artifact manifest TypeScript runtime digest mismatch")

    expected_counts = {
        "schemaCount": len(all_schemas),
        "commandCount": len(commands["commands"]),
        "eventCount": len(events["events"]),
        "aliasCount": len(aliases["aliases"]),
    }
    for key, value in expected_counts.items():
        if artifact.get(key) != value and key != "aliasCount":
            errors.append(f"artifact count mismatch: {key}")
        if qualification.get(key) != value:
            errors.append(f"qualification count mismatch: {key}")

    for path_key in [
        "canonicalSchemaRoot",
        "commandRegistry",
        "eventRegistry",
        "aliasRegistry",
        "compatibilityRegistry",
        "artifactManifest",
        "qualificationManifest",
    ]:
        if not (ROOT / release[path_key]).exists():
            errors.append(f"release manifest path missing: {path_key}")

    fail(errors)


if __name__ == "__main__":
    main()
