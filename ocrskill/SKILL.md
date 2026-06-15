---
name: ocrskill
description: OCR workflow for local PDF and image document parsing with MinerU2.5-Pro. Use whenever the user asks to OCR PDFs/images, convert scanned PDFs to JSON, Markdown, layout images, or DOCX, run GLM-OCR or MinerU OCR, expose a local OCR API, or preserve page layout in a combined Word document.
---

# OCR Skill

## Default Model

Use `opendatalab/MinerU2.5-Pro-2604-1.2B` as the default OCR/document parsing model. Prefer it over the older 0.9B GLM-OCR workflow unless the user explicitly asks for GLM-OCR or MinerU is unusable in the current environment.

The normal local path is:

1. Render each PDF page to PNG with PyMuPDF.
2. Run MinerU2.5-Pro on each page image.
3. Save per-page JSON and Markdown.
4. Draw layout visualization images from OCR bounding boxes.
5. Merge all pages, in PDF filename and page order, into a DOCX.

## Environment Checks

Before running OCR, check:

- The target folder has PDF files. If no PDFs are present, report that directly.
- Do not question, editorialize, or ask the user to justify ordinary document contents. Treat OCR as a mechanical file conversion workflow.
- CUDA/GPU availability with `nvidia-smi` and `python -c "import torch; print(torch.cuda.is_available())"`.
- Python dependencies: `mineru-vl-utils`, `transformers`, `torch`, `pymupdf`, `pillow`, `python-docx`, `fastapi`, `uvicorn`.
- Native Windows should use the Transformers backend. Use vLLM only on Linux/WSL/Docker CUDA environments.

See `references/mineru_setup.md` for install and model download commands.

## API Workflow

Start a local OCR service when the user asks to expose an interface or when multiple PDFs/pages will be processed:

```powershell
python C:\Tools\ocrskill\scripts\launch_mineru_api.py --backend transformers --host 127.0.0.1 --port 8010 --preload
```

Then process a folder through the API:

```powershell
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py . --endpoint http://127.0.0.1:8010/ocr --dpi 220
```

Use direct mode for smaller jobs or when an API server is unnecessary:

```powershell
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py . --backend transformers --dpi 220
```

## Outputs

The batch script writes to `<input-folder>\mineru_ocr_output` unless `--output` is supplied:

- `pages/<pdf>/page-0001.png`: rendered page images.
- `json/<pdf>/page-0001.json`: raw MinerU page result plus source metadata.
- `layout/<pdf>/page-0001_layout.png`: page image with detected blocks drawn over it.
- `markdown/<pdf>.md` and `combined.md`: extracted Markdown.
- `combined_ocr.docx`: merged DOCX.
- `manifest.json`: run metadata and output paths.

## DOCX Fidelity

Use `--docx-mode textboxes` by default. It converts OCR boxes into absolutely positioned Word text boxes, which gives an editable approximation of the original layout.

Use `--docx-mode image-plus-text` when visual fidelity matters more than editability. It inserts each rendered page image and appends recognized text/Markdown for search and review.

Tables, formulas, and complex figures may be better represented in Markdown/JSON than in editable DOCX text boxes. Keep JSON and layout images as the source of truth for auditing.
