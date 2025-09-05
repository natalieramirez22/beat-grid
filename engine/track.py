# engine/track.py

class Track:
    def __init__(self, bpm=120, steps=16):
        self.bpm = bpm
        self.steps = steps
        self.patterns = {}

    def set_bpm(self, bpm):
        self.bpm = bpm

    def get_bpm(self):
        return self.bpm

    def set_steps(self, steps: int):
        steps = max(1, int(steps))
        self.steps = steps
        # Normalize existing patterns to this length
        for inst, pat in list(self.patterns.items()):
            self.patterns[inst] = pat[:steps].ljust(steps, "-")

    def get_steps(self):
        return self.steps

    def add_pattern(self, instrument, pattern):
        # Clamp/pad to current steps length
        pat = str(pattern)[:self.steps].ljust(self.steps, "-")
        self.patterns[instrument] = pat

    def get_patterns(self):
        return self.patterns
