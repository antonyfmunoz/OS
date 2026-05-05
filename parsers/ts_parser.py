"""TypeScript parser — reuses JS regexes and adds interface/type extraction."""

from __future__ import annotations

import re
from pathlib import Path

from parsers.base import ParsedFile, ParsedSymbol
from parsers.js_parser import JSParser

RE_INTERFACE = re.compile(r"""^\s*(?:export\s+)?interface\s+(?P<name>[\w$]+)""", re.M)
RE_TYPE = re.compile(r"""^\s*(?:export\s+)?type\s+(?P<name>[\w$]+)\s*=""", re.M)


class TSParser(JSParser):
    language = "typescript"
    extensions = (".ts", ".tsx")

    def parse(self, path: Path) -> ParsedFile:
        parsed = super().parse(path)
        parsed.language = self.language
        source = path.read_text(encoding="utf-8", errors="replace")
        for m in RE_INTERFACE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            parsed.symbols.append(
                ParsedSymbol(name=m.group("name"), kind="interface", line=line)
            )
        for m in RE_TYPE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            parsed.symbols.append(
                ParsedSymbol(name=m.group("name"), kind="type", line=line)
            )
        return parsed
