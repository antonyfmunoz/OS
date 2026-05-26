#!/usr/bin/env python3
"""Kokoro TTS Server — OpenAI-compatible API on Beast GPU.

Exposes POST /v1/audio/speech with the same contract as OpenAI's TTS API.
Runs Kokoro 82M locally on the GTX 1080 Ti for zero-cost, high-quality TTS.

Start: python kokoro_server.py
Listens: 0.0.0.0:8880
"""

from __future__ import annotations

import io
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger("kokoro-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SAMPLE_RATE = 24000
pipeline = None


class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: str = "am_adam"
    response_format: str = "wav"
    speed: float = 1.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    logger.info("Loading Kokoro pipeline...")
    t0 = time.time()
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code="a")
    logger.info("Kokoro ready in %.1fs", time.time() - t0)
    yield
    logger.info("Shutting down Kokoro server")


app = FastAPI(title="Kokoro TTS", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model": "kokoro-82m", "ready": pipeline is not None}


@app.post("/v1/audio/speech")
async def create_speech(req: SpeechRequest):
    if pipeline is None:
        raise HTTPException(503, "Pipeline not loaded yet")

    text = req.input.strip()
    if not text:
        raise HTTPException(400, "Empty input")

    t0 = time.time()
    chunks: list[np.ndarray] = []

    try:
        for _gs, _ps, audio in pipeline(text, voice=req.voice, speed=req.speed):
            if audio is not None:
                chunks.append(audio)
    except Exception as e:
        logger.error("Kokoro synthesis failed: %s", e)
        raise HTTPException(500, f"Synthesis failed: {e}")

    if not chunks:
        raise HTTPException(500, "No audio generated")

    full_audio = np.concatenate(chunks)
    elapsed = time.time() - t0
    duration = len(full_audio) / SAMPLE_RATE
    logger.info(
        "TTS: %.1fs audio in %.2fs (%.1fx realtime) voice=%s len=%d",
        duration, elapsed, duration / max(elapsed, 0.001), req.voice, len(text),
    )

    buf = io.BytesIO()
    if req.response_format == "wav":
        sf.write(buf, full_audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        media = "audio/wav"
    elif req.response_format == "pcm":
        pcm = (full_audio * 32767).astype(np.int16)
        buf.write(pcm.tobytes())
        media = "audio/pcm"
    else:
        sf.write(buf, full_audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        media = "audio/wav"

    return Response(content=buf.getvalue(), media_type=media)


@app.get("/v1/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "am_adam", "name": "Adam", "lang": "en-us", "gender": "male"},
            {"id": "am_michael", "name": "Michael", "lang": "en-us", "gender": "male"},
            {"id": "af_heart", "name": "Heart", "lang": "en-us", "gender": "female"},
            {"id": "af_sarah", "name": "Sarah", "lang": "en-us", "gender": "female"},
            {"id": "af_nova", "name": "Nova", "lang": "en-us", "gender": "female"},
            {"id": "bf_emma", "name": "Emma", "lang": "en-gb", "gender": "female"},
            {"id": "bm_george", "name": "George", "lang": "en-gb", "gender": "male"},
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8880, log_level="info")
