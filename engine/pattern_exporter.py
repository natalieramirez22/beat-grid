# engine/pattern_exporter.py
"""
Preset (JSON) save/load helpers.

Format:
{
  "name": "my_groove",
  "bpm": 128,
  "steps": 16,
  "instruments": {
    "kick": "X---X---X---X---",
    "snare": "----X-------X---",
    "hihat": "-X-X-X-X-X-X-X-X",
    "bass":  "--X-----X--X----",
    "clap":  "----X-------X---"
  }
}
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any


def save_preset(track, steps: int, file_path: str, name: str | None = None) -> str:
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    patterns = track.get_patterns().copy()
    data: Dict[str, Any] = {
        "name": name or os.path.splitext(os.path.basename(file_path))[0],
        "bpm": int(track.get_bpm()),
        "steps": int(steps),
        "instruments": patterns,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return file_path


def load_preset(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Basic validation/defaults
    bpm = int(data.get("bpm", 120))
    steps = int(data.get("steps", 16))
    instruments = data.get("instruments", {}) or {}

    # Coerce instrument values to strings
    instruments = {k: str(v) for k, v in instruments.items()}

    return {
        "name": data.get("name") or os.path.splitext(os.path.basename(file_path))[0],
        "bpm": bpm,
        "steps": steps,
        "instruments": instruments,
    }
