"""Modular parser system for the EOS codebase knowledge graph.

Each parser consumes a file and returns a ParsedFile containing
symbols, imports, and relationships in a language-agnostic shape.

Register new languages by implementing base.Parser and adding to
REGISTRY at the bottom of this module.
"""

from __future__ import annotations

from pathlib import Path

from parsers.base import ParsedFile, Parser
from parsers.config_parser import ConfigParser
from parsers.js_parser import JSParser
from parsers.python_parser import PythonParser
from parsers.sql_parser import SQLParser
from parsers.ts_parser import TSParser

REGISTRY: list[Parser] = [
    PythonParser(),
    TSParser(),
    JSParser(),
    SQLParser(),
    ConfigParser(),
]


def parse(path: Path) -> ParsedFile | None:
    """Dispatch a file to the first parser that claims it."""
    for parser in REGISTRY:
        if parser.handles(path):
            return parser.parse(path)
    return None


__all__ = ["ParsedFile", "Parser", "REGISTRY", "parse"]
