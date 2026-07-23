#!/usr/bin/env python3
"""Fixture-app generator for Wave 2 field qualification.

Emits a small, deterministic real web app (FastAPI backend + static vanilla-JS
frontend + pytest tests) into a target directory, git-inits it, and prints the
base commit sha. The generated app is GREEN at base; the seeded objective —
"add note search: a backend endpoint + a frontend search box, integrated and
verified" — decomposes into Tasks A (backend), B (frontend), C (integration),
D (verification).

The generator is SPEC-ONLY: it seeds the working app and the OBJECTIVE.md
contract. It NEVER contains the solution patch — the real workers implement it.

Usage:
    make_fixture_app.py --dest <targets>/<run-id>/fixture --variant clean|tools-revoked-a
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

# ── File contents (base app — GREEN, no search yet) ──────────────────────────

MAIN_PY = '''\
"""Fixture notes app — FastAPI backend + static frontend."""
from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.store import NoteStore

app = FastAPI(title="fixture-notes")
_store = NoteStore(os.path.join(os.path.dirname(__file__), "..", "seed", "notes.json"))


class NoteIn(BaseModel):
    title: str
    body: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/notes")
def list_notes() -> dict:
    return {"notes": _store.all()}


@app.post("/api/notes")
def add_note(note: NoteIn) -> dict:
    if not note.title.strip():
        raise HTTPException(status_code=400, detail="title required")
    return _store.add(note.title, note.body)


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with open(os.path.join(_STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
'''

STORE_PY = '''\
"""In-memory + seed-file note store."""
from __future__ import annotations

import json
import uuid


class NoteStore:
    def __init__(self, seed_path: str) -> None:
        with open(seed_path, encoding="utf-8") as f:
            seed = json.load(f)
        self._notes = [dict(n) for n in seed]

    def all(self) -> list[dict]:
        return list(self._notes)

    def add(self, title: str, body: str) -> dict:
        note = {"id": uuid.uuid4().hex[:8], "title": title, "body": body}
        self._notes.append(note)
        return note
'''

INDEX_HTML = '''\
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Fixture Notes</title></head>
<body>
  <h1>Notes</h1>
  <ul data-testid="note-list" id="note-list"></ul>
  <script src="/static/app.js"></script>
</body>
</html>
'''

APP_JS = '''\
async function loadNotes() {
  const resp = await fetch('/api/notes');
  const data = await resp.json();
  const list = document.querySelector('[data-testid="note-list"]');
  list.innerHTML = '';
  for (const n of data.notes) {
    const li = document.createElement('li');
    li.textContent = n.title;
    list.appendChild(li);
  }
}
loadNotes();
'''

TEST_API_PY = '''\
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_notes():
    notes = client.get("/api/notes").json()["notes"]
    assert len(notes) == 6
    assert any(n["title"] == "alpha" for n in notes)


def test_add_note():
    r = client.post("/api/notes", json={"title": "zeta", "body": "z"})
    assert r.status_code == 200
    assert r.json()["title"] == "zeta"


def test_add_note_requires_title():
    assert client.post("/api/notes", json={"title": ""}).status_code == 400
'''

TEST_UI_SERVED_PY = '''\
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_served():
    html = client.get("/").text
    assert 'data-testid="note-list"' in html


def test_app_js_served():
    assert client.get("/static/app.js").status_code == 200
'''

SEED_NOTES = [
    {"id": "n1", "title": "alpha", "body": "first note"},
    {"id": "n2", "title": "bravo", "body": "second note"},
    {"id": "n3", "title": "charlie", "body": "third note"},
    {"id": "n4", "title": "delta", "body": "fourth note"},
    {"id": "n5", "title": "echo", "body": "fifth note"},
    {"id": "n6", "title": "foxtrot", "body": "sixth note"},
]

REQUIREMENTS = "fastapi\nuvicorn\npytest\nhttpx\n"

OBJECTIVE_MD = '''\
# Objective: Add note search to the fixture app

Add a case-insensitive note search to this app — a backend search endpoint and a
frontend search box — integrated and verified end to end.

## Task A (backend) — the exact contract

Implement `GET /api/notes/search?q=<str>`:
- case-insensitive substring match over each note's `title` AND `body`;
- response JSON: `{"query": "<q>", "results": [<note>, ...]}` where each note is
  the full `{id, title, body}` object;
- an empty or missing `q` returns HTTP 400.
Add tests in `tests/test_search_api.py`. Confine changes to `app/main.py`,
`app/store.py`, and `tests/test_search_api.py`.

## Task B (frontend) — the exact contract

Add to `static/index.html`:
- a search input with `data-testid="note-search-input"`;
- a results list with `data-testid="note-search-results"`.
Wire `static/app.js` to call `GET /api/notes/search?q=<value>` on input and
render the results. Add `tests/test_ui_search.py` asserting the served HTML
contains BOTH testids. Confine changes to `static/*` and `tests/test_ui_search.py`.

## Task C (integration) — depends on A and B

Reconcile the A and B branches, run the FULL test suite (base + A's + B's), and
confirm the app launches (`uvicorn app.main:app`), `/health` returns 200.

## Task D (verification) — depends on C, independent verifier

Validate the API contract, the served UI testids, a live browser check (type
"alpha", results render), the source diff scope, and produce Proof.
'''

GITIGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\nfixture-venv/\n"


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate(dest: str, variant: str) -> str:
    _write(os.path.join(dest, "app", "__init__.py"), "")
    _write(os.path.join(dest, "app", "main.py"), MAIN_PY)
    _write(os.path.join(dest, "app", "store.py"), STORE_PY)
    _write(os.path.join(dest, "app", "static", "index.html"), INDEX_HTML)
    _write(os.path.join(dest, "app", "static", "app.js"), APP_JS)
    _write(os.path.join(dest, "tests", "test_api.py"), TEST_API_PY)
    _write(os.path.join(dest, "tests", "test_ui_served.py"), TEST_UI_SERVED_PY)
    _write(os.path.join(dest, "seed", "notes.json"), json.dumps(SEED_NOTES, indent=2))
    _write(os.path.join(dest, "requirements.txt"), REQUIREMENTS)
    _write(os.path.join(dest, "OBJECTIVE.md"), OBJECTIVE_MD)
    _write(os.path.join(dest, ".gitignore"), GITIGNORE)

    # variant hook: tools-revoked-a is a dispatch-time policy, not a fixture
    # change — the fixture is identical; the failure is injected via the
    # attempt's tool policy. Recorded here for provenance only.
    _write(os.path.join(dest, ".variant"), variant)

    env = dict(os.environ, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@local",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@local")
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "fixture: base notes app (green)"],
                   cwd=dest, check=True, env=env)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True,
                         text=True, env=env).stdout.strip()
    return sha


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--variant", default="clean", choices=["clean", "tools-revoked-a"])
    args = ap.parse_args()
    sha = generate(args.dest, args.variant)
    print(json.dumps({"fixture_base_sha": sha, "dest": args.dest, "variant": args.variant}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
