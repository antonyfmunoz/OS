"""CutStudio server — the API layer over the Phase 1 cut pipeline.

Phase 1 (transcribe.py -> edl.py -> cutter.py) is the engine. This package is
the service around it: project storage, background jobs, media streaming,
detection, AI edits, and rendering.

The API contract (prefix /api/cut) is the product surface — the cockpit
instrument is one consumer, CreativesOS will be another. Nothing in here may
assume a cockpit-specific caller (see D9 in the build plan).
"""
