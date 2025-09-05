import tkinter as tk
from tkinter import ttk, messagebox

from engine.audio_exporter import export_to_wav


class MixerUI:
    def __init__(self, sequencer):
        self.sequencer = sequencer
        self.track = sequencer.track

        self.root = tk.Tk()
        self.root.title("CLI Music Mixer")
        self.root.configure(bg="#1e1e1e")

        self.instruments = ["kick", "bass", "clap", "snare", "hihat"]
        self.steps = 16
        self.pads = {instr: [] for instr in self.instruments}
        self.current_playhead = None

        self.sequencer.playhead_callback = self.highlight_playhead

        # ===== BUTTON STYLE FIX =====
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Dark.TButton",
            background="#333333",
            foreground="white",
            font=("Helvetica", 10, "bold"),
            padding=5,
            relief="flat",
        )
        style.map(
            "Dark.TButton",
            background=[("active", "#555555")],
            foreground=[("active", "white")],
        )

        # ===== PADS SECTION =====
        pad_frame = tk.Frame(self.root, bg="#1e1e1e")
        pad_frame.pack(pady=10)

        for row, instr in enumerate(self.instruments):
            tk.Label(
                pad_frame, text=instr.upper(), fg="white", bg="#1e1e1e"
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")

            for col in range(self.steps):
                pad = tk.Canvas(
                    pad_frame,
                    width=20,
                    height=20,
                    bg="#2b2b2b",
                    highlightthickness=2,
                    highlightbackground="#555",
                )
                pad.grid(row=row, column=col + 1, padx=1, pady=1)
                pad.bind("<Button-1>", lambda e, i=instr, c=col: self.toggle_pad(i, c))
                self.pads[instr].append(pad)

            clear_btn = ttk.Button(
                pad_frame, text="Clear", style="Dark.TButton", command=lambda i=instr: self.clear_pattern(i)
            )
            clear_btn.grid(row=row, column=self.steps + 1, padx=5)

        # ===== CONTROL BUTTONS =====
        control_frame = tk.Frame(self.root, bg="#1e1e1e")
        control_frame.pack(pady=10)

        ttk.Button(
            control_frame, text="Start", style="Dark.TButton", command=self.sequencer.start
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            control_frame, text="Stop", style="Dark.TButton", command=self.stop_all
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            control_frame, text="Export WAV", style="Dark.TButton", command=self.export_wav
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            control_frame, text="Exit", style="Dark.TButton", command=self.exit_app
        ).grid(row=0, column=3, padx=5)

        # ===== SLIDERS =====
        slider_frame = tk.Frame(self.root, bg="#1e1e1e")
        slider_frame.pack(pady=20)

        self.add_slider_group(
            slider_frame,
            "Kick",
            self.sequencer.kick_synth,
            [
                ("Volume", "volume", 0, 5, 0.1),
                ("Decay", "decay", 0.05, 1.0, 0.01),
            ],
        )

        self.add_slider_group(
            slider_frame,
            "Bass",
            self.sequencer.bass_synth,
            [
                ("Volume", "volume", 0, 5, 0.1),
                ("Freq", "freq", 30, 120, 1),
                ("Decay", "decay", 0.05, 1.0, 0.01),
            ],
            wave_control=True,
        )

    def add_slider_group(self, parent, name, synth, params, wave_control=False):
        group_frame = tk.LabelFrame(
            parent, text=f"{name} Controls", fg="white", bg="#1e1e1e", labelanchor="n", highlightbackground="#555"
        )
        group_frame.pack(side="top", pady=10)

        for label, param, minv, maxv, step in params:
            tk.Label(group_frame, text=f"{label}", fg="white", bg="#1e1e1e").pack()
            slider = tk.Scale(
                group_frame,
                from_=minv,
                to=maxv,
                resolution=step,
                orient="horizontal",
                length=200,
                bg="#1e1e1e",
                fg="white",
                troughcolor="#333333",
                highlightthickness=0,
                command=lambda v, p=param: synth.update(p, float(v)),
            )
            try:
                val = getattr(synth, param)
                slider.set(val.value if hasattr(val, "value") else val)
            except Exception:
                pass
            slider.pack()

        if wave_control:
            tk.Label(group_frame, text="Wave", fg="white", bg="#1e1e1e").pack()
            bass_wave = ttk.Combobox(group_frame, values=["saw", "square", "sine"])
            try:
                bass_wave.set(synth.wave)
            except Exception:
                bass_wave.set("saw")
            bass_wave.bind("<<ComboboxSelected>>", lambda e: synth.update("wave", bass_wave.get()))
            bass_wave.pack()

    def toggle_pad(self, instr, col):
        pattern = list(self.track.get_patterns().get(instr, "-" * self.steps))
        pattern[col] = "X" if pattern[col] == "-" else "-"
        self.track.add_pattern(instr, "".join(pattern))
        self.update_pad_colors(instr)

    def update_pad_colors(self, instr):
        pattern = self.track.get_patterns().get(instr, "-" * self.steps)
        for col, pad in enumerate(self.pads[instr]):
            if pad.winfo_exists():
                # show playhead with a thicker, brighter border
                is_on = (pattern[col] == "X")
                pad.configure(bg="#ff7f50" if is_on else "#2b2b2b")
                if self.current_playhead == col:
                    pad.configure(highlightbackground="#ffdd77", highlightthickness=3)
                else:
                    pad.configure(highlightbackground="#555", highlightthickness=2)

    def clear_pattern(self, instr):
        self.track.add_pattern(instr, "-" * self.steps)
        self.update_pad_colors(instr)

    def highlight_playhead(self, step):
        self.current_playhead = step
        for instr in self.instruments:
            self.update_pad_colors(instr)

    def stop_all(self):
        # Don’t zero volumes permanently; just stop the loop
        self.sequencer.stop()

    def export_wav(self):
        try:
            export_to_wav(self.track, filename="output.wav")
            messagebox.showinfo("Export", "WAV exported to exports/output.wav")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def exit_app(self):
        try:
            self.stop_all()
            self.sequencer.shutdown()
        finally:
            self.root.quit()
            self.root.destroy()

    def start(self):
        self.root.mainloop()
