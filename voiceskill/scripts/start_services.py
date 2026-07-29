#!/usr/bin/env python3
"""Start both local voice APIs as detached background processes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
LOG_ROOT = SKILL_ROOT / "logs"


def is_healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = json.load(response)
        return payload.get("status") == "ok"
    except Exception:
        return False


def start_service(
    name: str,
    python: Path,
    application: str,
    host: str,
    port: int,
) -> None:
    health_url = f"http://{host}:{port}/health"
    if is_healthy(health_url):
        print(f"{name} is already healthy at {health_url}")
        return
    if not python.is_file():
        raise RuntimeError(f"{name} environment not found: {python}")

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_ROOT / f"{name.lower()}.out.log"
    stderr_path = LOG_ROOT / f"{name.lower()}.err.log"
    command = [
        str(python),
        "-m",
        "uvicorn",
        application,
        "--app-dir",
        str(SCRIPT_ROOT),
        "--host",
        host,
        "--port",
        str(port),
    ]
    popen_kwargs: dict[str, object] = {
        "cwd": str(SKILL_ROOT),
        "close_fds": True,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        popen_kwargs["start_new_session"] = True

    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            **popen_kwargs,
        )
    (LOG_ROOT / f"{name.lower()}.pid").write_text(
        f"{process.pid}\n",
        encoding="ascii",
    )

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            error_tail = stderr_path.read_text(
                encoding="utf-8",
                errors="replace",
            )[-4000:]
            raise RuntimeError(f"{name} exited during startup:\n{error_tail}")
        if is_healthy(health_url):
            print(f"{name} started at {health_url} (PID {process.pid})")
            return
        time.sleep(2)
    raise RuntimeError(f"{name} did not become healthy; check {stderr_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--tts-port", type=int, default=8761)
    parser.add_argument("--asr-port", type=int, default=8762)
    args = parser.parse_args()

    if sys.platform == "win32":
        python_relative = Path("Scripts/python.exe")
    else:
        python_relative = Path("bin/python")

    start_service(
        "TTS",
        SKILL_ROOT / ".venv-tts" / python_relative,
        "tts_server:app",
        args.host,
        args.tts_port,
    )
    start_service(
        "ASR",
        SKILL_ROOT / ".venv-asr" / python_relative,
        "asr_server:app",
        args.host,
        args.asr_port,
    )


if __name__ == "__main__":
    main()
