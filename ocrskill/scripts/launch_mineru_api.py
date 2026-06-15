#!/usr/bin/env python3
"""Launch the MinerU OCR API as a detached local background process."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch MinerU OCR API in the background.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--backend", default="transformers", choices=["transformers", "vllm-engine"])
    parser.add_argument("--model-id", default="opendatalab/MinerU2.5-Pro-2605-1.2B")
    parser.add_argument("--preload", action="store_true")
    parser.add_argument("--image-analysis", action="store_true")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--log", default=r"C:\Tools\ocrskill_server.log")
    parser.add_argument("--pid-file", default=r"C:\Tools\ocrskill_server.pid")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    serve_script = script_dir / "serve_mineru_api.py"
    command = [
        sys.executable,
        str(serve_script),
        "--backend",
        args.backend,
        "--model-id",
        args.model_id,
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.preload:
        command.append("--preload")
    if args.image_analysis:
        command.append("--image-analysis")
    if args.allow_download:
        command.append("--allow-download")

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")

    creationflags = 0
    if sys.platform == "win32":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )

    process = subprocess.Popen(
        command,
        cwd=str(script_dir.parent),
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        close_fds=True,
        creationflags=creationflags,
    )
    Path(args.pid_file).write_text(str(process.pid), encoding="utf-8")
    print(f"started pid={process.pid} url=http://{args.host}:{args.port}/health log={log_path}")


if __name__ == "__main__":
    main()
