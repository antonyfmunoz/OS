"""Shared contracts for all language parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSymbol:
    """A named thing extracted from a file (class, function, table, key)."""

    name: str
    kind: str  # class | function | table | key | route
    line: int
    parent: str | None = None  # e.g. class name for a method
    docstring: str | None = None


@dataclass
class ParsedImport:
    """An edge into another module, file, or external package."""

    module: str
    symbol: str | None = None
    alias: str | None = None
    kind: str = "import"  # import | from | require | include


@dataclass
class ParsedFile:
    """Language-agnostic view of a source file."""

    path: str
    language: str
    line_count: int
    size_bytes: int
    docstring: str | None = None
    symbols: list[ParsedSymbol] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    is_entry_point: bool = False


class Parser(ABC):
    """Base class every language parser must implement."""

    language: str = ""
    extensions: tuple[str, ...] = ()

    def handles(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    @abstractmethod
    def parse(self, path: Path) -> ParsedFile:  # pragma: no cover - abstract
        ...
