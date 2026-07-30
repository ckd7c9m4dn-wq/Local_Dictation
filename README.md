# Local Dictation

Private, fully-local voice dictation for macOS. Hold a key, speak, and text
appears at your cursor in any app — like Wispr Flow, but **nothing ever
leaves your machine**.

Setting this up for someone non-technical? Send them the `installer/` folder
— `installer/README.txt` walks through a one-double-click install.

```
hold Right Option ─▶ mic ─▶ Parakeet or Whisper (MLX, on-GPU) ─▶ Ollama cleanup ─▶ paste at cursor
```

## Run it

Launch **Local Dictation** from /Applications (rebuild it any time with
`uv run python scripts/build_app.py`). The bundle is a thin stub that runs
this project's venv, so code changes only need an app relaunch, not a rebuild.
Logs go to `~/.config/local_dictation/app.log`.

Alternatives: double-click **Local Dictation.command** (runs in a Terminal
window with live logs), or:

```sh
uv run local-dictation
```

A 🎤 appears in the menu bar. **Hold Right Option**, speak, release.
🔴 = recording, ✍️ = transcribing.

First launch, macOS will ask for two permissions (grant to your terminal app):

- **Microphone** — to record you
- **Accessibility / Input Monitoring** — for the global hotkey and the ⌘V paste
  (System Settings → Privacy & Security if the prompt doesn't appear)

## Menu options

- **Engine: Parakeet (fast)** — ~0.3 s per utterance, best for English
- **Engine: Whisper (multilingual)** — ~2.5 s, 99 languages
- **AI Cleanup (Ollama)** — removes "um/uh", fixes grammar, applies
  self-corrections, formats spoken lists as bullets/numbers (local
  `llama3.2:3b`, ~1 s). Toggle off for raw, fastest output.
- **Settings →**
  - **Cleanup Hotkey** — pick the hold-to-talk key that runs AI cleanup
    (applies immediately)
  - **Verbatim Hotkey** — a second hold-to-talk key that skips cleanup for
    raw ASR output; must be a different key from the cleanup hotkey
  - **Start at Login** — installs/removes a LaunchAgent for the /Applications bundle
  - **Save Dictation History** — append every dictation to
    `~/.config/local_dictation/history.txt` (Open Dictation History shows it)
  - **Shortcuts** — lists the phrases that expand to canned text. Say one
    alone (e.g. just "humanize") and the whole dictation is replaced by its
    expansion, skipping cleanup and find/replace. Edit them in
    `~/.config/local_dictation/shortcuts.txt`, one block per shortcut delimited
    by `@shortcut: <phrase>` and `@end`; everything in between (blank lines,
    `#` comments, markdown, code, Obsidian `[[wiki links]]`) is kept
    verbatim, so long-form structured prompts/snippets are safe to paste in.
    List several comma-separated phrases on the `@shortcut:` line to give
    one expansion multiple trigger aliases (e.g. to cover a likely ASR
    mis-transcription of the phrase). Changes apply to the next dictation.
  - **Edit Cleanup Prompt** — the cleanup instructions live in
    `~/.config/local_dictation/cleanup_prompt.txt`; edits apply to the next
    dictation, no restart. Keep the `Input:`/`Output:` examples — they are
    sent as few-shot chat turns.
  - **Edit Find/Replace List** — mechanical, post-cleanup whole-word
    substitutions in `~/.config/local_dictation/replacements.txt`
    (`term -> standard term`, case-insensitive).
  - **Edit Terminology List** — names, jargon, and product names in
    `~/.config/local_dictation/vocabulary.txt` that the AI cleanup stage uses
    to fix mis-transcriptions (e.g. nudging "clod" back to "Claude"); edits
    apply to the next dictation.
  - **Edit System Prompt** — general preferences/context for the AI cleanup
    stage in `~/.config/local_dictation/system_prompt.txt` (e.g. "I'm in the
    UK — use £", or how to format spoken numbers); edits apply to the next
    dictation.

Settings persist in `~/.config/local_dictation/config.json`.

## Requirements

- Apple Silicon Mac, [uv](https://docs.astral.sh/uv/), and
  [Ollama](https://ollama.com) running with `llama3.2:3b` pulled
  (only needed for the cleanup toggle).

See `implementationplan.md` for the architecture and research notes.
