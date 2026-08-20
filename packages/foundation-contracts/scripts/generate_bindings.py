#!/usr/bin/env python3
"""Generate Python/Pydantic and TypeScript/Zod bindings from canonical schemas."""

from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
PY_OUT = ROOT / "generated" / "python" / "foundation_contracts"
TS_OUT = ROOT / "generated" / "typescript"
MANIFEST_OUT = ROOT / "generated" / "artifact-manifest.v1.json"
GENERATOR_VERSION = "1.1.1"
PY_NAME_OVERRIDES = {
    "EvidenceRef": "FoundationEvidenceRef",
}


def load_schemas() -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for path in sorted(SCHEMA_ROOT.rglob("*.schema.json")):
        schema = json.loads(path.read_text())
        schema["_source_path"] = str(path.relative_to(ROOT))
        schemas.append(schema)
    return schemas


def class_name(schema: dict[str, Any]) -> str:
    return str(schema["title"])


def py_class_name(schema: dict[str, Any]) -> str:
    return PY_NAME_OVERRIDES.get(class_name(schema), class_name(schema))


def schema_id(schema: dict[str, Any]) -> str:
    return str(schema["$id"])


def ref_name(ref: str, id_to_name: dict[str, str]) -> str:
    if ref not in id_to_name:
        raise ValueError(f"unknown $ref: {ref}")
    return id_to_name[ref]


def refs_in(schema_part: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(schema_part, dict):
        if "$ref" in schema_part:
            refs.add(str(schema_part["$ref"]))
        for value in schema_part.values():
            refs.update(refs_in(value))
    elif isinstance(schema_part, list):
        for item in schema_part:
            refs.update(refs_in(item))
    return refs


def dependency_order(schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {schema_id(schema): schema for schema in schemas}
    remaining = dict(by_id)
    emitted: set[str] = set()
    ordered: list[dict[str, Any]] = []

    while remaining:
        progressed = False
        for sid in sorted(list(remaining)):
            deps = {ref for ref in refs_in(remaining[sid]) if ref in by_id and ref != sid}
            if deps.issubset(emitted):
                ordered.append(remaining.pop(sid))
                emitted.add(sid)
                progressed = True
        if not progressed:
            unresolved = ", ".join(sorted(remaining))
            raise ValueError(f"cyclic or unresolved schema dependencies: {unresolved}")
    return ordered


def py_literal(value: Any) -> str:
    return repr(value)


def py_type_for(schema: dict[str, Any], id_to_name: dict[str, str], self_name: str) -> str:
    if "$ref" in schema:
        return ref_name(str(schema["$ref"]), id_to_name)
    if "const" in schema:
        return f"Literal[{py_literal(schema['const'])}]"
    if "enum" in schema:
        values = ", ".join(py_literal(v) for v in schema["enum"])
        return f"Literal[{values}]"
    if "oneOf" in schema:
        types = [py_type_for(item, id_to_name, self_name) for item in schema["oneOf"]]
        return " | ".join(types)

    typ = schema.get("type")
    if typ == "string":
        return "str"
    if typ == "integer":
        return "int"
    if typ == "number":
        return "float"
    if typ == "boolean":
        return "bool"
    if typ == "null":
        return "None"
    if typ == "array":
        item_type = py_type_for(schema.get("items", {"type": "object"}), id_to_name, self_name)
        return f"list[{item_type}]"
    if typ == "object":
        if "properties" in schema:
            return "dict[str, Any]"
        return "dict[str, Any]"
    return "Any"


def py_field_args(prop_schema: dict[str, Any], required: bool) -> str:
    args: list[str] = []
    if not required:
        args.append("default=None")
    if prop_schema.get("type") == "string":
        if "minLength" in prop_schema:
            args.append(f"min_length={int(prop_schema['minLength'])}")
        if "pattern" in prop_schema:
            args.append(f"pattern={prop_schema['pattern']!r}")
    if prop_schema.get("type") in {"integer", "number"}:
        if "minimum" in prop_schema:
            args.append(f"ge={prop_schema['minimum']!r}")
        if "maximum" in prop_schema:
            args.append(f"le={prop_schema['maximum']!r}")
    if prop_schema.get("type") == "array":
        if "minItems" in prop_schema:
            args.append(f"min_length={int(prop_schema['minItems'])}")
        if "maxItems" in prop_schema:
            args.append(f"max_length={int(prop_schema['maxItems'])}")
    return ", ".join(args)


def generate_python(schemas: list[dict[str, Any]]) -> None:
    id_to_name = {schema_id(schema): py_class_name(schema) for schema in schemas}
    ordered = dependency_order(schemas)
    lines = [
        '"""Generated foundation contract Pydantic models. Do not hand-edit."""',
        "",
        "from __future__ import annotations",
        "",
        "import re",
        "",
        "from typing import Any, Literal",
        "",
        "from pydantic import BaseModel, ConfigDict, Field, field_validator",
        "",
        "",
    ]
    exports: list[str] = []

    for schema in ordered:
        name = py_class_name(schema)
        exports.append(name)
        required = set(schema.get("required", []))
        lines.append(f"class {name}(BaseModel):")
        lines.append('    model_config = ConfigDict(extra="forbid")')
        props = schema.get("properties", {})
        if not props:
            lines.append("    pass")
        for field_name, prop_schema in props.items():
            field_required = field_name in required
            typ = py_type_for(prop_schema, id_to_name, name)
            if not field_required and "None" not in typ.split(" | "):
                typ = f"{typ} | None"
            args = py_field_args(prop_schema, field_required)
            if args:
                lines.append(f"    {field_name}: {typ} = Field({args})")
            elif field_required:
                lines.append(f"    {field_name}: {typ}")
            else:
                lines.append(f"    {field_name}: {typ} = None")
        for field_name, prop_schema in props.items():
            pattern = prop_schema.get("propertyNames", {}).get("pattern")
            if pattern:
                method_name = re.sub(r"[^0-9a-zA-Z_]", "_", f"_validate_{field_name}_property_names")
                lines.append("")
                lines.append(f"    @field_validator({field_name!r})")
                lines.append("    @classmethod")
                lines.append(f"    def {method_name}(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:")
                lines.append("        if value is None:")
                lines.append("            return value")
                lines.append(f"        pattern = re.compile({pattern!r})")
                lines.append("        invalid = [key for key in value if not pattern.match(key)]")
                lines.append("        if invalid:")
                lines.append("            raise ValueError(f'invalid extension namespace(s): {invalid}')")
                lines.append("        return value")
        lines.append("")
        lines.append("")

    lines.append(f"__all__ = {exports!r}")
    PY_OUT.mkdir(parents=True, exist_ok=True)
    (PY_OUT / "models.py").write_text("\n".join(lines) + "\n")
    (PY_OUT / "__init__.py").write_text(
        '"""Generated foundation contract Python bindings."""\n\n'
        "from .models import *\n"
        "from .models import __all__\n"
    )


def js_regex(pattern: str) -> str:
    escaped = pattern.replace("/", "\\/")
    return f"/{escaped}/"


def zod_expr_for(schema: dict[str, Any], id_to_name: dict[str, str], self_name: str) -> str:
    if "$ref" in schema:
        target = ref_name(str(schema["$ref"]), id_to_name)
        if target == self_name:
            return f"z.lazy(() => {target}Schema)"
        return f"{target}Schema"
    if "const" in schema:
        return f"z.literal({json.dumps(schema['const'])})"
    if "enum" in schema:
        return "z.enum([" + ", ".join(json.dumps(v) for v in schema["enum"]) + "])"
    if "oneOf" in schema:
        return "z.union([" + ", ".join(zod_expr_for(item, id_to_name, self_name) for item in schema["oneOf"]) + "])"

    typ = schema.get("type")
    if typ == "string":
        expr = "z.string()"
        if "minLength" in schema:
            expr += f".min({int(schema['minLength'])})"
        if "pattern" in schema:
            expr += f".regex({js_regex(str(schema['pattern']))})"
        if schema.get("format") == "date-time":
            expr += ".datetime()"
        return expr
    if typ == "integer":
        expr = "z.number().int()"
        if "minimum" in schema:
            expr += f".min({int(schema['minimum'])})"
        if "maximum" in schema:
            expr += f".max({int(schema['maximum'])})"
        return expr
    if typ == "number":
        expr = "z.number()"
        if "minimum" in schema:
            expr += f".min({schema['minimum']!r})"
        if "maximum" in schema:
            expr += f".max({schema['maximum']!r})"
        return expr
    if typ == "boolean":
        return "z.boolean()"
    if typ == "null":
        return "z.null()"
    if typ == "array":
        expr = f"z.array({zod_expr_for(schema.get('items', {'type': 'object'}), id_to_name, self_name)})"
        if "minItems" in schema:
            expr += f".min({int(schema['minItems'])})"
        return expr
    if typ == "object":
        if "properties" in schema:
            return "z.record(z.string(), z.unknown())"
        expr = "z.record(z.string(), z.unknown())"
        pattern = schema.get("propertyNames", {}).get("pattern")
        if pattern:
            expr += (
                f".refine((value) => Object.keys(value).every((key) => "
                f"{js_regex(str(pattern))}.test(key)), "
                "{ message: 'invalid extension namespace' })"
            )
        return expr
    return "z.unknown()"


def zod_object_schema(schema: dict[str, Any], id_to_name: dict[str, str]) -> str:
    name = class_name(schema)
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    lines = [f"export const {name}Schema = z.object({{"]
    for field_name, prop_schema in props.items():
        expr = zod_expr_for(prop_schema, id_to_name, name)
        if field_name not in required:
            expr += ".optional()"
        lines.append(f"  {json.dumps(field_name)}: {expr},")
    lines.append("}).strict();")
    return "\n".join(lines)


def ts_type_for(schema: dict[str, Any], id_to_name: dict[str, str]) -> str:
    if "$ref" in schema:
        return ref_name(str(schema["$ref"]), id_to_name)
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return " | ".join(json.dumps(v) for v in schema["enum"])
    if "oneOf" in schema:
        return " | ".join(ts_type_for(item, id_to_name) for item in schema["oneOf"])
    typ = schema.get("type")
    if typ == "string":
        return "string"
    if typ in {"integer", "number"}:
        return "number"
    if typ == "boolean":
        return "boolean"
    if typ == "null":
        return "null"
    if typ == "array":
        return f"Array<{ts_type_for(schema.get('items', {'type': 'object'}), id_to_name)}>"
    if typ == "object":
        return "Record<string, unknown>"
    return "unknown"


def generate_typescript(schemas: list[dict[str, Any]]) -> None:
    id_to_name = {schema_id(schema): class_name(schema) for schema in schemas}
    ordered = dependency_order(schemas)
    TS_OUT.mkdir(parents=True, exist_ok=True)

    mjs_lines = [
        "// Generated foundation contract Zod schemas. Do not hand-edit.",
        "import { z } from 'zod';",
        "",
    ]
    ts_lines = [
        "// Generated foundation contract TypeScript/Zod bindings. Do not hand-edit.",
        "import { z } from 'zod';",
        "",
    ]

    for schema in ordered:
        mjs_lines.append(zod_object_schema(schema, id_to_name))
        mjs_lines.append("")
        ts_lines.append(zod_object_schema(schema, id_to_name))
        required = set(schema.get("required", []))
        ts_lines.append(f"export interface {class_name(schema)} {{")
        for field_name, prop_schema in schema.get("properties", {}).items():
            optional = "" if field_name in required else "?"
            ts_lines.append(f"  {field_name}{optional}: {ts_type_for(prop_schema, id_to_name)};")
        ts_lines.append("}")
        ts_lines.append("")

    schema_map = ", ".join(f"{name}: {name}Schema" for name in sorted(id_to_name.values()))
    mjs_lines.append(f"export const FoundationSchemas = {{ {schema_map} }};")
    ts_lines.append(f"export const FoundationSchemas = {{ {schema_map} }};")

    (TS_OUT / "index.mjs").write_text("\n".join(mjs_lines) + "\n")
    (TS_OUT / "index.ts").write_text("\n".join(ts_lines) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def package_version() -> str:
    return json.loads((ROOT / "package.json").read_text())["version"]


def generate_manifest(schemas: list[dict[str, Any]]) -> None:
    commands = json.loads((ROOT / "registry" / "commands.v1.json").read_text())
    events = json.loads((ROOT / "registry" / "events.v1.json").read_text())
    aliases = json.loads((ROOT / "registry" / "legacy-aliases.v1.json").read_text())
    manifest = {
        "manifestVersion": "1.0.0",
        "contractPackageVersion": package_version(),
        "generatorVersion": GENERATOR_VERSION,
        "generatorSourceDigest": sha256_file(ROOT / "scripts" / "generate_bindings.py"),
        "schemaCount": len(schemas),
        "schemas": [
            {
                "schemaId": schema["$id"],
                "canonicalName": schema["title"],
                "semanticVersion": schema.get("x-umh", {}).get("contractVersion", "1.0.0"),
                "sourcePath": schema["_source_path"],
                "digest": sha256_json({k: v for k, v in schema.items() if k != "_source_path"}),
            }
            for schema in sorted(schemas, key=lambda item: item["$id"])
        ],
        "commandCount": len(commands["commands"]),
        "eventCount": len(events["events"]),
        "aliasCount": len(aliases["aliases"]),
        "registryDigests": {
            "commands": sha256_json(commands),
            "events": sha256_json(events),
            "legacyAliases": sha256_json(aliases),
        },
        "generatedArtifacts": {
            "pythonModels": sha256_file(PY_OUT / "models.py"),
            "pythonInit": sha256_file(PY_OUT / "__init__.py"),
            "typescriptSource": sha256_file(TS_OUT / "index.ts"),
            "typescriptRuntime": sha256_file(TS_OUT / "index.mjs"),
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main() -> None:
    schemas = load_schemas()
    generate_python(schemas)
    generate_typescript(schemas)
    generate_manifest(schemas)
    print(f"generated {len(schemas)} schemas")


if __name__ == "__main__":
    main()
