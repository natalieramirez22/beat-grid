# engine/track.py

class Track:
    def __init__(self, bpm=120):
        self.bpm = bpm
        self.patterns = {}

    def set_bpm(self, bpm):
        self.bpm = bpm

    def add_pattern(self, instrument, pattern):
        self.patterns[instrument] = pattern

    def get_patterns(self):
        return self.patterns

    def get_bpm(self):
        return self.bpm
