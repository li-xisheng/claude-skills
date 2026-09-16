#!/usr/bin/env python3
"""Download the pinned Qwen voice models from Hugging Face."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download


MODELS = {
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base": "Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-ASR-1.7B": "Qwen3-ASR-1.7B",
    "Qwen/Qwen3-ForcedAligner-0.6B": "Qwen3-ForcedAligner-0.6B",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models",
    )
    args = parser.parse_args()
    models_dir = args.models_dir.resolve()
    models_dir.mkdir(parents=True, exist_ok=True)

    api = HfApi()
    manifest: dict[str, dict[str, str]] = {}
    for repo_id, directory in MODELS.items():
        revision = api.model_info(repo_id).sha
        destination = models_dir / directory
        print(f"Downloading {repo_id}@{revision} -> {destination}", flush=True)
        snapshot_download(
            repo_id=repo_id,
            revision=revision,
            local_dir=destination,
        )
        manifest[repo_id] = {
            "revision": revision,
            "path": str(destination),
        }

    manifest_path = models_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Model manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
