# engine/audio_exporter.py
import os
from typing import Dict
from pydub import AudioSegment

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

def export_to_wav(track, filename="output.wav", bars: int = 4, tail_ms: int = 250) -> str:
    """
    Renders the current grid to a .wav using sample files.
    - bars: how many times to repeat the current pattern
    - tail_ms: silence appended at the end to avoid truncating last hits
    Returns absolute path to the exported file.
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)

    bpm = max(1, int(track.get_bpm()))
    steps = int(track.get_steps()) if hasattr(track, "get_steps") else 16
    step_duration_ms = 60_000 / bpm / 4  # 16th note in ms

    # Total length: steps * bars + a short tail
    total_ms = int(step_duration_ms * steps * bars) + int(tail_ms)
    output = AudioSegment.silent(duration=total_ms)

    patterns = track.get_patterns().items()
    for instrument, pattern in patterns:
        path = SAMPLE_PATHS.get(instrument)
        if not path or not os.path.exists(path):
            continue

        sample = AudioSegment.from_wav(path)
        pat = (pattern[:steps].ljust(steps, "-"))

        for bar in range(bars):
            bar_offset = int(bar * steps * step_duration_ms)
            for i, char in enumerate(pat):
                if char.upper() == "X":
                    offset = int(i * step_duration_ms) + bar_offset
                    if offset < total_ms:
                        output = output.overlay(sample, position=offset)

    export_path = os.path.join(EXPORT_DIR, filename)
    output.export(export_path, format="wav")
    abs_path = os.path.abspath(export_path)
    print(f"WAV exported to {abs_path}")
    return abs_path
