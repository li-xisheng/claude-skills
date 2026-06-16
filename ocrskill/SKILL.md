---
name: ocrskill
description: OCR workflow for local PDF/DOCX/PPTX and image-like document parsing with MinerU2.5-Pro. Use when Codex needs to OCR files or folders, convert DOCX/PPTX through LibreOffice or platform PDF converters, produce ezkotae v2 Markdown plus *_images.json outputs, crop detected image blocks into real files, generate DOCX, run MinerU/GLM-OCR style OCR, or expose/use a local OCR API.
---

# OCR Skill

## Default Model

Use `opendatalab/MinerU2.5-Pro-2605-1.2B` as the default OCR/document parsing model. Prefer MinerU2.5-Pro over older GLM-OCR workflows unless the user explicitly asks for GLM-OCR or MinerU is unusable.

## v2 Workflow

Run `scripts/run_mineru_ocr.py` as the main entry point. It accepts a `.pdf`, `.docx`, `.pptx`, or a folder containing those files.

1. Normalize input: keep PDFs as-is; convert DOCX/PPTX to PDF with LibreOffice/soffice, or Microsoft Office COM on Windows when LibreOffice is unavailable.
2. Render PDF pages to PNG with PyMuPDF.
3. Run MinerU OCR on page images.
4. Crop valid MinerU `image` blocks from rendered page images.
5. Write ezkotae v2 outputs: Markdown, sibling image files, one document-level `*_images.json`, internal raw page JSON, layout overlays, manifest, and optional DOCX.

Do not leave Markdown image references pointing to missing files. The real image filename, Markdown reference, and `*_images.json` key must match exactly.
For website upload, use `{docname}.md`, `{docname}_images.json`, and the sibling `.jpg` files. The `json/page-*.json` files are internal MinerU raw OCR cache/audit artifacts and are not the upload image JSON.

## Environment Checks

Before running OCR:

- Check that the input path contains at least one supported file: `.pdf`, `.docx`, or `.pptx`.
- For `.docx` or `.pptx`, verify a PDF converter is available: LibreOffice/`soffice` is preferred on every OS; Windows can fall back to Microsoft Word/PowerPoint COM when `pywin32` is installed. PDFs do not require a converter.
- Check CUDA/GPU when using local inference: `nvidia-smi` and `python -c "import torch; print(torch.cuda.is_available())"`.
- Check Python dependencies: `mineru-vl-utils`, `transformers`, `torch`, `pymupdf`, `pillow`, `python-docx`, `fastapi`, `uvicorn`, `requests`.
- Use the Transformers backend on native Windows. Use vLLM only on Linux/WSL/Docker CUDA environments.
- Treat OCR as mechanical file conversion. Do not question ordinary document contents.

See `references/mineru_setup.md` for install and model download commands.

## Running OCR

Default local mode:

```powershell
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py "C:\path\to\input" --backend transformers
```

Use `--no-docx` for the minimal ezkotae upload set:

```powershell
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py "C:\path\to\input" --no-docx
```

Use an API server for batch/page parallelism:

```powershell
python C:\Tools\ocrskill\scripts\launch_mineru_api.py --backend transformers --host 127.0.0.1 --preload
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py "C:\path\to\input" --backend api --endpoint <printed-endpoint> --workers 4
```

`launch_mineru_api.py` chooses a free port by default and prints `endpoint=...`, `pid_file=...`, and `log=...`. Stop the server after OCR by killing the printed PID or the PID stored in the printed pid file.

macOS/Linux examples use the same scripts with POSIX paths:

```bash
python /path/to/ocrskill/scripts/launch_mineru_api.py --backend transformers --host 127.0.0.1 --preload
python /path/to/ocrskill/scripts/run_mineru_ocr.py "/path/to/input" --backend api --endpoint "<printed-endpoint>" --workers 4
```

Key flags:

| Flag | Default | Purpose |
|---|---:|---|
| `--output DIR` | file parent or `<folder>\mineru_ocr_output` | Output root; each source writes to `{output}\{docname}` |
| `--dpi N` | 220 | Page render resolution |
| `--workers N` | 1 | Parallel page rendering; also parallel API requests |
| `--backend MODE` | transformers | `transformers`, `vllm-engine`, or `api` |
| `--endpoint URL` | none | OCR API endpoint for API mode |
| `--skip-existing` | off | Reuse existing page JSON, then rerun image extraction/output |
| `--no-docx` | off | Skip DOCX and output only Markdown/images JSON/assets |
| `--docx-mode MODE` | mixed | `mixed`, `textboxes`, `image-plus-text`, or `markdown` |
| `--image-quality N` | 92 | JPEG quality for extracted image crops |

In `transformers` and `vllm-engine` modes, OCR inference is sequential. In `api` mode, `--workers` sends concurrent requests.

Rebuild DOCX without rerunning OCR:

```powershell
python C:\Tools\ocrskill\scripts\build_mixed_docx.py "C:\path\to\output\docname" --docx-mode mixed
```

## Output Contract

For every input document, write:

```text
{output}\{docname}\
├── {docname}.md
├── {docname}_images.json        # one JSON per document; contains all image base64 entries
├── {docname}-{hash}.jpg
├── pages\page-0001.png
├── json\page-0001.json          # internal raw page OCR cache, not upload payload
├── layout\page-0001_layout.png
├── manifest.json
└── {docname}.docx
```

`docname` is always the original source filename stem, even when DOCX/PPTX is converted to PDF first. `manifest.json` records `source_type` as `pdf`, `docx`, or `pptx`.

`{docname}_images.json` is the only upload images JSON for the document. It uses schema `https://ezkotae.dev/schemas/images/v1` and contains every extracted image keyed by the same filename used in Markdown:

```json
{
  "$schema": "https://ezkotae.dev/schemas/images/v1",
  "docname": "契約書2025",
  "images": {
    "契約書2025-a1b2c3d4e5.jpg": "/9j/4AAQSkZJRg..."
  },
  "generated_by": "ocrskill-v2",
  "generated_at": "2026-06-15T00:00:00Z",
  "source_type": "pdf",
  "image_count": 1
}
```

The Markdown file must reference real sibling files:

```markdown
![図の説明](契約書2025-a1b2c3d4e5.jpg)
```

At the end of each run, read the printed `Upload set` summary to confirm the output location. It lists the output folder, Markdown path, `{docname}_images.json` path, sibling `.jpg` count, optional DOCX path, and manifest path. If console output is unavailable, open `{output}\{docname}\manifest.json`; it records `markdown_path`, `images_json_path`, `docx_path`, and `output_dir`.

## DOCX Modes

- `mixed`: default. Position text boxes and embed cropped image blocks.
- `textboxes`: position text only; no cropped images.
- `image-plus-text`: insert each rendered page image, then recognized text.
- `markdown`: write text/Markdown without layout preservation.

Tables, formulas, and complex figures may be better represented in Markdown/JSON than editable DOCX. Keep JSON and layout images as the audit source of truth.
