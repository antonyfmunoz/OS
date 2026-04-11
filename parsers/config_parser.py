"""Config parser — top-level key extraction for JSON/YAML/TOML files."""

from __future__ import annotations

import json
from pathlib import Path

from parsers.base import ParsedFile, ParsedSymbol, Parser

ROOT = Path("/opt/OS")


class ConfigParser(Parser):
    language = "config"
    extensions = (".json", ".yaml", ".yml", ".toml")

    def parse(self, path: Path) -> ParsedFile:
        source = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        parsed = ParsedFile(
            path=rel,
            language=f"config:{path.suffix.lstrip('.')}",
            line_count=source.count("\n") + 1,
            size_bytes=path.stat().st_size,
        )

        keys: list[str] = []
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(source)
                if isinstance(data, dict):
                    keys = list(data.keys())
            except json.JSONDecodeError:
                pass
        else:
            # YAML/TOML — dependency-free: extract unindented keys.
            for i, line in enumerate(source.splitlines(), start=1):
                if not line or line[0] in " #\t":
                    continue
                if ":" in line:
                    key = line.split(":", 1)[0].strip()
                    if key and not key.startswith("-"):
                        parsed.symbols.append(
                            ParsedSymbol(name=key, kind="key", line=i)
                        )
            return parsed

        for key in keys:
            parsed.symbols.append(ParsedSymbol(name=str(key), kind="key", line=1))
        return parsed
