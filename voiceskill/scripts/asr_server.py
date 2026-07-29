#!/usr/bin/env python3
"""FastAPI server for Qwen3-ASR with language detection and timestamps."""

from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from qwen_asr import Qwen3ASRModel


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(
    os.environ.get(
        "QWEN_ASR_MODEL",
        SKILL_ROOT / "models" / "Qwen3-ASR-1.7B",
    )
).resolve()
ALIGNER_PATH = Path(
    os.environ.get(
        "QWEN_ASR_ALIGNER",
        SKILL_ROOT / "models" / "Qwen3-ForcedAligner-0.6B",
    )
).resolve()
MAX_UPLOAD_BYTES = int(os.environ.get("VOICE_MAX_UPLOAD_BYTES", 500 * 1024 * 1024))

model: Qwen3ASRModel | None = None
inference_lock = asyncio.Lock()


def load_model() -> Qwen3ASRModel:
    if not MODEL_PATH.is_dir():
        raise RuntimeError(f"ASR model not found: {MODEL_PATH}")
    if not ALIGNER_PATH.is_dir():
        raise RuntimeError(f"ASR timestamp aligner not found: {ALIGNER_PATH}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for this local ASR configuration")
    return Qwen3ASRModel.from_pretrained(
        str(MODEL_PATH),
        forced_aligner=str(ALIGNER_PATH),
        forced_aligner_kwargs={
            "dtype": torch.bfloat16,
            "device_map": "cuda:0",
            "attn_implementation": "sdpa",
        },
        dtype=torch.bfloat16,
        device_map="cuda:0",
        attn_implementation="sdpa",
        max_inference_batch_size=1,
        max_new_tokens=4096,
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
    title="Qwen3-ASR Transcription API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok" if model is not None else "loading",
        "model": str(MODEL_PATH),
        "aligner": str(ALIGNER_PATH),
        "device": "cuda:0",
        "automatic_language_detection": True,
        "timestamps": True,
    }


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    timestamps: bool = Form(False),
    context: str = Form(""),
) -> dict[str, object]:
    if model is None:
        raise HTTPException(status_code=503, detail="ASR model is not ready")

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="audio file is too large")
    if not payload:
        raise HTTPException(status_code=422, detail="audio file is empty")

    requested_language = (language or "").strip()
    if requested_language.lower() == "auto" or not requested_language:
        requested_language = None

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(payload)
            temporary_path = temporary.name

        async with inference_lock:
            results = await run_in_threadpool(
                lambda: model.transcribe(
                    audio=temporary_path,
                    language=requested_language,
                    context=context,
                    return_time_stamps=timestamps,
                )
            )
        result = results[0]
        spans = []
        if result.time_stamps is not None:
            spans = [
                {
                    "text": item.text,
                    "start": float(item.start_time),
                    "end": float(item.end_time),
                }
                for item in result.time_stamps
            ]
        return {
            "language": result.language,
            "text": result.text,
            "timestamps": spans,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
