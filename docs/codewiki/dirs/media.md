---
type: codewiki-dir
dir: media
---

# `media/` — output sink for generated media (Higgsfield images/video)

**0 files · 0 bytes · [Full file inventory](../inventory/media.md)**

*(Counts as of the manifest's `generated_at` 2026-07-10T20:18Z, git SHA `a5f09e48e`. Empty scaffold: the single subdirectory `media/higgsfield/` exists but currently holds no files.)*

## Purpose
`media/` is the download destination for generated media assets. Today it contains exactly one subdirectory, `media/higgsfield/`, which is where the Higgsfield generation webhook saves finished images and videos. The tree is a scaffold — the directory exists so the writer has a stable target, but no assets are currently present (the manifest counts 0 files).

## How it fits
`media/` is a data sink, not code. It is written by the Higgsfield webhook handler in the transports/services layer and referenced by the state store that tracks generation jobs. Nothing imports it; producers open paths under it at runtime. Generated media is treated as gitignored runtime output — heavy binary artifacts belong on the GPU/executor node, not the VPS coordination brain, per Node Role Discipline.

## Structure

| Path | Files | Role |
|---|---|---|
| `higgsfield/` | 0 | Download target for Higgsfield-generated images/video. Populated on demand when a generation job completes. |

## Key components
- `services/higgsfield_webhook.py` — the producer. On a completed job it downloads the generated image/video to `/opt/OS/media/higgsfield/` (`_download(url, dest)` writes the streamed asset). This webhook is why the `higgsfield/` subdir exists even while empty.
- `substrate/state/stores/higgsfield_store.py` — the job store (`insert_job`, `update_status`) that tracks generation requests whose outputs land in this directory. It records job state; the webhook writes the bytes.

## Data & state
Binary media files (images, video) downloaded from Higgsfield generation results. Writes are on-demand, driven entirely by inbound webhook events — there is no scheduled producer, so an empty `media/` simply means no generation job has completed and been downloaded recently. Generated content here is runtime output and gitignored in practice (binary blobs, per the node-role and universal secrets/generated-files conventions); the empty scaffold is what remains tracked.

## Gotchas
- **Empty is the normal steady state on the VPS.** 0 files is expected — media generation is event-driven and heavy artifacts are meant to live on the executor/GPU node, not accumulate on the coordination brain. Do not treat the empty dir as a broken pipeline; check whether a job actually completed (`higgsfield_store`) before concluding the writer failed.
- **Don't commit generated media.** If assets appear here, they are runtime output — keep them out of git to respect Node Role Discipline (the VPS stays lightweight) and the universal "generated files" convention.
- **The subdir is load-bearing.** `services/higgsfield_webhook.py` writes to `media/higgsfield/` specifically; removing the directory would break the download path on the next completed job.

## See also
- [`services/`](services.md) — `higgsfield_webhook.py` (the media writer)
- [`substrate/`](substrate.md) — `state/stores/higgsfield_store.py` (the job store)
- [`data/`](data.md) — other runtime sinks (`chat_media/`, generated proofs)
- [Services & runtime](../services-runtime.md)
