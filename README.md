# CLI Music Generator 🎛️

A lightweight **GUI step-sequencer** for crafting beats. Click pads to program patterns, tweak synths, **record your performance to WAV**, and **save presets**.

---

## Features
- Pad grid for **kick / bass / clap / snare / hihat**
- **BPM slider** and **pattern length** (8 / 16 / 32)
- Per-instrument controls  
  - Kick: Volume, Decay  
  - Bass: Volume, Freq, Decay, Wave (saw/square/sine)
- **Live recording** of what you hear (Start → Stop → Save or Cancel)  
  - Red **REC** dot indicates recording is active
- **Save Track (JSON)** presets to `./exports/`
- **Load Track (JSON)** presets back into the grid from `./exports/`

---

## Getting Started (macOS, Apple Silicon)

```bash
# 1) System deps (Homebrew)
brew update
brew install python@3.11 portaudio libsndfile flac libogg libvorbis ffmpeg

# 2) Virtual env
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

# 3) Python packages
pip install -r requirements.txt

# 4) Run
python3 main.py
```

## Tools Used
- **pyo**: audio engine, synths, recording
- **Tkinter**: GUI
- **pydub**: offline export helper

Notes: Kick and Bass are synthesized (no samples needed). Clap/Snare/Hihat use WAVs from assets/. pygame/mido appear in requirements.txt for legacy CLI features but aren't required at runtime for the GUI.

## Project Layout
```bash
cli-music-gen/
├─ assets/
│  ├─ bass.wav          # (not required; bass is synthesized)
│  ├─ clap.wav          # used
│  ├─ hihat.wav         # used
│  ├─ kick.wav          # (not required; kick is synthesized)
│  └─ snare.wav         # used
├─ engine/
│  ├─ audio_exporter.py     # offline export to WAV (pydub)
│  ├─ __init__.py
│  ├─ live_sequencer.py     # pyo server, timing, recording, transport
│  ├─ pattern_exporter.py   # preset (JSON) export helpers
│  ├─ synths.py             # Kick/Bass synths + sample players (hat/clap/snare)
│  └─ track.py              # BPM, patterns, steps
├─ exports/                 # created when saving recordings/presets
├─ dsl_parser.py            # legacy DSL commands (optional)
├─ main.py                  # entry point (launches Mixer UI)
├─ mixer.py                 # Tkinter UI
└─ requirements.txt
```