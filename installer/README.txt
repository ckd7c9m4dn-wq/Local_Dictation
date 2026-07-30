LOCAL DICTATION — INSTALL GUIDE
================================

What this is
-------------
Local Dictation types out what you say, right where your cursor is, in
any app. Hold a key, talk, let go — done. Everything happens on your
own Mac; your voice is never sent over the internet.

Before you start, you need
---------------------------
- An Apple Silicon Mac (M1, M2, M3, or M4 — not an older Intel Mac)
- About 15-20 minutes and a decent internet connection (it downloads
  a speech-recognition model, roughly 1-2 GB)
- Your Mac password (needed once, to install a couple of small,
  standard developer tools)

To install
-----------
1. Double-click "Install Local Dictation.command" in this folder.

2. A Terminal window will open and start setting things up. This is
   normal — just follow the on-screen instructions.

3. Partway through, macOS may pop up a window asking to install
   "Command Line Developer Tools." Click Install, wait for it to
   finish, then double-click the installer again to pick up where
   it left off.

4. You'll be asked about Ollama, a free tool that cleans up "ums" and
   grammar in what you say. It's optional but recommended — a browser
   tab will open to download it. If you'd rather skip it, just press
   Enter; Local Dictation still works, it just won't tidy up your
   speech.

5. Near the end, macOS will ask for two permissions. Turn ON
   "Local Dictation" for both:
     - Microphone (so it can hear you)
     - Accessibility (so it can "type" for you)

6. Quit Local Dictation (right-click its microphone icon in the menu
   bar, top of your screen, and choose Quit) and reopen it from your
   Applications folder. Look for the small microphone icon 🎤 in your
   menu bar — that means it's ready.

To use it
----------
- Hold down the Right Option key, say what you want, then let go.
  Your words are typed wherever your cursor is.
- Holding Right Command instead skips the cleanup step and types
  exactly what you said, word for word.
- Click the 🎤 menu-bar icon for more options (switching keys,
  turning cleanup on/off, custom shortcuts, etc).

To uninstall
-------------
Double-click "Uninstall Local Dictation.command" in this folder.
Your settings and dictation history are kept in case you reinstall
later; the uninstaller tells you where they are if you want to
delete those too.

Trouble?
---------
Whoever gave you this app can help. If they ask, the diagnostic tool
at scripts/diagnose.py (one level up from this folder) checks each
step — microphone, transcription, cleanup, and typing — and reports
which one, if any, is broken.
