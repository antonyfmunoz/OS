"""CutStudio HTTP routes — prefix /api/cut.

THIS API IS THE PRODUCT SURFACE (D9). The cockpit instrument is its first
consumer; CreativesOS will mount its own UI against the same contract, the
way conference rooms share one backend. Therefore nothing here may assume a
cockpit-specific caller: auth is dual (Clerk OR API key), the JSON shapes
are stable, and the EDL/transcript schemas from Phase 1 (`edl.py`,
`transcribe.py`) remain the canonical contract.

Two routers are exported:
  `router`          — authed, everything below
  `public_router`   — unauthed, /media only (the link token IS the auth;
                      a <video> element cannot send an Authorization header)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse, StreamingResponse

from projections.empyrean.recovery_pilot.renderer import link_tokens

from . import ai, detect, media, rendering, store, transcription
from .registry import get_registry

logger = logging.getLogger("cutstudio.routes")

router = APIRouter(prefix="/api/cut", tags=["cutstudio"])
public_router = APIRouter(prefix="/api/cut", tags=["cutstudio-public"])

MEDIA_TOKEN_TTL = 12 * 3600
DEFAULT_WHISPER_MODEL = "small"


def _meta_or_404(project_id: str) -> dict:
    try:
        return store.read_meta(project_id)
    except store.StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _words_for(project_id: str) -> list[dict]:
    tr = store.read_transcript(project_id)
    return transcription.all_words(tr) if tr else []


# ── 1. create project (upload) ───────────────────────────────────────────
@router.post("/projects")
async def create_project(file: UploadFile = File(...), name: str = Form(default="")) -> dict:
    if not store.disk_ok():
        raise HTTPException(
            status_code=507,
            detail="insufficient disk space (%.1fGB free, %.0fGB required)"
            % (store.free_gb(), store.MIN_FREE_GB),
        )
    try:
        media.check_content_type(file.content_type)
    except media.UnsupportedMedia as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    project_id = store.new_id()
    filename = media.safe_name(file.filename)
    dest = store.project_dir(project_id) / filename
    try:
        written = await media.stream_upload(file, dest)
    except media.UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    probe = media.probe(dest)
    duration = float(probe.get("duration") or 0.0)
    if duration <= 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="could not read media duration")

    meta = store.create(project_id, name.strip() or (file.filename or filename), filename, probe)
    initial_edl = {
        "version": 1,
        "source": str(dest),
        "clips": [{"start": 0.0, "end": round(duration, 3), "label": "full"}],
        "captions": False,
        "vertical": False,
        "output": "cut_output.mp4",
    }
    store.write_edl(project_id, initial_edl)
    return {
        "id": project_id,
        "name": meta["name"],
        "media": filename,
        "duration": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "fps": meta["fps"],
        "size": written["size"],
        "sha256": written["sha256"],
    }


# ── 2/3. list + delete ───────────────────────────────────────────────────
@router.get("/projects")
async def list_projects() -> list[dict]:
    return store.list_projects()


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """A project summary plus its jobs.

    Same shape as one entry of GET /projects (store.summarize) so a client
    never has to call both to assemble a whole project; `jobs` is the only
    addition, since listing them for every project would be wasteful.
    """
    meta = _meta_or_404(project_id)
    summary = store.summarize(meta, store.project_dir(project_id))
    summary["jobs"] = get_registry().list_for_project(project_id)
    return summary


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> dict:
    try:
        store.delete(project_id)
    except store.StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


# ── 4/5. transcription ───────────────────────────────────────────────────
@router.post("/projects/{project_id}/transcribe")
async def start_transcribe(project_id: str, body: dict | None = None) -> dict:
    meta = _meta_or_404(project_id)
    model_size = str((body or {}).get("model") or DEFAULT_WHISPER_MODEL)
    src = store.media_path(project_id)
    out_dir = store.project_dir(project_id)
    duration = float(meta.get("duration") or 0.0)

    def work(job):
        return transcription.transcribe_project(src, out_dir, model_size, duration, job)

    job = get_registry().submit("transcribe", project_id, work)
    return {"job_id": job.id}


@router.get("/projects/{project_id}/transcript")
async def get_transcript(project_id: str) -> dict:
    _meta_or_404(project_id)
    tr = store.read_transcript(project_id)
    if tr is None:
        raise HTTPException(status_code=404, detail="no transcript — run transcribe first")
    return tr


# ── 6/7. EDL read + optimistic write ─────────────────────────────────────
@router.get("/projects/{project_id}/edl")
async def get_edl(project_id: str, response: Response) -> dict:
    _meta_or_404(project_id)
    try:
        edl, rev = store.read_edl(project_id)
    except store.StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.headers["X-EDL-Rev"] = str(rev)
    return edl


@router.put("/projects/{project_id}/edl")
async def put_edl(project_id: str, request: Request, response: Response) -> dict:
    _meta_or_404(project_id)
    body = await request.json()
    if_match = request.headers.get("if-match")
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match header required")
    try:
        rev_requested = int(str(if_match).strip().strip('"'))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="If-Match must be an integer rev") from exc

    edl_module = rendering.get_edl_module()
    try:
        validated = edl_module.validate(dict(body))
    except Exception as exc:  # EDLError and any coercion failure
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        saved, rev = store.write_edl(project_id, validated, if_match=rev_requested)
    except store.RevMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except store.StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.headers["X-EDL-Rev"] = str(rev)
    return saved


# ── 8. AI edit ───────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/ai-edit")
async def ai_edit(project_id: str, body: dict) -> dict:
    meta = _meta_or_404(project_id)
    instruction = str((body or {}).get("instruction") or "").strip()
    if not instruction:
        raise HTTPException(status_code=422, detail="instruction required")
    tr = store.read_transcript(project_id)
    if tr is None:
        raise HTTPException(status_code=409, detail="transcribe the project first")
    edl, rev = store.read_edl(project_id)
    result = ai.revise_edl(edl, tr, instruction, float(meta.get("duration") or 0.0))
    result["rev"] = rev  # proposal only — the client applies it with a PUT
    return result


# ── 9. highlights ────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/highlights")
async def highlights(project_id: str, body: dict | None = None) -> dict:
    meta = _meta_or_404(project_id)
    tr = store.read_transcript(project_id)
    if tr is None:
        raise HTTPException(status_code=409, detail="transcribe the project first")
    payload = body or {}
    count = int(payload.get("count") or 4)
    target = float(payload.get("target_seconds") or 45.0)
    duration = float(meta.get("duration") or 0.0)

    def work(job):
        job.progress = 0.2
        return ai.find_highlights(tr, duration, count, target)

    job = get_registry().submit("highlights", project_id, work)
    return {"job_id": job.id}


# ── 10. detection ────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/detect")
async def run_detect(project_id: str, body: dict | None = None) -> dict:
    _meta_or_404(project_id)
    tr = store.read_transcript(project_id)
    if tr is None:
        raise HTTPException(status_code=409, detail="transcribe the project first")
    payload = body or {}
    words = transcription.all_words(tr)

    filler_words: list[dict] = []
    if payload.get("fillers", True):
        custom = payload.get("filler_list")
        filler_words = detect.find_fillers(words, custom if isinstance(custom, list) else None)

    silence_gaps: list[dict] = []
    silences = payload.get("silences", True)
    if silences:
        threshold = detect.DEFAULT_SILENCE_THRESHOLD
        if isinstance(silences, dict):
            try:
                threshold = float(silences.get("threshold", threshold))
            except (TypeError, ValueError):
                pass
        silence_gaps = detect.find_silences(words, threshold)

    return {"filler_words": filler_words, "silence_gaps": silence_gaps}


# ── 11. render ───────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/render")
async def start_render(project_id: str, body: dict | None = None) -> dict:
    _meta_or_404(project_id)
    payload = body or {}
    aspect = str(payload.get("aspect") or "source")
    if aspect not in rendering.VALID_ASPECTS:
        raise HTTPException(
            status_code=422,
            detail="aspect must be one of %s" % (", ".join(rendering.VALID_ASPECTS)),
        )
    captions = bool(payload.get("captions", False))
    try:
        caption_style = int(payload.get("caption_style") or 1)
    except (TypeError, ValueError):
        caption_style = 1
    if caption_style not in (1, 2, 3):
        raise HTTPException(status_code=422, detail="caption_style must be 1, 2, or 3")
    clean_audio = bool(payload.get("clean_audio", False))

    clip = payload.get("clip")
    if clip is not None:
        try:
            clip = {"start": float(clip["start"]), "end": float(clip["end"])}
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="clip needs numeric start/end") from exc
        if clip["end"] <= clip["start"]:
            raise HTTPException(status_code=422, detail="clip end must be > start")

    output = str(payload.get("output") or "").strip()
    if output and ("/" in output or "\\" in output):
        raise HTTPException(status_code=422, detail="output must be a bare filename")
    if not output:
        output = "render_%s.mp4" % time.strftime("%Y%m%d_%H%M%S")
    if not output.lower().endswith(".mp4"):
        output += ".mp4"

    edl, _rev = store.read_edl(project_id)
    src = store.media_path(project_id)
    out_dir = store.renders_dir(project_id)
    words = _words_for(project_id)
    if captions and not words:
        raise HTTPException(status_code=409, detail="captions need a transcript")
    store.prune_renders(project_id)

    def work(job):
        return rendering.render(
            edl,
            src,
            out_dir,
            output,
            words,
            aspect=aspect,
            captions=captions,
            caption_style=caption_style,
            clean_audio=clean_audio,
            clip=clip,
            job=job,
        )

    job = get_registry().submit("render", project_id, work)
    return {"job_id": job.id}


# ── 12. job status ───────────────────────────────────────────────────────
@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = get_registry().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()


# ── 13/14. media token + Range stream ────────────────────────────────────
def _media_ref(project_id: str, name: str) -> str:
    return "cutmedia-%s-%s" % (project_id, name)


@router.get("/projects/{project_id}/media-token")
async def media_token(project_id: str, name: str = "") -> dict:
    meta = _meta_or_404(project_id)
    filename = name or meta["media"]
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="invalid media name")
    ref = _media_ref(project_id, filename)
    try:
        token = link_tokens.mint(ref, ttl_seconds=MEDIA_TOKEN_TTL)
    except ValueError as exc:  # link_tokens refuses PII-looking refs
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"token": token, "url": "/api/cut/media?tok=%s" % token}


def _resolve_media_path(ref: str) -> Path:
    """Turn a resolved token ref into a real path.

    The client never supplies a path — only a signed ref — so traversal is
    structurally impossible, and the resolved path is re-checked against the
    project directory anyway.
    """
    if not ref.startswith("cutmedia-"):
        raise HTTPException(status_code=403, detail="invalid media reference")
    remainder = ref[len("cutmedia-") :]
    project_id, sep, filename = remainder.partition("-")
    if not sep or not filename:
        raise HTTPException(status_code=403, detail="invalid media reference")
    try:
        base = store.project_dir(project_id)
    except store.StoreError as exc:
        raise HTTPException(status_code=403, detail="invalid media reference") from exc

    candidate = (base / filename).resolve()
    if base not in candidate.parents and candidate.parent != base:
        raise HTTPException(status_code=403, detail="invalid media reference")
    if not candidate.exists():
        renders_candidate = (base / "renders" / filename).resolve()
        if renders_candidate.exists() and renders_candidate.parent == (base / "renders"):
            return renders_candidate
        raise HTTPException(status_code=404, detail="media not found")
    return candidate


@public_router.get("/media")
async def stream_media(tok: str = "", request: Request = None) -> Response:
    """Range-capable media stream. The token IS the auth (D3)."""
    ref = link_tokens.resolve(tok) if tok else None
    if not ref:
        raise HTTPException(status_code=403, detail="invalid or expired media token")
    path = _resolve_media_path(ref)

    size = path.stat().st_size
    ctype = media.content_type_for(path)
    range_header = request.headers.get("range") if request is not None else None
    span = media.parse_range(range_header, size)

    if span is None:
        return StreamingResponse(
            media.file_chunks(path, 0, size - 1),
            media_type=ctype,
            headers={"Content-Length": str(size), "Accept-Ranges": "bytes"},
        )
    start, end = span
    return StreamingResponse(
        media.file_chunks(path, start, end),
        status_code=206,
        media_type=ctype,
        headers={
            "Content-Range": "bytes %d-%d/%d" % (start, end, size),
            "Content-Length": str(end - start + 1),
            "Accept-Ranges": "bytes",
        },
    )


# ── 15. CMX3600 export ───────────────────────────────────────────────────
@router.get("/export/{project_id}.edl", response_class=PlainTextResponse)
async def export_cmx(project_id: str) -> PlainTextResponse:
    meta = _meta_or_404(project_id)
    try:
        edl, _rev = store.read_edl(project_id)
    except store.StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    text = rendering.to_cmx3600(edl, meta.get("name") or project_id, float(meta.get("fps") or 30.0))
    return PlainTextResponse(
        text,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="%s.edl"' % project_id},
    )
