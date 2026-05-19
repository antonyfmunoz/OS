"""Notion integration config — UMH-owned manifest and transforms.

This directory holds UMH's configuration for the Notion integration:
- manifest.py  — socket declarations, signal/capability descriptors
- transforms.py — payload translations (future)
- routing.py   — signal routing rules (future)

The handler implementation (code that calls the Notion API) lives
outside UMH, e.g. in /opt/EOS/umh_integration/notion/.
"""
