import os
from pydub import AudioSegment

SAMPLE_PATHS = {
    "kick": "assets/samples/kick.wav",
    "snare": "assets/samples/snare.wav",
    "hihat": "assets/samples/hihat.wav",
    "clap": "assets/samples/clap.wav",
    "bass": "assets/samples/bass.wav",
}

EXPORT_DIR = "exports"

def export_to_wav(track, filename="output.wav"):
    # Ensure the export directory exists
    os.makedirs(EXPORT_DIR, exist_ok=True)

    bpm = track.get_bpm()
    step_duration_ms = 60_000 / bpm / 4  # 16th note duration in ms
    steps = 16
    output = AudioSegment.silent(duration=step_duration_ms * steps)

    for instrument, pattern in track.get_patterns().items():
        if instrument not in SAMPLE_PATHS:
            continue

        sample = AudioSegment.from_wav(SAMPLE_PATHS[instrument])

        for i, char in enumerate(pattern):
            if char.upper() == "X":
                offset = int(i * step_duration_ms)
                output = output.overlay(sample, position=offset)

    export_path = os.path.join(EXPORT_DIR, filename)
    output.export(export_path, format="wav")
    print(f"WAV exported to {export_path}")
