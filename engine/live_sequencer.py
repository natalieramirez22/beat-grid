# engine/live_sequencer.py
"""
Realtime step sequencer driven by a background thread.
- Uses pyo exclusively for audio (no pygame needed).
- Fixed sample rate / channels for consistent recording and playback.
- Built-in recording of the exact live output between Start and Stop.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Dict, Optional

from pyo import Server  # explicit import, no wildcard

from engine.synths import BassSynth, KickSynth, HatSynth, ClapSynth, SnareSynth


class LiveSequencer:
    def __init__(self, track):
        self.track = track
        self.running: bool = False
        self.step: int = 0
        self.bpm: int = 120
        self.loop_thread: Optional[threading.Thread] = None

        # Start pyo server with explicit settings (stable SR avoids detune/recording drift)
        # - sr=44100 (CD quality), nchnls=2 (stereo)
        # - buffersize=512 for stability (256 is snappier but higher CPU)
        # - duplex=0 (output only)
        self.server: Server = Server(sr=44100, nchnls=2, buffersize=512, duplex=0).boot()
        # Global headroom so the master bus doesn't clip when recording
        self.server.setAmp(0.8)
        self.server.start()

        # Optional UI callback for playhead highlight
        self.playhead_callback: Optional[Callable[[int], None]] = None

        # Synth instances (all audio comes from here)
        self.bass_synth = BassSynth(self.server)
        self.kick_synth = KickSynth(self.server)
        self.hihat_synth = HatSynth(self.server)
        self.clap_synth = ClapSynth(self.server)
        self.snare_synth = SnareSynth(self.server)

        # Recording state
        self.recording: bool = False
        self._record_temp_path: Optional[str] = None

        # Allow DSL / other modules to address the sequencer via the Track
        track.sequencer = self

    # ---------------------------
    # Public controls
    # ---------------------------
    def start(self):
        if self.running:
            return
        self.running = True
        self.bpm = int(self.track.get_bpm())
        self.loop_thread = threading.Thread(target=self._run_loop, name="SequencerLoop", daemon=True)
        self.loop_thread.start()
        print("[loop] started")

    def stop(self):
        self.running = False
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=1.0)
        print("[loop] stopped")

    def shutdown(self):
        """Stops loop and tears down the server cleanly."""
        try:
            self.stop()
        except Exception:
            pass
        try:
            self.server.stop()
            self.server.shutdown()
        except Exception:
            pass

    # ---------------------------
    # Recording helpers
    # ---------------------------
    def make_temp_record_path(self) -> str:
        """Exports/temporary path for a unique recording filename."""
        stamp = time.strftime("%Y%m%d_%H%M%S")
        tmp_dir = os.path.join("exports", "live_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        return os.path.join(tmp_dir, f"recording_{stamp}.wav")

    def start_recording(self, temp_path: str):
        """
        Record the server's output to the given WAV file until stop_recording.
        Use 32-bit float WAV to avoid clipping/quantization issues.
        """
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        # fileformat=1 -> WAV, sampletype=3 -> 32-bit float
        self.server.recordOptions(dur=0, filename=temp_path, fileformat=1, sampletype=3)
        self.server.recstart()
        self.recording = True
        self._record_temp_path = temp_path
        print(f"[rec] started -> {temp_path}")

    def stop_recording(self) -> Optional[str]:
        """
        Stops recording. Returns the temp file path if a recording was active.
        """
        if not self.recording:
            return None
        self.server.recstop()
        self.recording = False
        print(f"[rec] stopped -> {self._record_temp_path}")
        return self._record_temp_path

    # ---------------------------
    # Internal loop
    # ---------------------------
    def _run_loop(self):
        """
        Simple 16th-note stepper. At each step, checks the current patterns and
        triggers the appropriate synths/players.
        """
        while self.running:
            # Fetch current tempo and patterns at the top of each bar chunk
            bpm = int(self.track.get_bpm())
            beat_duration = 60.0 / bpm / 4.0  # 16th note in seconds

            patterns: Dict[str, str] = self.track.get_patterns().copy()
            # Determine number of steps from the longest pattern (fallback 16)
            steps = max((len(p) for p in patterns.values()), default=16)

            for i in range(steps):
                if not self.running:
                    break

                self.step = i
                if self.playhead_callback:
                    try:
                        self.playhead_callback(i)
                    except Exception:
                        pass

                start_time = time.time()

                # Trigger instruments that have an "X" at this step
                for name, pattern in patterns.items():
                    if i < len(pattern) and pattern[i].upper() == "X":
                        if name == "bass":
                            self.bass_synth.play()
                        elif name == "kick":
                            self.kick_synth.play()
                        elif name == "hihat":
                            self.hihat_synth.play()
                        elif name == "clap":
                            self.clap_synth.play()
                        elif name == "snare":
                            self.snare_synth.play()
                        # else: ignore unknown instruments in live mode

                # Tight timing to next 16th
                elapsed = time.time() - start_time
                wait_time = max(0.0, beat_duration - elapsed)
                time.sleep(wait_time)
