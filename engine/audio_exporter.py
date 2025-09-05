# engine/audio_exporter.py
import os
from pathlib import Path
from pydub import AudioSegment

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

SAMPLE_PATHS = {
    "kick":  ASSETS_DIR / "kick.wav",
    "snare": ASSETS_DIR / "snare.wav",
    "hihat": ASSETS_DIR / "hihat.wav",
    "clap":  ASSETS_DIR / "clap.wav",
    "bass":  ASSETS_DIR / "bass.wav",
}

EXPORT_DIR = BASE_DIR / "exports"

def export_to_wav(track, filename="output.wav"):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    bpm = track.get_bpm()
    step_duration_ms = 60_000 / bpm / 4  # 16th note duration in ms

    # infer length from longest pattern (fallback 16)
    steps = max([len(p) for p in track.get_patterns().values()] + [16])

    output = AudioSegment.silent(duration=int(step_duration_ms * steps))

    for instrument, pattern in track.get_patterns().items():
        path = SAMPLE_PATHS.get(instrument)
        if not path or not path.exists():
            continue
        try:
            sample = AudioSegment.from_wav(path)
        except Exception:
            continue

        for i, char in enumerate(pattern):
            if char.upper() == "X":
                offset = int(i * step_duration_ms)
                output = output.overlay(sample, position=offset)

    export_path = EXPORT_DIR / filename
    output.export(export_path, format="wav")
    print(f"WAV exported to {export_path}")
