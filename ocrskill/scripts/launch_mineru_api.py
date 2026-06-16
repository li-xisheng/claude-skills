#!/usr/bin/env python3
"""Launch the MinerU OCR API as a detached local background process."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((_probe_host(host), 0))
        return int(sock.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch MinerU OCR API in the background.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Port to bind. Use 0 or omit for an automatic free port.")
    parser.add_argument("--backend", default="transformers", choices=["transformers", "vllm-engine"])
    parser.add_argument("--model-id", default="opendatalab/MinerU2.5-Pro-2605-1.2B")
    parser.add_argument("--preload", action="store_true")
    parser.add_argument("--image-analysis", action="store_true")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--log", help="Log file. Defaults to the system temp directory.")
    parser.add_argument("--pid-file", help="PID file. Defaults to the system temp directory.")
    args = parser.parse_args()
    if args.port < 0 or args.port > 65535:
        raise SystemExit("--port must be between 0 and 65535.")
    if args.port == 0:
        args.port = find_free_port(args.host)

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

    temp_dir = Path(tempfile.gettempdir())
    log_path = Path(args.log) if args.log else temp_dir / f"ocrskill_server_{args.port}.log"
    pid_file = Path(args.pid_file) if args.pid_file else temp_dir / f"ocrskill_server_{args.port}.pid"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    creationflags = 0
    start_new_session = sys.platform != "win32"
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
        start_new_session=start_new_session,
    )
    pid_file.write_text(str(process.pid), encoding="utf-8")
    display_host = _probe_host(args.host)
    print(
        f"started pid={process.pid} endpoint=http://{display_host}:{args.port}/ocr "
        f"health=http://{display_host}:{args.port}/health pid_file={pid_file} log={log_path}"
    )


if __name__ == "__main__":
    main()
