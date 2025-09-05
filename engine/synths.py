# engine/synths.py
"""
Synth and sample players for the live sequencer.
- Pylance-friendly (no wildcard imports; targeted type ignores where pyo stubs are narrow).
- Built-in headroom so the master mix doesn't clip on recordings.
- Sample-based parts (hat/clap/snare) create a fresh player per hit to avoid stuck notes.
"""

from __future__ import annotations

import os
from typing import Optional, Any, cast

from pyo import Adsr, Linseg, Osc, SfPlayer, Sig, SigTo, Sine, SquareTable, SuperSaw

# Resolve assets/samples relative to project root for robustness
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../engine -> project root
ASSETS_DIR = os.path.join(_BASE_DIR, "assets", "samples")


class BassSynth:
    def __init__(self, server, freq: float = 60, wave: str = "saw", decay: float = 0.2, volume: float = 1.0):
        self.server = server
        self.wave = wave
        self.decay = float(decay)
        self.freq = SigTo(value=float(freq), time=0.05)
        self.volume = Sig(float(volume))

        self.osc = None
        self.env: Optional[Adsr] = None
        self.output = None

        self._build_synth()

    def _build_synth(self):
        # Stop previous chain if we're rebuilding (e.g., wave change)
        if self.output is not None:
            try:
                self.output.stop()
            except Exception:
                pass

        # Lower gains for headroom in recordings
        if self.wave == "saw":
            self.osc = SuperSaw(freq=self.freq, mul=self.volume * 0.6)  # type: ignore[arg-type]
        elif self.wave == "square":
            self.osc = Osc(SquareTable(), freq=self.freq, mul=self.volume * 0.6)  # type: ignore[arg-type]
        else:  # sine with gentle harmonic to help presence on small speakers
            base = Sine(freq=self.freq, mul=self.volume * 0.6)  # type: ignore[arg-type]
            harmonic = Sine(freq=self.freq * 2, mul=self.volume * 0.3)  # type: ignore[arg-type]
            self.osc = base + harmonic  # type: ignore[assignment]

        self.env = Adsr(
            attack=0.01,
            decay=self.decay,
            sustain=0.3,
            release=0.05,
            dur=cast(Any, 0.5),
            mul=cast(Any, 1.0),
        )
        self.output = self.osc * self.env  # type: ignore[operator]
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
    def __init__(self, server, base_freq: float = 50, decay: float = 0.3, volume: float = 1.0):
        self.server = server
        self.base_freq = float(base_freq)
        self.decay = float(decay)
        self.volume = Sig(float(volume))

        self.pitch_env = Linseg([(0, self.base_freq * 2.0), (self.decay, self.base_freq)])
        self.env = Adsr(attack=0.001, decay=self.decay, sustain=0.0, release=0.05, mul=self.volume * 0.8)  # type: ignore[arg-type]
        self.osc = Sine(freq=self.pitch_env, mul=self.env)  # type: ignore[arg-type]
        self.output = self.osc
        self.output.out()

    def update(self, param: str, value):
        if param == "base_freq":
            self.base_freq = float(value)
            self.pitch_env.list = [(0, self.base_freq * 2.0), (self.decay, self.base_freq)]
        elif param == "decay":
            self.decay = float(value)
            self.pitch_env.list = [(0, self.base_freq * 2.0), (self.decay, self.base_freq)]
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


class HatSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "hihat.wav")

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        # Stateless: new player per hit for clean transients
        SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume * 0.8).out()  # type: ignore[arg-type]

    def stop(self):
        pass


class ClapSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "clap.wav")

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume * 0.8).out()  # type: ignore[arg-type]

    def stop(self):
        pass


class SnareSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "snare.wav")

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume * 0.8).out()  # type: ignore[arg-type]

    def stop(self):
        pass
