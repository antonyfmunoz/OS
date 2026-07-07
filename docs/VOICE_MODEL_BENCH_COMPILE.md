# Voice Model Benchmark — Compile Artifact

Compiled 2026-07-07 as the compile-only benchmark PLAN and candidate matrix for
the local / open-source voice stack under **P4S-VOICE-MODEL-BENCH-001**. Data
artifact: `data/umh/voice/voice_model_bench_compile.json`.

**Compile mode — no activation authorized by this document.** No benchmark is
run, no model is downloaded, and no heavy compute is executed by this artifact.
It defines the benchmark METHOD and the CANDIDATE MATRIX a later, owner-called
execution packet runs and is validated against. Every latency / footprint /
accuracy number in the matrix is a compile-time **ESTIMATE**, never a
measurement taken in this environment. Style matches
`docs/DESKTOP_AMBIENT_WAKE_COMPILE.md` and `docs/VOICE_INTENT_CONTRACT.md`.

---

## Why benchmark, and against what

The current shipping voice path (`umh/voice_server.py`) is the **baseline**
every candidate is measured against:

| Capability | Current shipping engine | Local fallback |
| --- | --- | --- |
| STT | Groq `whisper-large-v3-turbo` (cloud API) | `faster-whisper` (local, executor GPU) |
| TTS | Kokoro on the executor GPU node (`:8880`) | espeak (CPU-gated subprocess) |
| VAD | energy threshold (`compute_audio_level`, `SPEECH_LEVEL_THRESHOLD=0.02`) | — |
| Wake | (not yet shipping) | candidates in `desktop_ambient_wake_compile.json` |

The point of the benchmark is to let the platform **choose** STT/TTS/wake/VAD
engines on measured evidence — WER, MOS, false-accept/false-reject,
precision/recall, latency, footprint — instead of vendor claims. This artifact
is the plan; it does not choose and it does not measure.

## Node Role Discipline (binding — CLAUDE.md, NON-NEGOTIABLE)

Every candidate is annotated with which device **role** may host it at runtime
(`node_binding.runtime_host_role`), resolved from `infra/device_registry.json`
by role — never a hostname or device-name literal.

- **orchestrator role** (the always-on coordination brain): runs **no heavy
  model**. Allowed voice work is network-bound API clients only (Groq STT,
  ElevenLabs) plus the trivial energy / WebRTC VAD. Loading whisper, Kokoro, or
  XTTS here is forbidden — the CPU Gate Law exists because that host is
  throttled for a week on CPU abuse.
- **executor role** (GPU workhorse): hosts all local STT (faster-whisper /
  whisper.cpp / distil-whisper), all local TTS (Kokoro / Piper / XTTS), and the
  on-device wake runtime. It already hosts `kokoro_tts` per the registry.
- **controller role** (the operator's own device): may run on-device STT / wake
  / WebGPU-Whisper on the operator's own silicon.

**The benchmark EXECUTION packet runs on an executor-role GPU node, never on the
orchestrator.** It is CPU-gated: `cpu_gate_check(caller)` before every heavy
load, `gated_subprocess_run` / `gated_popen` for any subprocess. If the gate
reports overload, the run pauses — it never saturates the host.

## Candidate matrix (summary)

Full per-candidate detail (license, on-device vs API, estimated latency /
footprint / accuracy, node binding, quality dimension, governance flags) lives
in the JSON artifact. Summary:

### STT — primary metric WER (lower is better)

| Candidate | License | On-device / API | Host role | Note |
| --- | --- | --- | --- | --- |
| `groq_whisper_large_v3_turbo` | proprietary API (weights MIT) | API | any (client) | **baseline** — current default |
| `faster_whisper_large_v3` | MIT | on-device | executor | accuracy ceiling; heavy |
| `faster_whisper_small` | MIT | on-device | executor | realistic local default |
| `distil_whisper_large_v3` | MIT | on-device | executor | near-large accuracy, faster |
| `whisper_cpp_base_en` | MIT | on-device | executor / controller | smallest local footprint |
| `webgpu_whisper_transformers_js` | Apache-2.0 / MIT | on-device (browser) | controller | fully client-side |

### TTS — primary metric MOS (higher is better; human panel)

| Candidate | License | On-device / API | Host role | Clone-capable |
| --- | --- | --- | --- | --- |
| `kokoro` | Apache-2.0 | on-device | executor | no — **baseline** |
| `piper` | MIT (per-voice varies) | on-device | executor / controller | no |
| `xtts_v2_coqui` | **Coqui CPML (non-commercial)** | on-device | executor | **YES — flagged** |
| `elevenlabs` | proprietary API (paid) | API | any (client) | **YES — flagged** |
| `espeak` | GPL-3.0 | on-device | any | no — MOS floor |

### Wake-word — primary metrics FA/hr + FRR (lower is better)

| Candidate | License | On-device / API | Host role |
| --- | --- | --- | --- |
| `openwakeword_onnx` | Apache-2.0 | on-device | executor / controller |
| `porcupine` | **proprietary (Picovoice)** | on-device | executor / controller |

(Candidate set + CPU/RSS bounds inherited from
`desktop_ambient_wake_compile.json`; restated, not softened.)

### VAD — primary metrics precision + recall (higher is better)

| Candidate | License | On-device / API | Host role |
| --- | --- | --- | --- |
| `energy_threshold_baseline` | n/a (in-repo) | on-device | any — **baseline** |
| `silero_vad` | MIT | on-device | executor / controller |
| `webrtc_vad` | BSD-3-Clause | on-device | any |

## Outbound-voice governance (binding for TTS)

Per `docs/VOICE_INTENT_CONTRACT.md` and the outbound-voice governance: **any TTS
engine capable of zero/few-shot voice cloning is a governance-flagged candidate
and is NOT recommended by this benchmark without an explicit outbound-voice
governance + licensing sign-off.** A clone-capable model can synthesize a target
person's voice — an impersonation / consent / likeness risk.

- **Clone-capable, flagged:** `xtts_v2_coqui` (also **non-commercial** Coqui
  CPML license — commercial ship BLOCKED without a separate Coqui license),
  `elevenlabs` (cloud, paid).
- **Not clone-capable, safe:** `kokoro`, `piper`, `espeak`.

This artifact lists the clone-capable engines for completeness and flags each;
it recommends none. Selecting one is the governance review's call, not the
benchmark's.

## Benchmark method

- **STT** — LibriSpeech `test-clean` / `test-other` (public WER standard) plus a
  ~50-item held-out set of UMH-style operator commands (transcript-only,
  synthetic/paraphrased — **never real recorded operator audio**, per the
  transcript-only, no-audio-persistence policy). Conditions: clean, noisy (SNR
  sweep), accented. Metrics: WER (primary), RTF, latency, footprint.
- **TTS** — a fixed ~30-sentence set (short commands, long paragraphs,
  numbers/dates/acronyms). MOS scored by a small human listening panel on the
  same sentences per engine (MOS is subjective and is never auto-measured);
  latency and RTF measured mechanically.
- **Wake-word** — positive set (clean + noisy utterances of the
  instance-configured keyword, on-device only) and a many-hour negative corpus
  to measure false-accepts/hour and false-reject rate.
- **VAD** — a labelled speech/non-speech corpus with per-frame ground truth;
  precision and recall (primary), CPU, frame latency.

## How to run it (execution packet — not this artifact)

1. Resolve the executor host from `infra/device_registry.json` by
   `role=executor` with a GPU + display. Never hardcode a hostname.
2. On the executor, for each candidate: `cpu_gate_check(caller)` -> load model
   (gated) -> run the dataset -> record the metric -> unload.
3. API baselines (Groq, ElevenLabs) run as network clients — no model load, so
   they may be invoked from any node.
4. Replace each ESTIMATE in the matrix with the measured value.
5. Write measured results to `data/umh/voice/voice_model_bench_results.jsonl`
   (one JSON line per candidate per condition; created by the execution packet
   only — **this compile artifact never writes it**).
6. The run is idempotent and resumable so a CPU-gate pause never loses progress.

**No STT/TTS/wake/VAD model is ever loaded on the orchestrator during the
benchmark.** Models are downloaded and cached only on the executor's local model
store (GPU-workhorse role) — nothing on the orchestrator.

## Forbidden in this packet

Running any benchmark; downloading any model or dataset; any heavy compute or
model load on any node; any provider execution (no Groq / ElevenLabs / Kokoro
call beyond referencing existing runtime logs); adding any STT/TTS/wake/VAD
library to a dependency manifest; recommending a voice-clone-capable model
without the governance + licensing flag; loading any heavy model on the
orchestrator; writing `voice_model_bench_results.jsonl`; any tenant or
device-hostname literal as global truth.

## Rollback

This compile artifact is additive (one doc + one data file + one test). Revert
the commit and nothing at runtime changes — no model, no download, no service,
no dependency was introduced.
