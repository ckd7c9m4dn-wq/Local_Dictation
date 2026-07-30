# Local Dictation — Implementation Plan

A private, fully-local voice dictation app for macOS, modeled on Wispr Flow's
architecture but with nothing ever leaving the machine.

## How Wispr Flow works (research summary)

Wispr Flow is a menu-bar daemon: hold a hotkey, speak, text lands at your
cursor in any app. Its pipeline is cloud-based:

1. Audio captured locally, streamed to their servers.
2. **ASR**: proprietary Whisper-class model tuned for conversational speech.
3. **LLM cleanup**: fine-tuned Llama (Baseten/AWS, TensorRT-LLM) removes
   filler words, fixes grammar, and formats for the target app.
   Target: < 700 ms end-to-end at p99.
4. Text injected into the focused app via accessibility APIs.

Privacy cost: audio *and* screen context go to the cloud. This project
replicates the pipeline entirely on-device.

## Local architecture

```
hold hotkey ──▶ mic capture ──▶ ASR engine ──▶ [optional Ollama cleanup] ──▶ paste at cursor
                (sounddevice)   (switchable)     (llama3.2:3b, local)        (clipboard + ⌘V)
                        all orchestrated by a rumps menu-bar app
```

### Decisions (confirmed 2026-07-03)

| Decision | Choice |
|---|---|
| ASR engines | **Both, switchable**: Parakeet (parakeet-mlx, fast English) and Whisper large-v3-turbo (mlx-whisper, 99 languages) |
| AI cleanup | **Yes**, via local Ollama `llama3.2:3b` (already installed), toggleable |
| App form | **Python menu-bar app** (rumps) |

### Target hardware

Apple M4, 24 GB RAM, macOS 15.7. Expected latency: Parakeet ~0.1–0.5 s per
utterance, Whisper turbo ~1 s, cleanup ~0.3–0.8 s when enabled.

## Components

- `local_dictation/app.py` — rumps menu-bar app; wiring, status icon (idle/recording/transcribing), engine switcher, cleanup toggle, quit.
- `local_dictation/hotkey.py` — global hold-to-talk listener (pynput). Default: hold **Right Option**; press starts recording, release stops.
- `local_dictation/audio.py` — 16 kHz mono capture via sounddevice.
- `local_dictation/engines/` — `base.py` (interface), `parakeet.py`, `whisper.py`. Models lazy-loaded on first use, kept warm after.
- `local_dictation/cleanup.py` — Ollama HTTP call (`localhost:11434`) with a strict "clean, never add content" prompt.
- `local_dictation/inject.py` — save clipboard → set transcript → synthesize ⌘V → restore clipboard.
- `local_dictation/config.py` — JSON config in `~/.config/local_dictation/` (engine, cleanup on/off, hotkey).

## Environment

- `uv`-managed venv pinned to Python 3.12 (system 3.14 is too new for some MLX wheels).
- Dependencies: `parakeet-mlx`, `mlx-whisper`, `sounddevice`, `pynput`, `rumps`, `requests`.
- macOS permissions needed at first run: **Microphone** + **Accessibility** (for the hotkey listener and ⌘V synthesis) — granted to the terminal/Python.

## Milestones

1. ✅ Research + plan (this document)
2. Environment setup, deps verified on Apple Silicon
3. Core pipeline: record → transcribe with both engines, measure latency
4. Ollama cleanup stage
5. Hotkey + text injection
6. Menu-bar app, config, end-to-end test
7. (Later, if wanted) launch-at-login, custom vocabulary, per-app formatting, streaming partial results
