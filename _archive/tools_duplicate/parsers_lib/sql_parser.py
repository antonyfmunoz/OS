"""SQL parser — detects tables, views, and FROM references."""

from __future__ import annotations

import re
from pathlib import Path

from tools.parsers_lib.base import ParsedFile, ParsedImport, ParsedSymbol, Parser

ROOT = Path("/opt/OS")

RE_CREATE = re.compile(
    r"""create\s+(?:or\s+replace\s+)?(?:table|view|materialized\s+view)\s+(?:if\s+not\s+exists\s+)?['"`]?(?P<name>[\w.]+)['"`]?""",
    re.I,
)
RE_ALTER = re.compile(r"""alter\s+table\s+['"`]?(?P<name>[\w.]+)['"`]?""", re.I)
RE_FROM = re.compile(r"""\bfrom\s+['"`]?(?P<name>[\w.]+)['"`]?""", re.I)
RE_JOIN = re.compile(r"""\bjoin\s+['"`]?(?P<name>[\w.]+)['"`]?""", re.I)


class SQLParser(Parser):
    language = "sql"
    extensions = (".sql",)

    def parse(self, path: Path) -> ParsedFile:
        source = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        parsed = ParsedFile(
            path=rel,
            language=self.language,
            line_count=source.count("\n") + 1,
            size_bytes=path.stat().st_size,
        )

        seen_tables: set[str] = set()
        for m in RE_CREATE.finditer(source):
            name = m.group("name")
            if name not in seen_tables:
                line = source[: m.start()].count("\n") + 1
                parsed.symbols.append(ParsedSymbol(name=name, kind="table", line=line))
                seen_tables.add(name)
        for m in RE_ALTER.finditer(source):
            name = m.group("name")
            parsed.imports.append(ParsedImport(module=name, kind="alter"))
        for rx in (RE_FROM, RE_JOIN):
            for m in rx.finditer(source):
                name = m.group("name")
                if name.lower() in {"select", "where", "dual"}:
                    continue
                parsed.imports.append(ParsedImport(module=name, kind="read"))

        return parsed
