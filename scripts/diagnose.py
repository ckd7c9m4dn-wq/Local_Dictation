"""Stage-by-stage diagnostic for Local Dictation. Run inside the venv:

    python scripts/diagnose.py

Speak while it records. It reports mic level, transcription, cleanup,
and clipboard injection, and says which stage (if any) is broken.
"""

import time

import numpy as np

RECORD_SECONDS = 4


def main():
    print("=== Local Dictation diagnostics ===\n")

    # 1. Microphone
    import sounddevice as sd

    from local_dictation.audio import SAMPLE_RATE, Recorder

    print(f"Default input device: {sd.query_devices(kind='input')['name']}")
    print(f"\n[1/4] Recording {RECORD_SECONDS}s — SPEAK NOW...")
    rec = Recorder()
    rec.start()
    time.sleep(RECORD_SECONDS)
    audio = rec.stop()
    rms = float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0
    peak = float(np.abs(audio).max()) if len(audio) else 0.0
    print(f"      captured {len(audio)/SAMPLE_RATE:.1f}s, RMS={rms:.4f}, peak={peak:.4f}")
    if len(audio) == 0:
        print("      FAIL: no audio captured at all (stream never delivered frames).")
        return
    if peak < 0.001:
        print("      FAIL: audio is pure silence — macOS is blocking the microphone.")
        print("      Fix: System Settings > Privacy & Security > Microphone > enable Terminal,")
        print("      then fully quit (Cmd+Q) and reopen Terminal.")
        return
    print("      OK: microphone is live.")

    # 2. Transcription
    from local_dictation.config import Config
    from local_dictation.engines import get_engine

    cfg = Config()
    eng = get_engine(cfg["engine"])
    print(f"\n[2/4] Transcribing with {cfg['engine']}...")
    t0 = time.time()
    text = eng.transcribe(audio)
    print(f"      {time.time()-t0:.2f}s -> {text!r}")
    if not text:
        print("      FAIL: engine returned empty text (was there speech in the clip?)")
        return
    print("      OK.")

    # 3. Cleanup
    if cfg["cleanup_enabled"]:
        from local_dictation.cleanup import clean

        print(f"\n[3/4] Cleanup via Ollama ({cfg['ollama_model']})...")
        t0 = time.time()
        cleaned = clean(text, cfg["ollama_model"], cfg["ollama_url"])
        print(f"      {time.time()-t0:.2f}s -> {cleaned!r}")
        if cleaned == text:
            print("      note: unchanged text can mean Ollama unreachable/timed out (raw fallback).")
    else:
        print("\n[3/4] Cleanup disabled in config — skipped.")

    # 4. Injection (types into whatever is focused — this terminal is fine)
    from local_dictation.inject import inject

    print("\n[4/4] Injecting text via clipboard+Cmd-V in 2s — leave this window focused...")
    time.sleep(2)
    inject("local dictation injection test")
    print("\nIf 'local dictation injection test' appeared on your command line above,")
    print("every stage works. If not, Accessibility permission is the problem.")


if __name__ == "__main__":
    main()
