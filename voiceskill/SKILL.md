---
name: voiceskill
description: Run local multilingual speech synthesis, reference-audio voice cloning, and speech recognition through Qwen3-TTS and Qwen3-ASR. Use whenever Codex needs to synthesize speech/audio, clone an authorized voice, transcribe audio/video, detect spoken language, or return word/character timestamps. Prefer the local APIs supplied by this skill instead of remote speech services.
---

# Voice Skill

Use the local Qwen services for every speech-synthesis or speech-recognition task.

## Locate the installation

Set `VOICE_SKILL_ROOT` to this skill directory. Model paths default to:

- `models/Qwen3-TTS-12Hz-1.7B-Base`
- `models/Qwen3-ASR-1.7B`
- `models/Qwen3-ForcedAligner-0.6B`

Read [references/api.md](references/api.md) when calling or troubleshooting the APIs.

## Ensure the services are ready

1. Call `GET http://127.0.0.1:8761/health` for TTS.
2. Call `GET http://127.0.0.1:8762/health` for ASR.
3. If a service is unavailable, run `python scripts/start_services.py`. For foreground diagnostics on Windows, use `scripts/start-tts.ps1` or `scripts/start-asr.ps1`.
   - Any platform: invoke the matching virtual environment and server module described in the API reference.
4. If models or environments are absent, run `scripts/setup.ps1`, then `scripts/download-models.py`.
5. Do not silently fall back to a remote service. Report a local setup or hardware error clearly.

## Synthesize speech

Call `POST /v1/audio/speech` on port 8761 using multipart form data.

- Supply `text`, `language`, `reference_audio`, and normally `reference_text`.
- Use `language=Auto` for mixed or unknown input; use an explicit language when known.
- Set `x_vector_only_mode=true` only when no accurate reference transcript is available. Expect lower cloning quality.
- Save the returned `audio/wav` bytes to the requested output path.
- Use only voices the user owns or is authorized to clone. Do not imply another person endorsed generated speech.

Supported TTS languages: Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, and Italian.

## Transcribe speech

Call `POST /v1/audio/transcriptions` on port 8762 using multipart form data.

- Supply the audio as `file`.
- Omit `language`, or use `language=auto`, to enable automatic language detection.
- Set `timestamps=true` to return forced-alignment spans in seconds.
- Pass optional `context` only when it materially helps with names or domain vocabulary.
- Preserve the returned `language`, `text`, and `timestamps` fields when the user asks for structured results.

ASR supports 52 languages and dialects. Timestamp alignment requires the bundled Qwen3-ForcedAligner model and supports the languages documented by the upstream model.

## Handle long or non-audio inputs

- Extract audio from video with ffmpeg before transcription.
- Split unusually long recordings into sensible chunks if GPU memory or request limits are reached.
- Preserve chronological order and offset timestamps when recombining chunks.
- Never overwrite the source media.

## Validate outputs

- For TTS, confirm the returned file opens, has a nonzero duration, and uses the reported sample rate.
- For ASR, sanity-check detected language and text; for timestamps, confirm spans are monotonic and within the media duration.
- Keep reference audio and generated artifacts local unless the user explicitly asks to publish or send them.
