# engine/live_sequencer.py

import pygame
import time
import threading

SAMPLE_PATHS = {
    "kick": "assets/samples/kick.wav",
    "snare": "assets/samples/snare.wav",
    "hihat": "assets/samples/hihat.wav",
    "clap": "assets/samples/clap.wav",
    "bass": "assets/samples/bass.wav",
}

class LiveSequencer:
    def __init__(self, track):
        self.track = track
        self.running = False
        self.step = 0
        self.bpm = 120
        self.loop_thread = None

        pygame.mixer.init()
        self.sounds = {
            name: pygame.mixer.Sound(path)
            for name, path in SAMPLE_PATHS.items()
        }

    def start(self):
        self.running = True
        self.bpm = self.track.get_bpm()
        self.loop_thread = threading.Thread(target=self.run_loop)
        self.loop_thread.start()
        print("loop started")

    def stop(self):
        self.running = False
        if self.loop_thread:
            self.loop_thread.join()
        print("loop stopped")

    def run_loop(self):
        steps = 16

        while self.running:
            bpm = self.track.get_bpm()
            beat_duration = 60 / bpm / 4  # 16th note

            for i in range(steps):
                if not self.running:
                    break

                start_time = time.time()
                self.step = i

                for name, pattern in self.track.get_patterns().copy().items():
                    if i < len(pattern) and pattern[i].upper() == "X":
                        self.sounds[name].play()

                # Wait precisely until the next step
                elapsed = time.time() - start_time
                wait_time = max(0, beat_duration - elapsed)
                time.sleep(wait_time)


