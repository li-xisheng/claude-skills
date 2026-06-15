#!/usr/bin/env python3
"""Batch OCR PDFs with MinerU2.5-Pro and merge the result into a DOCX."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape

import fitz
import requests
from docx import Document
from docx.enum.section import WD_SECTION
from docx.oxml import parse_xml
from docx.shared import Pt
from PIL import Image, ImageDraw, ImageFont

DEFAULT_MODEL_ID = "opendatalab/MinerU2.5-Pro-2604-1.2B"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "document"


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def resolve_model_ref(model_id: str, local_files_only: bool) -> str:
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


def collect_pdfs(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(p for p in input_dir.glob(pattern) if p.is_file())



def render_pdf_page(page: fitz.Page, image_path: Path, dpi: int) -> dict[str, Any]:
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(image_path))
    return {
        "page_width_pt": float(page.rect.width),
        "page_height_pt": float(page.rect.height),
        "image_width": int(pix.width),
        "image_height": int(pix.height),
    }


class ApiRecognizer:
    def __init__(self, endpoint: str) -> None:
        endpoint = endpoint.rstrip("/")
        self.url = endpoint if endpoint.endswith("/ocr") else endpoint + "/ocr"

    def recognize(self, image_path: Path) -> dict[str, Any]:
        with image_path.open("rb") as handle:
            response = requests.post(
                self.url,
                files={"file": (image_path.name, handle, "image/png")},
                timeout=None,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"OCR API failed for {image_path}: {response.status_code} {response.text[:1000]}")
        return response.json()


class DirectRecognizer:
    def __init__(self, model_id: str, backend: str, image_analysis: bool, local_files_only: bool) -> None:
        try:
            from mineru_vl_utils import MinerUClient
            from mineru_vl_utils.post_process import json2md
        except ImportError as exc:
            raise RuntimeError(
                'Missing mineru-vl-utils. Install with: python -m pip install "mineru-vl-utils[transformers]"'
            ) from exc

        self.json2md = json2md
        model_ref = resolve_model_ref(model_id, local_files_only)
        if backend == "transformers":
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_ref,
                dtype="auto",
                device_map="auto",
                local_files_only=local_files_only,
            )
            processor = AutoProcessor.from_pretrained(model_ref, use_fast=True, local_files_only=local_files_only)
            self.client = MinerUClient(
                backend="transformers",
                model=model,
                processor=processor,
                image_analysis=image_analysis,
            )
        elif backend == "vllm-engine":
            from mineru_vl_utils import MinerULogitsProcessor
            from vllm import LLM

            llm = LLM(model=model_ref, logits_processors=[MinerULogitsProcessor])
            self.client = MinerUClient(
                backend="vllm-engine",
                vllm_llm=llm,
                image_analysis=image_analysis,
            )
        else:
            raise RuntimeError(f"Unsupported backend: {backend}")

    def recognize(self, image_path: Path) -> dict[str, Any]:
        with Image.open(image_path) as image:
            content_list = self.client.two_step_extract(image.convert("RGB"))
        return {
            "content_list": to_jsonable(content_list),
            "markdown": self.json2md(content_list),
        }


def text_from_item(item: dict[str, Any]) -> str:
    for key in ("text", "content", "markdown", "latex", "html"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def content_items(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, list):
        for child in node:
            yield from content_items(child)
        return
    if not isinstance(node, dict):
        return

    has_text = bool(text_from_item(node))
    has_box = raw_bbox(node) is not None
    if has_text or has_box:
        yield node

    for key in ("children", "blocks", "lines", "spans", "cells", "items"):
        child = node.get(key)
        if isinstance(child, (dict, list)):
            yield from content_items(child)


def raw_bbox(item: dict[str, Any]) -> list[float] | None:
    for key in ("bbox", "box", "rect"):
        value = item.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            try:
                return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]
            except (TypeError, ValueError):
                return None

    for key in ("poly", "polygon"):
        value = item.get(key)
        if not isinstance(value, (list, tuple)) or not value:
            continue
        points: list[tuple[float, float]] = []
        for point in value:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                try:
                    points.append((float(point[0]), float(point[1])))
                except (TypeError, ValueError):
                    pass
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return [min(xs), min(ys), max(xs), max(ys)]
    return None


def normalize_bbox_to_pixels(
    bbox: list[float],
    image_width: int,
    image_height: int,
    page_width_pt: float,
    page_height_pt: float,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox
    max_value = max(abs(v) for v in bbox)

    if max_value <= 1.5:
        x0, x1 = x0 * image_width, x1 * image_width
        y0, y1 = y0 * image_height, y1 * image_height
    elif max_value <= max(page_width_pt, page_height_pt) * 1.5:
        x_scale = image_width / page_width_pt if page_width_pt else 1.0
        y_scale = image_height / page_height_pt if page_height_pt else 1.0
        x0, x1 = x0 * x_scale, x1 * x_scale
        y0, y1 = y0 * y_scale, y1 * y_scale

    x0, x1 = sorted((max(0.0, x0), min(float(image_width), x1)))
    y0, y1 = sorted((max(0.0, y0), min(float(image_height), y1)))
    return x0, y0, x1, y1


def item_type(item: dict[str, Any]) -> str:
    value = item.get("type") or item.get("category") or item.get("label") or "block"
    return str(value)


def draw_layout_image(page_record: dict[str, Any], layout_path: Path) -> int:
    content_list = page_record.get("content_list", [])
    image_path = Path(page_record["image_path"])
    with Image.open(image_path) as source:
        image = source.convert("RGB")

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    colors = {
        "title": (220, 38, 38),
        "text": (37, 99, 235),
        "table": (5, 150, 105),
        "formula": (147, 51, 234),
        "image": (234, 88, 12),
        "block": (75, 85, 99),
    }
    count = 0

    for item in content_items(content_list):
        bbox = raw_bbox(item)
        if not bbox:
            continue
        box = normalize_bbox_to_pixels(
            bbox,
            int(page_record["image_width"]),
            int(page_record["image_height"]),
            float(page_record["page_width_pt"]),
            float(page_record["page_height_pt"]),
        )
        if box[2] - box[0] < 2 or box[3] - box[1] < 2:
            continue

        kind = item_type(item).lower()
        color = next((value for name, value in colors.items() if name in kind), colors["block"])
        draw.rectangle(box, outline=color, width=3)
        label = item_type(item)[:28]
        text_box = draw.textbbox((box[0] + 2, box[1] + 2), label, font=font)
        draw.rectangle(text_box, fill=(255, 255, 255))
        draw.text((box[0] + 2, box[1] + 2), label, fill=color, font=font)
        count += 1

    layout_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(layout_path)
    return count


def fallback_markdown(content_list: Any) -> str:
    lines: list[str] = []
    for item in content_items(content_list):
        text = text_from_item(item)
        if text:
            lines.append(text)
    return "\n\n".join(lines)


def configure_section(section: Any, width_pt: float, height_pt: float) -> None:
    section.page_width = Pt(width_pt)
    section.page_height = Pt(height_pt)
    section.top_margin = Pt(0)
    section.bottom_margin = Pt(0)
    section.left_margin = Pt(0)
    section.right_margin = Pt(0)
    section.header_distance = Pt(0)
    section.footer_distance = Pt(0)


def textbox_xml(shape_id: str, x_pt: float, y_pt: float, width_pt: float, height_pt: float, text: str) -> str:
    font_size = max(6, min(12, height_pt / max(1, math.ceil(len(text) / 50)) / 1.6))
    half_points = int(round(font_size * 2))
    escaped_lines = [escape(line) for line in text.splitlines() or [""]]
    text_runs = []
    for index, line in enumerate(escaped_lines):
        if index:
            text_runs.append("<w:br/>")
        text_runs.append(f'<w:t xml:space="preserve">{line}</w:t>')
    text_body = "".join(text_runs)
    return f"""
<w:pict xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xmlns:v="urn:schemas-microsoft-com:vml"
        xmlns:o="urn:schemas-microsoft-com:office:office">
  <v:shape id="{shape_id}" type="#_x0000_t202"
    style="position:absolute;margin-left:{x_pt:.2f}pt;margin-top:{y_pt:.2f}pt;width:{width_pt:.2f}pt;height:{height_pt:.2f}pt;z-index:1;mso-position-horizontal-relative:page;mso-position-vertical-relative:page"
    stroked="f" filled="f">
    <v:textbox inset="0,0,0,0">
      <w:txbxContent>
        <w:p>
          <w:r>
            <w:rPr><w:sz w:val="{half_points}"/></w:rPr>
            {text_body}
          </w:r>
        </w:p>
      </w:txbxContent>
    </v:textbox>
  </v:shape>
</w:pict>
"""


def add_textbox(doc: Document, shape_id: str, x_pt: float, y_pt: float, width_pt: float, height_pt: float, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    run = paragraph.add_run()
    run._r.append(parse_xml(textbox_xml(shape_id, x_pt, y_pt, width_pt, height_pt, text)))


def write_docx(page_records: list[dict[str, Any]], output_path: Path, mode: str) -> None:
    doc = Document()
    if not page_records:
        doc.add_paragraph("No OCR pages were generated.")
        doc.save(output_path)
        return

    shape_index = 1000
    first_page = True
    for record in page_records:
        if first_page:
            section = doc.sections[0]
            first_page = False
        else:
            section = doc.add_section(WD_SECTION.NEW_PAGE)
        width_pt = float(record["page_width_pt"])
        height_pt = float(record["page_height_pt"])
        configure_section(section, width_pt, height_pt)

        markdown = record.get("markdown") or fallback_markdown(record.get("content_list", []))
        if mode == "image-plus-text":
            doc.add_picture(record["image_path"], width=Pt(width_pt))
            doc.add_page_break()
            doc.add_paragraph(f'{record["source_pdf"]} - page {record["page_number"]}')
            for paragraph_text in markdown.split("\n\n"):
                if paragraph_text.strip():
                    doc.add_paragraph(paragraph_text.strip())
            continue

        if mode == "markdown":
            doc.add_paragraph(f'{record["source_pdf"]} - page {record["page_number"]}')
            for paragraph_text in markdown.split("\n\n"):
                if paragraph_text.strip():
                    doc.add_paragraph(paragraph_text.strip())
            continue

        added = 0
        for item in content_items(record.get("content_list", [])):
            text = text_from_item(item)
            bbox = raw_bbox(item)
            if not text or not bbox:
                continue
            x0, y0, x1, y1 = normalize_bbox_to_pixels(
                bbox,
                int(record["image_width"]),
                int(record["image_height"]),
                width_pt,
                height_pt,
            )
            x_pt = x0 / float(record["image_width"]) * width_pt
            y_pt = y0 / float(record["image_height"]) * height_pt
            w_pt = max(4.0, (x1 - x0) / float(record["image_width"]) * width_pt)
            h_pt = max(4.0, (y1 - y0) / float(record["image_height"]) * height_pt)
            add_textbox(doc, f"_mineru_{shape_index}", x_pt, y_pt, w_pt, h_pt, text)
            shape_index += 1
            added += 1

        if added == 0:
            doc.add_paragraph(markdown or f'{record["source_pdf"]} - page {record["page_number"]}')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def process_pdf(
    pdf_path: Path,
    output_dir: Path,
    recognizer: ApiRecognizer | DirectRecognizer,
    dpi: int,
    skip_existing: bool,
) -> list[dict[str, Any]]:
    pdf_slug = slugify(pdf_path.stem)
    page_records: list[dict[str, Any]] = []

    with fitz.open(pdf_path) as pdf:
        for index, page in enumerate(pdf, start=1):
            page_name = f"page-{index:04d}"
            image_path = output_dir / "pages" / pdf_slug / f"{page_name}.png"
            json_path = output_dir / "json" / pdf_slug / f"{page_name}.json"
            layout_path = output_dir / "layout" / pdf_slug / f"{page_name}_layout.png"

            if skip_existing and json_path.exists():
                with json_path.open("r", encoding="utf-8") as handle:
                    record = json.load(handle)
            else:
                page_meta = render_pdf_page(page, image_path, dpi)
                ocr_result = recognizer.recognize(image_path)
                record = {
                    "source_pdf": str(pdf_path),
                    "source_pdf_name": pdf_path.name,
                    "page_number": index,
                    "image_path": str(image_path),
                    "layout_path": str(layout_path),
                    **page_meta,
                    "content_list": ocr_result.get("content_list", ocr_result),
                    "markdown": ocr_result.get("markdown", ""),
                }
                json_path.parent.mkdir(parents=True, exist_ok=True)
                with json_path.open("w", encoding="utf-8") as handle:
                    json.dump(to_jsonable(record), handle, ensure_ascii=False, indent=2)

            if not Path(record.get("layout_path", layout_path)).exists() and Path(record["image_path"]).exists():
                record["layout_box_count"] = draw_layout_image(record, layout_path)
            elif Path(record["image_path"]).exists():
                record["layout_box_count"] = draw_layout_image(record, layout_path)

            page_records.append(record)
            print(f"OCR complete: {pdf_path.name} page {index}/{len(pdf)}")

    return page_records


def write_markdown_files(page_records: list[dict[str, Any]], output_dir: Path) -> Path:
    by_pdf: dict[str, list[dict[str, Any]]] = {}
    for record in page_records:
        by_pdf.setdefault(record["source_pdf_name"], []).append(record)

    markdown_dir = output_dir / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    combined_parts: list[str] = []
    for pdf_name, records in by_pdf.items():
        parts = [f"# {pdf_name}", ""]
        for record in records:
            body = record.get("markdown") or fallback_markdown(record.get("content_list", []))
            parts.extend([f"## Page {record['page_number']}", "", body, ""])
        text = "\n".join(parts).strip() + "\n"
        (markdown_dir / f"{slugify(Path(pdf_name).stem)}.md").write_text(text, encoding="utf-8")
        combined_parts.append(text)

    combined_path = output_dir / "combined.md"
    combined_path.write_text("\n\n".join(combined_parts), encoding="utf-8")
    return combined_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch OCR PDFs with MinerU2.5-Pro.")
    parser.add_argument("input_dir", nargs="?", default=".", help="Folder containing PDF files.")
    parser.add_argument("--output", help="Output folder. Defaults to <input_dir>/mineru_ocr_output.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--backend", default="transformers", choices=["transformers", "vllm-engine"])
    parser.add_argument("--endpoint", help="Existing OCR endpoint, e.g. http://127.0.0.1:8010/ocr.")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--image-analysis", action="store_true")
    parser.add_argument("--allow-download", action="store_true", help="Allow Hugging Face network checks/downloads at load time.")
    parser.add_argument("--docx-mode", default="textboxes", choices=["textboxes", "image-plus-text", "markdown"])
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output).resolve() if args.output else input_dir / "mineru_ocr_output"
    found_pdfs = collect_pdfs(input_dir, args.recursive)
    if not found_pdfs:
        print(f"No PDF files found in {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    recognizer: ApiRecognizer | DirectRecognizer
    if args.endpoint:
        recognizer = ApiRecognizer(args.endpoint)
        recognizer_mode = f"api:{args.endpoint}"
    else:
        recognizer = DirectRecognizer(args.model_id, args.backend, args.image_analysis, not args.allow_download)
        recognizer_mode = args.backend

    all_pages: list[dict[str, Any]] = []
    for pdf_path in found_pdfs:
        all_pages.extend(process_pdf(pdf_path, output_dir, recognizer, args.dpi, args.skip_existing))

    combined_md = write_markdown_files(all_pages, output_dir)
    combined_docx = output_dir / "combined_ocr.docx"
    write_docx(all_pages, combined_docx, args.docx_mode)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "model_id": args.model_id,
        "recognizer": recognizer_mode,
        "dpi": args.dpi,
        "docx_mode": args.docx_mode,
        "pdf_count": len(found_pdfs),
        "page_count": len(all_pages),
        "combined_markdown": str(combined_md),
        "combined_docx": str(combined_docx),
        "pdfs": [str(path) for path in found_pdfs],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {combined_docx}")


if __name__ == "__main__":
    main()
