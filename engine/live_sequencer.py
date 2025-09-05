# engine/live_sequencer.py

import time
import threading
from typing import Callable, Dict, Optional

import pygame
from pyo import Server  # explicit import

from engine.synths import BassSynth, KickSynth, HatSynth, ClapSynth, SnareSynth


SAMPLE_PATHS: Dict[str, str] = {
    "kick": "assets/samples/kick.wav",
    "snare": "assets/samples/snare.wav",
    "hihat": "assets/samples/hihat.wav",
    "clap": "assets/samples/clap.wav",
    "bass": "assets/samples/bass.wav",
}


class LiveSequencer:
    def __init__(self, track):
        self.track = track
        self._stop_event = threading.Event()
        self._loop_thread: Optional[threading.Thread] = None
        self.step = 0

        # Defer to track bpm for consistency
        self.bpm = max(1, int(self.track.get_bpm()))

        # ---- pygame init (sample fallback only) ----
        pygame.mixer.init()
        self.sounds = {
            name: pygame.mixer.Sound(path) for name, path in SAMPLE_PATHS.items()
        }

        # ---- pyo server init ----
        # Use duplex=0 to avoid mic input permissions on macOS
        self.server = Server(duplex=0).boot()
        self.server.start()

        # UI callback to paint playhead
        self.playhead_callback: Optional[Callable[[int], None]] = None

        # ---- Synths ----
        self.bass_synth = BassSynth(self.server)
        self.kick_synth = KickSynth(self.server)
        self.hihat_synth = HatSynth(self.server)
        self.clap_synth = ClapSynth(self.server)
        self.snare_synth = SnareSynth(self.server)

        # Let the track reach us if CLI or other code wants to poke synths
        track.sequencer = self

    # ---------------- public controls ----------------

    def start(self):
        """Start sequencer loop in a background thread."""
        if self._loop_thread and self._loop_thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self.bpm = max(1, int(self.track.get_bpm()))
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()
        print("loop started")

    def stop(self):
        """Stop the sequencer loop and wait briefly for it to end."""
        self._stop_event.set()
        if self._loop_thread and self._loop_thread.is_alive():
            # Don’t block Tk for too long; wait briefly
            self._loop_thread.join(timeout=0.5)
        print("loop stopped")

    def shutdown(self):
        """Full audio shutdown for app exit."""
        # Stop loop
        self.stop()

        # Stop synth envelopes
        try:
            self.bass_synth.stop()
            self.kick_synth.stop()
            self.hihat_synth.stop()
            self.clap_synth.stop()
            self.snare_synth.stop()
        except Exception:
            pass

        # Stop/close pyo
        try:
            if self.server.getIsStarted():
                self.server.stop()
            if self.server.getIsBooted():
                # shutdown releases PortAudio resources
                self.server.shutdown()
        except Exception:
            pass

        # Quit pygame mixer
        try:
            pygame.mixer.quit()
        except Exception:
            pass

        print("audio shutdown complete")

    # ---------------- internal loop ----------------

    def _run_loop(self):
        steps = 16
        while not self._stop_event.is_set():
            bpm_now = max(1, int(self.track.get_bpm()))
            step_sec = 60.0 / bpm_now / 4.0  # 16th note
            for i in range(steps):
                if self._stop_event.is_set():
                    break

                self.step = i
                if self.playhead_callback:
                    try:
                        self.playhead_callback(i)
                    except Exception:
                        # Never crash the audio loop due to UI
                        pass

                start_time = time.time()

                # Pull the latest patterns every step (so UI toggles are live)
                for name, pattern in list(self.track.get_patterns().items()):
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
                        else:
                            # Fallback to sample if defined
                            snd = self.sounds.get(name)
                            if snd:
                                snd.set_volume(0.5)
                                snd.play()

                elapsed = time.time() - start_time
                wait_time = max(0.0, step_sec - elapsed)

                # Use Event.wait so we can interrupt immediately on stop
                if self._stop_event.wait(wait_time):
                    break
