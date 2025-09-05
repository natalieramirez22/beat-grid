# engine/synths.py

import os
import threading
from collections import deque
from typing import Deque, Optional, Any, cast

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

# Resolve assets/samples as an absolute path (works no matter the CWD).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "assets", "samples"))


def _safe_path(*parts: str) -> str:
    path = os.path.join(*parts)
    if not os.path.exists(path):
        print(f"[WARN] Sample not found: {path}")
    return path


class BassSynth:
    def __init__(self, server, freq: float = 60, wave: str = "saw", decay: float = 0.2, volume: float = 1.0):
        self.server = server
        self.wave = wave
        self.decay = decay
        self.freq = SigTo(value=freq, time=0.05)
        self.volume = Sig(volume)

        # Predeclare to satisfy linters / make attributes explicit
        self.osc: Any = None
        self.env: Optional[Adsr] = None
        self.output: Any = None

        self._build_synth()

    def _build_synth(self):
        # Stop previous output if rebuilding
        if self.output is not None:
            try:
                self.output.stop()
            except Exception:
                pass

        if self.wave == "saw":
            # Pylance gets confused by pyo's dynamic types; cast to Any to appease it.
            self.osc = SuperSaw(freq=cast(Any, self.freq), mul=cast(Any, self.volume * 2))  # type: ignore[arg-type]
        elif self.wave == "square":
            self.osc = Osc(SquareTable(), freq=cast(Any, self.freq), mul=cast(Any, self.volume * 2))  # type: ignore[arg-type]
        else:  # sine (+ harmonic for presence)
            base = Sine(freq=cast(Any, self.freq), mul=cast(Any, self.volume * 2))  # type: ignore[arg-type]
            harmonic = Sine(freq=cast(Any, self.freq * 2), mul=cast(Any, self.volume))  # type: ignore[arg-type]
            self.osc = base + harmonic

        self.env = Adsr(attack=0.01, decay=self.decay, sustain=0.3, release=0.05, dur=0.5, mul=1.0)  # type: ignore[arg-type]
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
                self.env.decay = float(value)
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
        self.env = Adsr(attack=0.001, decay=self.decay, sustain=0, release=0.05, mul=self.volume)  # type: ignore[arg-type]
        self.osc = Sine(freq=cast(Any, self.pitch_env), mul=cast(Any, self.env))  # type: ignore[arg-type]
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


class _SampleVoiceBin:
    """
    Keeps transient sample players alive until they naturally stop playing.
    Without a reference, pyo objects can get GC'd immediately (= no sound).
    """

    def __init__(self, max_voices: int = 32, lifetime_sec: float = 2.5):
        self._voices: Deque[Any] = deque(maxlen=max_voices)
        self._lifetime = lifetime_sec
        self._lock = threading.Lock()

    def play(self, player: Any):
        with self._lock:
            self._voices.append(player)
        # Schedule cleanup to release the reference after a short time.
        t = threading.Timer(self._lifetime, self._cleanup_one, args=(player,))
        t.daemon = True
        t.start()

    def _cleanup_one(self, player: Any):
        with self._lock:
            try:
                self._voices.remove(player)
            except ValueError:
                pass


class HatSynth:
    def __init__(self, server, volume: float = 1.0):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = _safe_path(ASSETS_DIR, "hihat.wav")
        self._bin = _SampleVoiceBin(max_voices=64, lifetime_sec=2.0)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        p = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)  # type: ignore[arg-type]
        p.out()
        self._bin.play(p)

    def stop(self):
        # Stateless one-shots; nothing persistent to stop.
        pass


class ClapSynth:
    def __init__(self, server, volume: float = 1.0):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = _safe_path(ASSETS_DIR, "clap.wav")
        self._bin = _SampleVoiceBin(max_voices=64, lifetime_sec=2.0)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        p = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)  # type: ignore[arg-type]
        p.out()
        self._bin.play(p)

    def stop(self):
        pass


class SnareSynth:
    def __init__(self, server, volume: float = 1.0):
        self.server = server
        self.volume = Sig(float(volume))
        self.file_path = _safe_path(ASSETS_DIR, "snare.wav")
        self._bin = _SampleVoiceBin(max_voices=64, lifetime_sec=2.0)

    def update(self, param: str, value):
        if param == "volume":
            self.volume.value = float(value)

    def play(self):
        p = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)  # type: ignore[arg-type]
        p.out()
        self._bin.play(p)

    def stop(self):
        pass
