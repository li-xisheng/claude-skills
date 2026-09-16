#!/usr/bin/env python3
"""FastAPI server for Qwen3-TTS Base voice cloning."""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from qwen_tts import Qwen3TTSModel


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(
    os.environ.get(
        "QWEN_TTS_MODEL",
        SKILL_ROOT / "models" / "Qwen3-TTS-12Hz-1.7B-Base",
    )
).resolve()
MAX_UPLOAD_BYTES = int(os.environ.get("VOICE_MAX_UPLOAD_BYTES", 200 * 1024 * 1024))
SUPPORTED_LANGUAGES = {
    "auto",
    "chinese",
    "english",
    "japanese",
    "korean",
    "german",
    "french",
    "russian",
    "portuguese",
    "spanish",
    "italian",
}

model: Qwen3TTSModel | None = None
inference_lock = asyncio.Lock()


def load_model() -> Qwen3TTSModel:
    if not MODEL_PATH.is_dir():
        raise RuntimeError(f"TTS model not found: {MODEL_PATH}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for this local TTS configuration")
    return Qwen3TTSModel.from_pretrained(
        str(MODEL_PATH),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model
    model = await run_in_threadpool(load_model)
    yield
    model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(
    title="Qwen3-TTS Voice Clone API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok" if model is not None else "loading",
        "model": str(MODEL_PATH),
        "device": "cuda:0",
        "languages": sorted(language.title() for language in SUPPORTED_LANGUAGES),
    }


@app.post("/v1/audio/speech")
async def speech(
    text: str = Form(...),
    language: str = Form("Auto"),
    reference_audio: UploadFile = File(...),
    reference_text: str | None = Form(None),
    x_vector_only_mode: bool = Form(False),
) -> Response:
    if model is None:
        raise HTTPException(status_code=503, detail="TTS model is not ready")
    if not text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    normalized_language = language.strip().lower()
    if normalized_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language: {language}",
        )
    if not x_vector_only_mode and not (reference_text or "").strip():
        raise HTTPException(
            status_code=422,
            detail="reference_text is required unless x_vector_only_mode=true",
        )

    suffix = Path(reference_audio.filename or "reference.wav").suffix or ".wav"
    payload = await reference_audio.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="reference_audio is too large")
    if not payload:
        raise HTTPException(status_code=422, detail="reference_audio is empty")

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(payload)
            temporary_path = temporary.name

        async with inference_lock:
            wavs, sample_rate = await run_in_threadpool(
                lambda: model.generate_voice_clone(
                    text=text,
                    language=language.title(),
                    ref_audio=temporary_path,
                    ref_text=reference_text,
                    x_vector_only_mode=x_vector_only_mode,
                )
            )
        output = io.BytesIO()
        sf.write(output, wavs[0], sample_rate, format="WAV")
        return Response(
            content=output.getvalue(),
            media_type="audio/wav",
            headers={
                "X-Sample-Rate": str(sample_rate),
                "Content-Disposition": 'attachment; filename="speech.wav"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
