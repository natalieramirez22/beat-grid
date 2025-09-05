# engine/synths.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Deque, Any, cast
from collections import deque

from pyo import (
    Adsr,
    Linseg,
    Osc,
    SfPlayer,
    Sig,
    SigTo,
    Sine,
    SquareTable,
    SuperSaw,
)

# NOTE for static type checkers:
# pyo is a realtime audio DSP lib with dynamic, signal-rate objects (Sig, SigTo, Linseg, Adsr, etc.).
# The type stubs are conservative (often "int" or "float"), so we cast to `Any` where we pass
# signal-rate objects. This silences Pylance without changing runtime behavior.

# Project root: .../engine/synths.py -> parent -> parent
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

def _asset(file_name: str) -> str:
    """Return absolute path to a file inside ./assets."""
    return str((ASSETS_DIR / file_name).resolve())


class BassSynth:
    def __init__(self, server, freq: float = 60, wave: str = "saw", decay: float = 0.2, volume: float = 1.0):
        self.server = server
        self.wave = wave
        self.decay = float(decay)
        self.freq = SigTo(value=float(freq), time=0.05)
        self.volume = Sig(float(volume))

        # Predeclare for linters
        self.osc: Any = None
        self.env: Optional[Adsr] = None
        self.output: Any = None

        self._build_synth()

    def _build_synth(self):
        # Stop previous output if rebuilding
        try:
            if self.output is not None:
                self.output.stop()
        except Exception:
            pass

        if self.wave == "saw":
            self.osc = SuperSaw(
                freq=cast(Any, self.freq),
                mul=cast(Any, self.volume) * 2,
            )
        elif self.wave == "square":
            self.osc = Osc(
                SquareTable(),
                freq=cast(Any, self.freq),
                mul=cast(Any, self.volume) * 2,
            )
        else:  # sine (+ small harmonic for presence)
            base = Sine(freq=cast(Any, self.freq), mul=cast(Any, self.volume) * 2)
            harmonic = Sine(freq=cast(Any, self.freq) * 2, mul=cast(Any, self.volume) * 0.5)
            self.osc = base + harmonic

        self.env = Adsr(
            attack=0.01,
            decay=self.decay,
            sustain=0.3,
            release=0.05,
            dur=cast(Any, 0.5),  # seconds
            mul=1.0,   # type: ignore[arg-type]  (pyo's Adsr mul/dur accept floats)
        )
        self.output = self.osc * self.env
        self.output.out()

    def update(self, param: str, value):
        if param == "freq":
            self.freq.value = float(value)
        elif param == "wave":
            self.wave = str(value)
            self._build_synth()
        elif param == "decay":
            self.decay = float(value)
            if self.env:
                self.env.decay = self.decay
        elif param == "volume":
            self.volume.value = float(value)
        else:
            print(f"Unknown parameter: {param}")

    def play(self):
        if self.env:
            self.env.play()

    def stop(self):
        if self.env:
            self.env.stop()


class KickSynth:
    def __init__(self, server, base_freq: float = 50, decay: float = 0.3, volume: float = 1.5):
        self.server = server
        self.base_freq = float(base_freq)
        self.decay = float(decay)
        self.volume = Sig(float(volume))

        self.pitch_env = Linseg([(0, self.base_freq * 2), (self.decay, self.base_freq)])
        self.env = Adsr(attack=0.001, decay=self.decay, sustain=0, release=0.05, mul=cast(Any, self.volume))
        self.osc = Sine(freq=cast(Any, self.pitch_env), mul=cast(Any, self.env))
        self.output = self.osc
        self.output.out()

    def update(self, param: str, value):
        if param == "base_freq":
            self.base_freq = float(value)
            self.pitch_env.list = [(0, self.base_freq * 2), (self.decay, self.base_freq)]
        elif param == "decay":
            self.decay = float(value)
            self.pitch_env.list = [(0, self.base_freq * 2), (self.decay, self.base_freq)]
            self.env.decay = self.decay
        elif param == "volume":
            self.volume.value = float(value)
        else:
            print(f"Unknown parameter: {param}")

    def play(self):
        self.pitch_env.play()
        self.env.play()

    def stop(self):
        self.env.stop()


# ---------- One-shot sample player base (keeps refs so sounds don't get GC'd) ----------

class _OneShotSample:
    def __init__(self, server, filename: str, volume: float = 1.0):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = _asset(filename)
        if not os.path.exists(self.file_path):
            print(f"[warning] Sample not found: {self.file_path}")
        # Keep recent players so they aren't garbage-collected mid-play
        self._players: Deque[Any] = deque(maxlen=64)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)
        # Optional: add "speed" support if you want to expose it later
        # elif param == "speed":
        #     self._speed = float(value)

    def play(self):
        # Create a fresh player per hit so transients are clean.
        p = SfPlayer(self.file_path, speed=1, loop=False, mul=cast(Any, self.volume)).out()
        self._players.append(p)  # keep a reference until the deque rolls over

    def stop(self):
        # One-shots finish on their own; nothing persistent to stop.
        pass


class HatSynth(_OneShotSample):
    def __init__(self, server, volume: float = 1.0):
        super().__init__(server, "hihat.wav", volume)


class ClapSynth(_OneShotSample):
    def __init__(self, server, volume: float = 1.0):
        super().__init__(server, "clap.wav", volume)


class SnareSynth(_OneShotSample):
    def __init__(self, server, volume: float = 1.0):
        super().__init__(server, "snare.wav", volume)
