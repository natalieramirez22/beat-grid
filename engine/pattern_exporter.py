# engine/pattern_exporter.py
import json
import os
from datetime import datetime

EXPORT_DIR = "exports"
PRESET_DIR = os.path.join(EXPORT_DIR, "presets")

def save_track_as_json(track, name: str) -> str:
    """
    Saves BPM, steps, and instrument patterns to exports/presets/{name}.json.
    Returns the absolute file path.
    """
    os.makedirs(PRESET_DIR, exist_ok=True)

    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "bpm": track.get_bpm(),
        "steps": getattr(track, "steps", 16),
        "instruments": track.get_patterns(),
    }
    # sanitize filename
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    if not safe:
        safe = "track"

    filename = f"{safe}.json"
    path = os.path.join(PRESET_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    abs_path = os.path.abspath(path)
    print(f"Track preset saved to {abs_path}")
    return abs_path
