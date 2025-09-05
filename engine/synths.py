# engine/synths.py
"""
Synth and sample players for the live sequencer.
- Avoids wildcard imports; silences pyo's noisy import prints.
- Adds headroom to prevent clipping in recordings.
- For sample-based parts (hat/clap/snare), keeps each SfPlayer alive
  until the sample finishes so hits are not cut off by GC.
"""

from __future__ import annotations

import contextlib
import io
import os
import threading
import wave
from typing import Optional

# ---- Silence pyo import-time prints ----
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from pyo import Adsr, Linseg, Osc, SfPlayer, Sig, SigTo, Sine, SquareTable, SuperSaw


# Resolve assets/samples relative to project root
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../engine -> project root
ASSETS_DIR = os.path.join(_BASE_DIR, "assets", "samples")


def _wav_duration_seconds(path: str, default: float = 0.5) -> float:
    """Return duration of a WAV file in seconds (fallback to default if unknown)."""
    try:
        with wave.open(path, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate() or 44100
            return max(default, frames / float(rate))
    except Exception:
        return default


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
            dur=0.5,  # type: ignore[arg-type]  # seconds
            mul=1.0,  # type: ignore[arg-type]
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


class _OneShotSample:
    """
    Helper that plays a WAV and keeps a reference alive until it finishes,
    then releases it. Prevents GC from stopping the sound prematurely.
    """
    def __init__(self, wav_path: str, volume_sig: Sig, gain: float = 0.8):
        self.path = wav_path
        self.volume_sig = volume_sig
        self.gain = float(gain)
        self._active = []  # list of live SfPlayer refs
        self._dur = _wav_duration_seconds(self.path, default=0.5)

    def trigger(self):
        if not os.path.exists(self.path):
            # Missing file: nothing to do (stay silent). You could add a fallback synth here.
            return
        p = SfPlayer(self.path, speed=1, loop=False, mul=self.volume_sig * self.gain)  # type: ignore[arg-type]
        p.out()
        self._active.append(p)
        # Schedule release slightly after the sample ends
        t = threading.Timer(self._dur + 0.1, self._release, args=(p,))
        t.daemon = True
        t.start()

    def _release(self, p):
        try:
            # not strictly necessary to stop; letting it finish is fine
            # but ensure we drop our reference so GC can clean it up
            if p in self._active:
                self._active.remove(p)
        except Exception:
            pass


class HatSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "hihat.wav")
        self.player = _OneShotSample(self.file_path, self.volume, gain=0.8)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        self.player.trigger()

    def stop(self):
        pass


class ClapSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "clap.wav")
        self.player = _OneShotSample(self.file_path, self.volume, gain=0.8)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        self.player.trigger()

    def stop(self):
        pass


class SnareSynth:
    def __init__(self, server, volume: float = 0.8):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = os.path.join(ASSETS_DIR, "snare.wav")
        self.player = _OneShotSample(self.file_path, self.volume, gain=0.8)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        self.player.trigger()

    def stop(self):
        pass
