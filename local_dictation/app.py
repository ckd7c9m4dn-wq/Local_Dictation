"""Local Dictation menu-bar app: ties hotkey → audio → ASR → cleanup → inject."""

import logging
import queue
import subprocess
import threading

import rumps
from PyObjCTools import AppHelper

from . import history, loginitem
from .audio import SAMPLE_RATE, Recorder
from .cleanup import PROMPT_PATH, clean, ensure_prompt_file, list_models, warm
from .config import CONFIG_DIR, CONFIG_PATH, Config
from .engines import get_engine
from .hotkey import KEY_LABELS, HoldToTalk
from .inject import inject
from .preferences import PREFERENCES_PATH, ensure_preferences_file
from .replacements import REPLACEMENTS_PATH, apply as apply_replacements, ensure_replacements_file
from .shortcuts import (
    SHORTCUTS_PATH,
    ensure_shortcuts_file,
    expand as expand_shortcut,
    list_phrases as list_shortcut_phrases,
)
from .vocabulary import VOCABULARY_PATH, ensure_vocabulary_file

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler(CONFIG_DIR / "app.log")],
)
log = logging.getLogger("local_dictation")

ICON_IDLE = "🎤"
ICON_RECORDING = "🔴"
ICON_BUSY = "✍️"

MIN_SECONDS = 0.3  # ignore accidental taps shorter than this

# Trade-off notes shown next to each cleanup model in the menu (benchmarked
# on this M4 / 24 GB). Unknown models fall back to a size-based note.
MODEL_NOTES = {
    "qwen3:4b-instruct": "recommended: best faithfulness, ~1s",
    "gemma3:12b": "highest quality, ~2-4s, needs ~8GB free RAM",
    "qwen3:4b": "thinking model: unusable for cleanup (leaks reasoning)",
}

# Models bigger than this can't be held in RAM alongside the ASR model
# without swapping, so they're hidden from the menu entirely.
MAX_MODEL_BYTES = 16e9


class LocalDictationApp(rumps.App):
    def __init__(self):
        super().__init__(ICON_IDLE, quit_button="Quit Local Dictation")
        self.config_store = Config()
        self.recorder = Recorder()
        self._engines = {}

        # All MLX model work runs on this one thread: MLX GPU streams are
        # thread-bound, so loading and inference must share a thread.
        self._jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

        self.engine_items = {
            "parakeet": rumps.MenuItem(
                "Parakeet — fastest (~0.3s), English-focused", callback=self._pick_engine
            ),
            "whisper": rumps.MenuItem(
                "Whisper — slower (~2.5s), 99 languages", callback=self._pick_engine
            ),
        }
        self.cleanup_item = rumps.MenuItem("AI Cleanup (Ollama)", callback=self._toggle_cleanup)
        self.cleanup_item.state = bool(self.config_store["cleanup_enabled"])
        self.status_item = rumps.MenuItem("")
        self.status_item.set_callback(None)
        self._update_status_label()

        # One submenu per mode; both draw from the same key list. _pick_hotkey
        # figures out which mode a click came from by which dict holds it.
        self.cleanup_hotkey_items = {
            name: rumps.MenuItem(label, callback=self._pick_hotkey)
            for name, label in KEY_LABELS.items()
        }
        cleanup_hotkey_menu = rumps.MenuItem("Cleanup Hotkey")
        for item in self.cleanup_hotkey_items.values():
            cleanup_hotkey_menu.add(item)

        self.verbatim_hotkey_items = {
            name: rumps.MenuItem(label, callback=self._pick_hotkey)
            for name, label in KEY_LABELS.items()
        }
        verbatim_hotkey_menu = rumps.MenuItem("Verbatim Hotkey")
        for item in self.verbatim_hotkey_items.values():
            verbatim_hotkey_menu.add(item)

        self.history_item = rumps.MenuItem(
            "Save Dictation History", callback=self._toggle_history
        )
        self.history_item.state = bool(self.config_store["history_enabled"])

        self.login_item = rumps.MenuItem("Start at Login", callback=self._toggle_login)
        self.login_item.state = loginitem.enabled()

        self.trailing_space_item = rumps.MenuItem(
            "Add Trailing Space After Paste", callback=self._toggle_trailing_space
        )
        self.trailing_space_item.state = bool(self.config_store["trailing_space"])

        self.whisper_language_item = rumps.MenuItem(
            "Whisper: Auto-Detect Language (~1s slower)",
            callback=self._toggle_whisper_language,
        )
        self.whisper_language_item.state = bool(self.config_store["whisper_auto_language"])

        self.shortcuts_menu = rumps.MenuItem("Shortcuts")
        self._build_shortcuts_menu()

        settings_menu = rumps.MenuItem("Settings")
        settings_menu.add(cleanup_hotkey_menu)
        settings_menu.add(verbatim_hotkey_menu)
        settings_menu.add(self.login_item)
        settings_menu.add(self.history_item)
        settings_menu.add(self.trailing_space_item)
        settings_menu.add(self.whisper_language_item)
        settings_menu.add(self.shortcuts_menu)
        settings_menu.add(rumps.MenuItem("Open Dictation History", callback=self._open_history))
        settings_menu.add(rumps.MenuItem("Edit Cleanup Prompt", callback=self._edit_prompt))
        settings_menu.add(
            rumps.MenuItem("Edit Find/Replace List", callback=self._edit_replacements)
        )
        settings_menu.add(
            rumps.MenuItem("Edit Terminology List", callback=self._edit_vocabulary)
        )
        settings_menu.add(rumps.MenuItem("Edit System Prompt", callback=self._edit_preferences))
        settings_menu.add(rumps.MenuItem("Edit Config File", callback=self._edit_config))

        engine_header = rumps.MenuItem("Speech-to-Text (both modes):")
        engine_header.set_callback(None)
        cleanup_header = rumps.MenuItem("Cleanup (cleanup hotkey only):")
        cleanup_header.set_callback(None)

        self.model_items = {}
        self.models_menu = rumps.MenuItem("Cleanup Model")
        self._build_model_menu()

        self.menu = [
            self.status_item,
            None,
            engine_header,
            self.engine_items["parakeet"],
            self.engine_items["whisper"],
            None,
            cleanup_header,
            self.cleanup_item,
            self.models_menu,
            None,
            settings_menu,
            None,
        ]
        self._sync_engine_checkmarks()
        self._sync_hotkey_checkmarks()
        ensure_prompt_file()
        ensure_replacements_file()
        ensure_vocabulary_file()
        ensure_shortcuts_file()
        ensure_preferences_file()
        self.config_store.save()  # materialize config.json so it's editable

        self._check_accessibility()
        self._verbatim = False
        self.hotkey = HoldToTalk(
            self.config_store["hotkey"],
            lambda: self._start_recording(verbatim=False),
            lambda: self._stop_recording(verbatim=False),
        )
        self.hotkey.start()
        self.verbatim_hotkey = HoldToTalk(
            self.config_store["verbatim_hotkey"],
            lambda: self._start_recording(verbatim=True),
            lambda: self._stop_recording(verbatim=True),
        )
        self.verbatim_hotkey.start()

        self._jobs.put(self._preload)

    @staticmethod
    def _check_accessibility():
        """Ask macOS for Accessibility trust, showing the system prompt if not granted."""
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        if AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}):
            log.info("accessibility: trusted")
        else:
            log.warning(
                "accessibility: NOT trusted — hotkey will not work. Grant it in "
                "System Settings > Privacy & Security > Accessibility, then relaunch."
            )

    def _set_icon(self, icon: str):
        """Update the menu-bar icon from any thread (AppKit is main-thread-only)."""
        AppHelper.callAfter(setattr, self, "title", icon)

    # -- worker thread ---------------------------------------------------------

    def _worker(self):
        while True:
            job = self._jobs.get()
            try:
                job()
            except Exception:
                log.exception("job failed")
                self._set_icon(ICON_IDLE)

    def _preload(self):
        """Warm the ASR model and Ollama so the first dictation is fast."""
        self._set_icon(ICON_BUSY)
        # Ollama warm-up is a plain HTTP call — it doesn't need the MLX
        # thread, so run it concurrently with engine loading instead of
        # after it.
        ollama_thread = None
        if self.config_store["cleanup_enabled"]:
            ollama_thread = threading.Thread(
                target=warm,
                args=(self.config_store["ollama_model"], self.config_store["ollama_url"]),
                daemon=True,
            )
            ollama_thread.start()
        try:
            self._current_engine().load()
            log.info("engine %r ready", self.config_store["engine"])
            if ollama_thread is not None:
                ollama_thread.join()
                log.info("ollama warm")
        finally:
            self._set_icon(ICON_IDLE)

    def _current_engine(self):
        name = self.config_store["engine"]
        if name not in self._engines:
            self._engines[name] = get_engine(name)
        engine = self._engines[name]
        if name == "whisper":
            engine.language = None if self.config_store["whisper_auto_language"] else "en"
        return engine

    # -- menu callbacks --------------------------------------------------------

    def _build_model_menu(self):
        """Populate the Cleanup Model submenu from installed Ollama models."""
        models = list_models(self.config_store["ollama_url"])
        if not models:
            unavailable = rumps.MenuItem("Ollama not running")
            unavailable.set_callback(None)
            self.models_menu.add(unavailable)
            return
        for m in sorted(models, key=lambda m: m["name"]):
            name = m["name"]
            if m["size"] > MAX_MODEL_BYTES:
                log.info("hiding %s from model menu: %.0f GB exceeds RAM", name, m["size"] / 1e9)
                continue
            note = MODEL_NOTES.get(name, f"{m['size'] / 1e9:.1f} GB, untested")
            item = rumps.MenuItem(f"{name} — {note}", callback=self._pick_model)
            self.model_items[name] = item
            self.models_menu.add(item)
        self._sync_model_checkmarks()

    def _build_shortcuts_menu(self):
        """List the currently-defined shortcut phrases plus an editor link.

        Rebuilt from disk at startup and whenever the editor is opened; the
        expansion itself is always read fresh at dictation time, so a saved
        edit takes effect on the next utterance even before the list here
        catches up.
        """
        if self.shortcuts_menu._menu is not None:
            self.shortcuts_menu.clear()
        header = rumps.MenuItem("Say one of these alone to expand it:")
        header.set_callback(None)
        self.shortcuts_menu.add(header)
        phrases = sorted(list_shortcut_phrases())
        if phrases:
            for phrase in phrases:
                item = rumps.MenuItem(f"  • {phrase}")
                item.set_callback(None)
                self.shortcuts_menu.add(item)
        else:
            empty = rumps.MenuItem("  (none defined yet)")
            empty.set_callback(None)
            self.shortcuts_menu.add(empty)
        self.shortcuts_menu.add(None)
        self.shortcuts_menu.add(
            rumps.MenuItem("Edit Shortcuts List", callback=self._edit_shortcuts)
        )

    def _pick_model(self, sender):
        name = next(n for n, item in self.model_items.items() if item is sender)
        self.config_store["ollama_model"] = name
        self._sync_model_checkmarks()
        self._jobs.put(
            lambda: warm(name, self.config_store["ollama_url"])
        )
        log.info("cleanup model changed to %s", name)

    def _sync_model_checkmarks(self):
        current = self.config_store["ollama_model"]
        for name, item in self.model_items.items():
            item.state = name == current

    def _pick_engine(self, sender):
        name = "parakeet" if sender is self.engine_items["parakeet"] else "whisper"
        self.config_store["engine"] = name
        self._sync_engine_checkmarks()
        self._jobs.put(self._current_engine().load)

    def _sync_engine_checkmarks(self):
        current = self.config_store["engine"]
        for name, item in self.engine_items.items():
            item.state = name == current

    def _update_status_label(self):
        cleanup = KEY_LABELS.get(self.config_store["hotkey"], self.config_store["hotkey"])
        verbatim = KEY_LABELS.get(
            self.config_store["verbatim_hotkey"], self.config_store["verbatim_hotkey"]
        )
        self.status_item.title = f"Hold {cleanup} → cleanup   ·   Hold {verbatim} → verbatim"

    def _pick_hotkey(self, sender):
        if sender in self.cleanup_hotkey_items.values():
            mode, items = "hotkey", self.cleanup_hotkey_items
        else:
            mode, items = "verbatim_hotkey", self.verbatim_hotkey_items
        name = next(n for n, item in items.items() if item is sender)
        other = "verbatim_hotkey" if mode == "hotkey" else "hotkey"
        if name == self.config_store[other]:
            # The two modes can't share a key — the one that started a
            # recording wouldn't be distinguishable from the other on release.
            self._sync_hotkey_checkmarks()  # revert the visual selection
            other_label = "verbatim" if other == "verbatim_hotkey" else "cleanup"
            rumps.alert(
                "Hotkey already in use",
                f"{KEY_LABELS.get(name, name)} is assigned to the {other_label} "
                "hotkey. Choose a different key for each mode.",
            )
            return
        self.config_store[mode] = name
        self._restart_hotkey(mode, name)
        self._sync_hotkey_checkmarks()
        self._update_status_label()
        log.info("%s changed to %s", mode, KEY_LABELS.get(name, name))

    def _restart_hotkey(self, mode: str, name: str):
        verbatim = mode == "verbatim_hotkey"
        old = self.verbatim_hotkey if verbatim else self.hotkey
        old.stop()
        new = HoldToTalk(
            name,
            lambda: self._start_recording(verbatim=verbatim),
            lambda: self._stop_recording(verbatim=verbatim),
        )
        new.start()
        if verbatim:
            self.verbatim_hotkey = new
        else:
            self.hotkey = new

    def _sync_hotkey_checkmarks(self):
        cleanup = self.config_store["hotkey"]
        verbatim = self.config_store["verbatim_hotkey"]
        for name, item in self.cleanup_hotkey_items.items():
            item.state = name == cleanup
        for name, item in self.verbatim_hotkey_items.items():
            item.state = name == verbatim

    def _toggle_login(self, sender):
        if sender.state:
            loginitem.disable()
        else:
            loginitem.enable()
        sender.state = loginitem.enabled()
        log.info("start at login: %s", bool(sender.state))

    def _toggle_history(self, sender):
        sender.state = not sender.state
        self.config_store["history_enabled"] = bool(sender.state)

    def _toggle_trailing_space(self, sender):
        sender.state = not sender.state
        self.config_store["trailing_space"] = bool(sender.state)

    def _toggle_whisper_language(self, sender):
        sender.state = not sender.state
        self.config_store["whisper_auto_language"] = bool(sender.state)
        log.info("whisper auto-detect language: %s", bool(sender.state))

    def _open_history(self, _):
        history.ensure_file()
        subprocess.run(["open", "-t", str(history.HISTORY_PATH)])

    def _edit_prompt(self, _):
        ensure_prompt_file()
        subprocess.run(["open", "-t", str(PROMPT_PATH)])

    def _edit_replacements(self, _):
        ensure_replacements_file()
        subprocess.run(["open", "-t", str(REPLACEMENTS_PATH)])

    def _edit_vocabulary(self, _):
        ensure_vocabulary_file()
        subprocess.run(["open", "-t", str(VOCABULARY_PATH)])

    def _edit_preferences(self, _):
        ensure_preferences_file()
        subprocess.run(["open", "-t", str(PREFERENCES_PATH)])

    def _edit_shortcuts(self, _):
        ensure_shortcuts_file()
        subprocess.run(["open", "-t", str(SHORTCUTS_PATH)])
        self._build_shortcuts_menu()  # refresh the listed phrases

    def _edit_config(self, _):
        self.config_store.save()
        subprocess.run(["open", "-t", str(CONFIG_PATH)])

    def _toggle_cleanup(self, sender):
        sender.state = not sender.state
        self.config_store["cleanup_enabled"] = bool(sender.state)
        if sender.state:
            threading.Thread(
                target=warm,
                args=(self.config_store["ollama_model"], self.config_store["ollama_url"]),
                daemon=True,
            ).start()

    # -- dictation flow --------------------------------------------------------

    def _start_recording(self, verbatim: bool):
        if self.recorder.recording:
            return
        self._verbatim = verbatim
        self.recorder.start()
        self._set_icon(ICON_RECORDING)
        if not verbatim and self.config_store["cleanup_enabled"]:
            # Re-warm Ollama while the user is speaking. Normally a cache
            # hit (~0.1s), but if keep_alive (30m) expired, this overlaps
            # the model reload + prompt eval (~6s) with the speech instead
            # of paying it after key release.
            threading.Thread(
                target=warm,
                args=(self.config_store["ollama_model"], self.config_store["ollama_url"]),
                daemon=True,
            ).start()

    def _stop_recording(self, verbatim: bool):
        if not self.recorder.recording or verbatim != self._verbatim:
            return  # releasing a key that didn't start this recording
        audio = self.recorder.stop()
        self._set_icon(ICON_BUSY)
        self._jobs.put(lambda: self._process(audio, verbatim))

    def _process(self, audio, verbatim: bool):
        seconds = len(audio) / SAMPLE_RATE
        if len(audio) < MIN_SECONDS * SAMPLE_RATE:
            log.info("recording too short (%.2fs), ignored", seconds)
            self._set_icon(ICON_IDLE)
            return
        peak = float(abs(audio).max())
        log.info("captured %.1fs of audio (peak level %.4f)", seconds, peak)
        if peak < 0.001:
            log.warning(
                "audio is pure silence — is Microphone permission granted "
                "to your terminal in System Settings > Privacy & Security?"
            )
        try:
            text = self._current_engine().transcribe(audio)
            log.info("transcribed%s: %r", " (verbatim)" if verbatim else "", text)
            # A whole-utterance shortcut short-circuits the pipeline: the
            # expansion is fixed canned text, so cleanup and find/replace
            # would only corrupt it. Checked in both modes on the raw
            # transcript, before any rewriting can alter the trigger phrase.
            expansion = expand_shortcut(text) if text else None
            cleaned = False
            if expansion is not None:
                log.info("shortcut matched: %r", text.strip())
                text = expansion
            else:
                if text and not verbatim and self.config_store["cleanup_enabled"]:
                    text = clean(
                        text,
                        self.config_store["ollama_model"],
                        self.config_store["ollama_url"],
                    )
                    cleaned = True
                    log.info("cleaned: %r", text)
                if text:
                    text = apply_replacements(text)
            if text:
                if self.config_store["trailing_space"]:
                    text += " "
                inject(text)
                log.info("injected into frontmost app")
                if self.config_store["history_enabled"]:
                    history.append(text, self.config_store["engine"], cleaned)
        except Exception as exc:  # dictation must never crash the app
            log.exception("dictation failed")
            try:
                rumps.notification("Local Dictation", "Transcription failed", str(exc))
            except Exception:
                pass  # notifications unavailable when not running as a bundle
        finally:
            self._set_icon(ICON_IDLE)


def main():
    LocalDictationApp().run()


if __name__ == "__main__":
    main()
