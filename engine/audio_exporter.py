# engine/audio_exporter.py
import os
from typing import Dict
from pydub import AudioSegment

# Resolve absolute path to assets/samples so export works from any CWD
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "assets", "samples"))

SAMPLE_PATHS: Dict[str, str] = {
    "kick": os.path.join(ASSETS_DIR, "kick.wav"),
    "snare": os.path.join(ASSETS_DIR, "snare.wav"),
    "hihat": os.path.join(ASSETS_DIR, "hihat.wav"),
    "clap": os.path.join(ASSETS_DIR, "clap.wav"),
    "bass": os.path.join(ASSETS_DIR, "bass.wav"),
}

EXPORT_DIR = "exports"

def export_to_wav(track, filename="output.wav") -> str:
    """
    Renders the current pattern grid to a .wav using the sample files.
    Returns the absolute export path.
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)

    bpm = max(1, int(track.get_bpm()))
    steps = int(track.get_steps()) if hasattr(track, "get_steps") else 16
    step_duration_ms = 60_000 / bpm / 4  # 16th note ms

    # Base silence length for exactly `steps`
    output = AudioSegment.silent(duration=int(step_duration_ms * steps))

    patterns = track.get_patterns().items()
    for instrument, pattern in patterns:
        path = SAMPLE_PATHS.get(instrument)
        if not path or not os.path.exists(path):
            # Skip unknown/missing instruments silently
            continue

        sample = AudioSegment.from_wav(path)
        # Clamp to grid length
        pat = pattern[:steps].ljust(steps, "-")

        for i, char in enumerate(pat):
            if char.upper() == "X":
                offset = int(i * step_duration_ms)
                output = output.overlay(sample, position=offset)

    export_path = os.path.join(EXPORT_DIR, filename)
    output.export(export_path, format="wav")
    abs_path = os.path.abspath(export_path)
    print(f"WAV exported to {abs_path}")
    return abs_path
