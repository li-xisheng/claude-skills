#!/usr/bin/env python3
"""Serve MinerU2.5-Pro OCR behind a small FastAPI interface."""

from __future__ import annotations

import argparse
import io
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

DEFAULT_MODEL_ID = "opendatalab/MinerU2.5-Pro-2604-1.2B"

app = FastAPI(title="MinerU OCR API")
_client_lock = threading.Lock()
_client: Any | None = None
_json2md: Any | None = None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _resolve_model_ref(model_id: str, local_files_only: bool) -> str:
    if Path(model_id).exists():
        return model_id
    if not local_files_only:
        return model_id
    try:
        from huggingface_hub import snapshot_download

        return snapshot_download(model_id, local_files_only=True)
    except Exception as exc:
        raise RuntimeError(
            f"Model is not available in the local Hugging Face cache: {model_id}. "
            "Download it first with snapshot_download or rerun with --allow-download."
        ) from exc


def _load_client() -> Any:
    global _client, _json2md
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        model_id = os.environ.get("MINERU_MODEL_ID", DEFAULT_MODEL_ID)
        backend = os.environ.get("MINERU_BACKEND", "transformers")
        image_analysis = os.environ.get("MINERU_IMAGE_ANALYSIS", "0") == "1"
        local_files_only = os.environ.get("MINERU_LOCAL_FILES_ONLY", "1") == "1"
        model_ref = _resolve_model_ref(model_id, local_files_only)

        try:
            from mineru_vl_utils import MinerUClient
            from mineru_vl_utils.post_process import json2md
        except ImportError as exc:
            raise RuntimeError(
                'Missing mineru-vl-utils. Install with: python -m pip install "mineru-vl-utils[transformers]"'
            ) from exc

        if backend == "transformers":
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_ref,
                dtype="auto",
                device_map="auto",
                local_files_only=local_files_only,
            )
            processor = AutoProcessor.from_pretrained(model_ref, use_fast=True, local_files_only=local_files_only)
            _client = MinerUClient(
                backend="transformers",
                model=model,
                processor=processor,
                image_analysis=image_analysis,
            )
        elif backend == "vllm-engine":
            from mineru_vl_utils import MinerULogitsProcessor
            from vllm import LLM

            llm = LLM(
                model=model_ref,
                logits_processors=[MinerULogitsProcessor],
            )
            _client = MinerUClient(
                backend="vllm-engine",
                vllm_llm=llm,
                image_analysis=image_analysis,
            )
        else:
            raise RuntimeError(f"Unsupported MINERU_BACKEND: {backend}")

        _json2md = json2md
        return _client


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "model": os.environ.get("MINERU_MODEL_ID", DEFAULT_MODEL_ID),
        "backend": os.environ.get("MINERU_BACKEND", "transformers"),
        "local_files_only": os.environ.get("MINERU_LOCAL_FILES_ONLY", "1") == "1",
        "loaded": _client is not None,
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        payload = await file.read()
        image = Image.open(io.BytesIO(payload)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read image: {exc}") from exc

    try:
        client = _load_client()
        content_list = client.two_step_extract(image)
        markdown = _json2md(content_list) if _json2md else ""
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "content_list": _to_jsonable(content_list),
        "markdown": markdown,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve MinerU2.5-Pro OCR over HTTP.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--backend", default="transformers", choices=["transformers", "vllm-engine"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--image-analysis", action="store_true")
    parser.add_argument("--allow-download", action="store_true", help="Allow Hugging Face network checks/downloads at load time.")
    parser.add_argument("--preload", action="store_true", help="Load the model before accepting requests.")
    args = parser.parse_args()

    os.environ["MINERU_MODEL_ID"] = args.model_id
    os.environ["MINERU_BACKEND"] = args.backend
    os.environ["MINERU_IMAGE_ANALYSIS"] = "1" if args.image_analysis else "0"
    os.environ["MINERU_LOCAL_FILES_ONLY"] = "0" if args.allow_download else "1"

    if args.preload:
        _load_client()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
