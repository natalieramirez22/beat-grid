# mixer.py
import tkinter as tk
from tkinter import ttk

class MixerUI:
    def __init__(self, sequencer):
        self.sequencer = sequencer
        self.track = sequencer.track
        self.current_playhead = 0
        self.playhead_callback = self.highlight_playhead
        sequencer.playhead_callback = self.playhead_callback

        self.root = tk.Tk()
        self.root.title("Music Mixer")
        self.root.configure(bg="#2E2E2E")

        # Pattern grid
        self.steps = 16
        self.instruments = ["kick", "bass", "clap", "snare", "hihat"]
        self.pattern_buttons = {instr: [] for instr in self.instruments}

        grid_frame = tk.Frame(self.root, bg="#2E2E2E")
        grid_frame.pack(pady=10)

        for row, instr in enumerate(self.instruments):
            tk.Label(grid_frame, text=instr.upper(), fg="white", bg="#2E2E2E").grid(row=row, column=0, padx=5)
            for col in range(self.steps):
                btn = tk.Button(grid_frame, width=2, height=1, bg="lightgray",
                                command=lambda i=instr, c=col: self.toggle_step(i, c))
                btn.grid(row=row, column=col+1, padx=1, pady=1)
                self.pattern_buttons[instr].append(btn)

            clear_btn = tk.Button(grid_frame, text="Clear", command=lambda i=instr: self.clear_pattern(i))
            clear_btn.grid(row=row, column=self.steps+2, padx=5)

        # Controls frame (start/stop + sliders)
        controls_frame = tk.Frame(self.root, bg="#2E2E2E")
        controls_frame.pack(pady=10)

        tk.Button(controls_frame, text="Start", command=self.sequencer.start).grid(row=0, column=0, padx=10)
        tk.Button(controls_frame, text="Stop", command=self.sequencer.stop).grid(row=0, column=1, padx=10)

        # Sliders section
        sliders_frame = tk.Frame(self.root, bg="#2E2E2E")
        sliders_frame.pack(pady=10)

        # Kick controls
        self.add_slider_group(sliders_frame, "Kick", self.sequencer.kick_synth, 
                              [("volume", 0, 5, 1.5), ("decay", 0.05, 1.0, self.sequencer.kick_synth.decay)], 0)

        # Bass controls
        self.add_slider_group(sliders_frame, "Bass", self.sequencer.bass_synth,
                              [("volume", 0, 5, 1.0), ("freq", 30, 120, 60), ("decay", 0.05, 1.0, self.sequencer.bass_synth.decay)], 1)

        # Waveform selector for bass
        tk.Label(sliders_frame, text="Bass Wave", fg="white", bg="#2E2E2E").grid(row=2, column=1, pady=2)
        bass_wave = ttk.Combobox(sliders_frame, values=["saw", "square", "sine"])
        bass_wave.set(self.sequencer.bass_synth.wave)
        bass_wave.bind("<<ComboboxSelected>>", lambda e: self.sequencer.bass_synth.update("wave", bass_wave.get()))
        bass_wave.grid(row=3, column=1, pady=2)

        # Hihat
        self.add_slider_group(sliders_frame, "Hihat", self.sequencer.hihat_synth,
                              [("volume", 0, 5, 1.0)], 2)

        # Clap
        self.add_slider_group(sliders_frame, "Clap", self.sequencer.clap_synth,
                              [("volume", 0, 5, 1.0)], 3)

        # Snare
        self.add_slider_group(sliders_frame, "Snare", self.sequencer.snare_synth,
                              [("volume", 0, 5, 1.0)], 4)

    def add_slider_group(self, parent, name, synth, sliders, col):
        """Create grouped sliders for each instrument."""
        frame = tk.Frame(parent, bg="#2E2E2E")
        frame.grid(row=0, column=col, padx=10, sticky="n")

        tk.Label(frame, text=f"{name} Controls", fg="white", bg="#2E2E2E").pack()

        for param, mn, mx, default in sliders:
            tk.Label(frame, text=f"{param.capitalize()}", fg="white", bg="#2E2E2E").pack()
            slider = tk.Scale(frame, from_=mn, to=mx, resolution=0.1 if param != "freq" else 1,
                              orient="horizontal", command=lambda v, p=param: synth.update(p, float(v)))
            try:
                val = getattr(synth, param)
                slider.set(val.value if hasattr(val, "value") else val)
            except:
                slider.set(default)
            slider.pack()

    def toggle_step(self, instr, col):
        pattern = list(self.track.get_patterns().get(instr, "-"*self.steps))
        pattern[col] = "X" if pattern[col] == "-" else "-"
        self.track.add_pattern(instr, "".join(pattern))
        self.pattern_buttons[instr][col].config(bg="green" if pattern[col] == "X" else "lightgray")

    def clear_pattern(self, instr):
        self.track.add_pattern(instr, "-"*self.steps)
        for btn in self.pattern_buttons[instr]:
            btn.config(bg="lightgray")

    def highlight_playhead(self, step):
        self.current_playhead = step
        for instr in self.instruments:
            pattern = self.track.get_patterns().get(instr, "-"*self.steps)
            for idx, btn in enumerate(self.pattern_buttons[instr]):
                if idx == step and step < len(pattern):
                    btn.config(bg="red" if pattern[idx] == "X" else "#ffcccc")
                else:
                    btn.config(bg="green" if pattern[idx] == "X" else "lightgray")

    def start(self):
        self.root.mainloop()

    def close_app(self):
        try:
            self.sequencer.stop()
            if hasattr(self.sequencer, "server"):
                self.sequencer.server.stop()
                self.sequencer.server.shutdown()
        except:
            pass
        self.root.quit()
        self.root.destroy()
