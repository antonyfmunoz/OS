"""Modular parser system for the EOS codebase knowledge graph.

Each parser consumes a file and returns a ParsedFile containing
symbols, imports, and relationships in a language-agnostic shape.

Register new languages by implementing base.Parser and adding to
REGISTRY at the bottom of this module.
"""

from __future__ import annotations

from pathlib import Path

from tools.parsers_lib.base import ParsedFile, Parser
from tools.parsers_lib.config_parser import ConfigParser
from tools.parsers_lib.js_parser import JSParser
from tools.parsers_lib.python_parser import PythonParser
from tools.parsers_lib.sql_parser import SQLParser
from tools.parsers_lib.ts_parser import TSParser

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
