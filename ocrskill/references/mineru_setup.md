# MinerU2.5-Pro Local Setup

Model: `opendatalab/MinerU2.5-Pro-2605-1.2B`

Use the Transformers backend on native Windows:

```powershell
python -m pip install "mineru-vl-utils[transformers]" pymupdf pillow python-docx fastapi uvicorn requests
```

Install LibreOffice when OCR inputs may include `.docx` or `.pptx`. On Windows, Microsoft Word/PowerPoint with `pywin32` can be used as a fallback when LibreOffice is unavailable. PDFs do not require a converter.

Pre-download the model into the Hugging Face cache:

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download('opendatalab/MinerU2.5-Pro-2605-1.2B')"
```

Start the API:

```powershell
python C:\Tools\ocrskill\scripts\launch_mineru_api.py --backend transformers --host 127.0.0.1 --port 18010 --preload
```

The scripts default to local-cache loading after the model is downloaded. Add `--allow-download` only when network access should be used during model loading.

Run a file or folder:

```powershell
python C:\Tools\ocrskill\scripts\run_mineru_ocr.py C:\path\to\input --endpoint http://127.0.0.1:18010/ocr
```

Linux/WSL/Docker CUDA can use vLLM for higher throughput:

```bash
python -m pip install "mineru-vl-utils[vllm]"
python scripts/serve_mineru_api.py --backend vllm-engine --host 0.0.0.0 --port 18010
```

If model loading fails on Windows due to VRAM pressure, close other GPU-heavy apps, lower PDF DPI, or use WSL/Docker with vLLM.
