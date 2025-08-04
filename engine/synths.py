from pyo import *
import os

ASSETS_DIR = "assets/samples"

class BassSynth:
    def __init__(self, server, freq=60, wave="saw", decay=0.2, volume=1.0):
        self.server = server
        self.freq = SigTo(value=freq, time=0.05)  # smooth pitch changes
        self.wave = wave
        self.decay = decay
        self.volume = Sig(volume)  # Sig volume for live control
        
        self._build_synth()

    def _build_synth(self):
        if self.wave == "saw":
            self.osc = SuperSaw(freq=self.freq, mul=self.volume*2)
        elif self.wave == "square":
            self.osc = Osc(SquareTable(), freq=self.freq, mul=self.volume*2)
        else:  # sine
            base = Sine(freq=self.freq, mul=self.volume*2)
            harmonic = Sine(freq=self.freq*2, mul=self.volume)  # harmonic for audibility
            self.osc = base + harmonic
        
        self.env = Adsr(attack=0.01, decay=self.decay, sustain=0.3, 
                        release=0.05, dur=0.5, mul=1.0)
        self.output = self.osc * self.env
        self.output.out()

    def update(self, param, value):
        if param == "freq":
            self.freq.value = value
        elif param == "wave":
            self.wave = value
            self._build_synth()
        elif param == "decay":
            self.decay = value
            self.env.decay = value
        elif param == "volume":
            self.volume.value = value
        else:
            print(f"Unknown parameter: {param}")

    def play(self):
        self.env.play()

    def stop(self):
        self.env.stop()


class KickSynth:
    def __init__(self, server, base_freq=50, decay=0.3, volume=1.5):
        self.server = server
        self.base_freq = base_freq
        self.decay = decay
        self.volume = Sig(volume)  # Sig volume for live control
        
        self.pitch_env = Linseg([(0, base_freq*2), (decay, base_freq)])
        self.env = Adsr(attack=0.001, decay=decay, sustain=0, release=0.05, mul=self.volume)
        self.osc = Sine(freq=self.pitch_env, mul=self.env)
        self.output = self.osc
        self.output.out()

    def update(self, param, value):
        if param == "base_freq":
            self.base_freq = value
            self.pitch_env.list = [(0, value*2), (self.decay, value)]
        elif param == "decay":
            self.decay = value
            self.pitch_env.list = [(0, self.base_freq*2), (value, self.base_freq)]
            self.env.decay = value
        elif param == "volume":
            self.volume.value = value
        else:
            print(f"Unknown parameter: {param}")

    def play(self):
        self.pitch_env.play()
        self.env.play()

    def stop(self):
        self.env.stop()


class HatSynth:
    def __init__(self, server, volume=1.0):
        self.server = server
        self.volume = Sig(volume)
        self.file_path = os.path.join(ASSETS_DIR, "hihat.wav")
        self.player = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)

    def update(self, param, value):
        if param == "volume":
            self.volume.value = value
        elif param == "speed":
            self.player.speed = value

    def play(self):
        self.player.out()


class ClapSynth:
    def __init__(self, server, volume=1.0):
        self.server = server
        self.volume = Sig(volume)
        self.file_path = os.path.join(ASSETS_DIR, "clap.wav")
        self.player = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)

    def update(self, param, value):
        if param == "volume":
            self.volume.value = value
        elif param == "speed":
            self.player.speed = value

    def play(self):
        self.player.out()


class SnareSynth:
    def __init__(self, server, volume=1.0):
        self.server = server
        self.volume = Sig(volume)
        self.file_path = os.path.join(ASSETS_DIR, "snare.wav")
        self.player = SfPlayer(self.file_path, speed=1, loop=False, mul=self.volume)

    def update(self, param, value):
        if param == "volume":
            self.volume.value = value
        elif param == "speed":
            self.player.speed = value

    def play(self):
        self.player.out()
