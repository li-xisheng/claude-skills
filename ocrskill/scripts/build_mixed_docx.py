#!/usr/bin/env python3
"""Rebuild a mixed DOCX from ocrskill v2 page JSON and rendered page images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_mineru_ocr import ImageExtractor, write_docx


def load_manifest(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_page_records(output_dir: Path) -> list[dict[str, Any]]:
    json_dir = output_dir / "json"
    if not json_dir.exists():
        raise RuntimeError(f"json/ directory not found in {output_dir}")

    records: list[dict[str, Any]] = []
    for json_path in sorted(json_dir.glob("*.json")):
        records.append(json.loads(json_path.read_text(encoding="utf-8")))
    if not records:
        for json_path in sorted(json_dir.glob("*/*.json")):
            records.append(json.loads(json_path.read_text(encoding="utf-8")))
    if not records:
        raise RuntimeError(f"No page JSON records found in {json_dir}")
    return records


def repair_image_paths(records: list[dict[str, Any]], output_dir: Path) -> None:
    for record in records:
        image_path = Path(record.get("image_path", ""))
        if image_path.exists():
            continue
        page_number = int(record["page_number"])
        candidates = [
            output_dir / "pages" / f"page-{page_number:04d}.png",
            *sorted((output_dir / "pages").glob(f"*/page-{page_number:04d}.png")),
        ]
        for candidate in candidates:
            if candidate.exists():
                record["image_path"] = str(candidate)
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild mixed DOCX from ocrskill output.")
    parser.add_argument("ocr_output_dir", help="Document output folder containing json/ and pages/.")
    parser.add_argument("--output", "-o", help="Output DOCX path. Defaults to <docname>.docx in the folder.")
    parser.add_argument("--docx-mode", default="mixed", choices=["mixed", "textboxes", "image-plus-text", "markdown"])
    args = parser.parse_args()

    output_dir = Path(args.ocr_output_dir).resolve()
    manifest = load_manifest(output_dir)
    docname = manifest.get("docname") or output_dir.name
    docx_path = Path(args.output).resolve() if args.output else output_dir / f"{docname}.docx"

    records = load_page_records(output_dir)
    repair_image_paths(records, output_dir)
    image_quality = int(manifest.get("image_quality", 92))
    ImageExtractor(docname, output_dir, image_quality).extract(records)
    write_docx(records, docx_path, args.docx_mode)
    print(f"Wrote {docx_path}")


if __name__ == "__main__":
    main()
