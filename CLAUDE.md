# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Local Dictation is a private, fully-local voice dictation menu-bar app for macOS
(Apple Silicon only). Hold a hotkey, speak, and the transcribed text is pasted
at the cursor in whatever app is focused — modeled on Wispr Flow, but nothing
ever leaves the machine. Pipeline:

```
hold hotkey ──▶ mic capture ──▶ ASR engine ──▶ [optional Ollama cleanup] ──▶ find/replace ──▶ paste at cursor
                (sounddevice)   (switchable)     (local, toggleable)                          (clipboard + ⌘V)
                        all orchestrated by a rumps menu-bar app (local_dictation/app.py)
```

See `README.md` for the user-facing menu reference and `implementationplan.md`
for the original research/design notes (Wispr Flow's cloud architecture vs.
this project's local equivalent, hardware targets, milestones).

## Commands

```sh
# Run from source (uses the uv-managed venv, Python 3.12 pinned — see .python-version)
uv run local-dictation

# Rebuild and reinstall the /Applications/Local Dictation.app bundle
# (only needed after packaging changes; source edits just need an app relaunch
# since the bundle's executable is a thin stub into this repo's venv)
uv run python scripts/build_app.py

# Stage-by-stage pipeline diagnostic (mic -> transcribe -> cleanup -> inject),
# reports which stage is broken
uv run python scripts/diagnose.py
```

There is no test suite, linter, or CI config in this repo. There is no build
step for iterating on source — only `scripts/build_app.py` (packaging) and
`scripts/diagnose.py` (runtime diagnostics) exist.

Logs: `~/.config/local_dictation/app.log`. Requires Ollama running locally
(`ollama.com`) with a chat model pulled for the cleanup stage, and macOS
Microphone + Accessibility/Input Monitoring permissions granted to whichever
process runs the app (Terminal, when running from source).

## Architecture

**Config and user-editable state** all live under `~/.config/local_dictation/`,
not in the repo:
- `config.json` — persisted settings (`local_dictation/config.py`'s `Config`
  class; every `__setitem__` immediately writes to disk)
- `cleanup_prompt.txt` — the Ollama cleanup system prompt + few-shot
  examples, user-editable, reloaded fresh on every dictation (no restart
  needed). `cleanup.py::_parse_prompt` splits the file on the literal
  `\nExamples:` marker into a system prompt plus `Input:`/`Output:` pairs,
  which are sent as real chat turns (small models follow real turns far more
  reliably than examples embedded in the system prompt).
- `replacements.txt` — user-editable find/replace pairs (`term -> standard
  term`, case-insensitive, whole-word), applied after cleanup and before
  paste/history.
- `history.txt` — append-only dictation log (only written if
  `history_enabled`).

**`local_dictation/app.py`** (`LocalDictationApp(rumps.App)`) is the hub: it owns
the `Config` instance, builds the entire menu tree in `__init__`, and defines
`_process()` as the single place the whole pipeline is stitched together
(transcribe → optional cleanup → find/replace → optional trailing space →
inject → optional history write). Any new pipeline stage or settings toggle
should be wired through here, following the existing pattern: a `DEFAULTS`
key in `config.py`, a `rumps.MenuItem` with a `_toggle_*`/`_pick_*` callback
that flips `sender.state` and writes to `self.config_store`, added under
`settings_menu`.

**All MLX model work (both ASR engines) runs on a single dedicated worker
thread** (`self._jobs` queue, drained by `_worker()`), because MLX GPU
streams are thread-bound — loading and inference must happen on the same
thread. Anything that touches an `Engine` must go through `self._jobs.put(...)`
rather than being called directly from the hotkey callback or main thread.

**Two independent hold-to-talk hotkeys** run concurrently
(`self.hotkey` / `self.verbatim_hotkey`, both `hotkey.HoldToTalk` instances):
one triggers cleanup, the other (`verbatim_hotkey`) skips the Ollama stage
entirely for raw ASR output. `_start_recording`/`_stop_recording` track which
mode is active via `self._verbatim` and ignore a stop event that doesn't
match the mode that started the recording (handles overlapping key events).
`HoldToTalk` runs the callbacks on its own dispatch thread, never on
pynput's macOS event-tap thread: a tap callback that stalls ~1s gets the
tap silently disabled by macOS (`kCGEventTapDisabledByTimeout`, which
pynput never recovers from), permanently killing the hotkey. Never put
blocking work in the tap path, and never touch AppKit (menu-bar title,
notifications) from a background thread — use `app._set_icon()` /
`AppHelper.callAfter`, which hop to the main thread.

**ASR engines** (`local_dictation/engines/`) implement the `Engine` ABC
(`base.py`: `load()` + `transcribe(audio) -> str`) and are lazily
instantiated/cached per-name in `app._engines`, then `.load()`'d once and
kept warm. `get_engine(name)` in `engines/__init__.py` is the registry —
add new engines there. Engines receive 16 kHz float32 mono numpy audio
directly from `audio.Recorder`.

**Failure philosophy**: dictation must never crash the app or silently lose
the user's speech. `cleanup.clean()` and `inject`-adjacent code catch broad
exceptions and fall back to returning the raw/unmodified text; `_process()`
wraps the whole pipeline in try/except and always resets the menu-bar icon
in `finally`.

**Packaging** (`scripts/build_app.py`): the installed `.app` bundle is not a
frozen/bundled Python app — its `CFBundleExecutable` is a tiny compiled C
stub (`scripts/launcher.c`) that just execs this repo's
`.venv/bin/local-dictation`. This means source changes take effect on app
relaunch alone; `build_app.py` only needs re-running when packaging metadata,
the icon, or the launcher itself changes. The bundle is ad-hoc codesigned
(`codesign -s -`) for a stable TCC identity so macOS permission grants
persist across rebuilds.
