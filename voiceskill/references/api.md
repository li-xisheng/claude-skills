# Local voice API

## Endpoints

| Capability | URL | Request | Response |
|---|---|---|---|
| TTS health | `GET http://127.0.0.1:8761/health` | none | JSON |
| Voice-clone TTS | `POST http://127.0.0.1:8761/v1/audio/speech` | multipart | WAV |
| ASR health | `GET http://127.0.0.1:8762/health` | none | JSON |
| Transcription | `POST http://127.0.0.1:8762/v1/audio/transcriptions` | multipart | JSON |

Interactive OpenAPI pages are at `/docs` on each port.

Start both services in the background with:

```text
python scripts/start_services.py
```

Runtime logs and PID files are written under `logs/`.

## TTS request

Required multipart fields:

- `text`: target text.
- `reference_audio`: authorized reference voice audio.
- `reference_text`: accurate reference transcript, required unless `x_vector_only_mode=true`.

Optional fields:

- `language`: `Auto` (default), `Chinese`, `English`, `Japanese`, `Korean`, `German`, `French`, `Russian`, `Portuguese`, `Spanish`, or `Italian`.
- `x_vector_only_mode`: default `false`; use `true` only without a reference transcript.

PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8761/v1/audio/speech `
  -F "text=こんにちは。音声合成のテストです。" `
  -F "language=Japanese" `
  -F "reference_audio=@C:\audio\reference.wav" `
  -F "reference_text=这是参考音频的准确文本。" `
  --output C:\audio\speech.wav
```

## ASR request

Required multipart field:

- `file`: audio file.

Optional fields:

- `language`: omit or set `auto` for detection; otherwise pass an upstream language name such as `Chinese`, `Japanese`, or `English`.
- `timestamps`: `true` to return aligned spans in seconds; default `false`.
- `context`: domain terms or names that help recognition.

PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8762/v1/audio/transcriptions `
  -F "file=@C:\audio\speech.wav" `
  -F "language=auto" `
  -F "timestamps=true"
```

Example response:

```json
{
  "language": "Japanese",
  "text": "こんにちは。音声合成のテストです。",
  "timestamps": [
    {"text": "こんにちは", "start": 0.12, "end": 0.88}
  ]
}
```

## Direct launch on non-Windows systems

Create separate Python 3.12 environments because the upstream packages pin different Transformers patch versions. Then launch:

```text
python -m uvicorn tts_server:app --app-dir scripts --host 127.0.0.1 --port 8761
python -m uvicorn asr_server:app --app-dir scripts --host 127.0.0.1 --port 8762
```

## Environment overrides

- `QWEN_TTS_MODEL`
- `QWEN_ASR_MODEL`
- `QWEN_ASR_ALIGNER`
- `VOICE_MAX_UPLOAD_BYTES`

The servers serialize GPU inference per process. If simultaneous services exceed VRAM, stop the idle service and run only the needed endpoint.
