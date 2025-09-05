import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from engine.audio_exporter import export_to_wav
from engine.pattern_exporter import save_track_as_json


class MixerUI:
    def __init__(self, sequencer):
        self.sequencer = sequencer
        self.track = sequencer.track

        self.root = tk.Tk()
        self.root.title("CLI Music Mixer")
        self.root.configure(bg="#1e1e1e")

        self.instruments = ["kick", "bass", "clap", "snare", "hihat"]
        self.steps = int(getattr(self.track, "get_steps", lambda: 16)())
        self.pads = {instr: [] for instr in self.instruments}
        self.current_playhead = None

        self.sequencer.playhead_callback = self.highlight_playhead

        # ===== Styles =====
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

        # ===== TOP BAR: Transport + Export =====
        top = tk.Frame(self.root, bg="#1e1e1e")
        top.pack(pady=8, fill="x")

        ttk.Button(top, text="Start", style="Dark.TButton",
                   command=self.sequencer.start).pack(side="left", padx=4)
        ttk.Button(top, text="Stop", style="Dark.TButton",
                   command=self.stop_all).pack(side="left", padx=4)

        ttk.Button(top, text="Export Audio (WAV)", style="Dark.TButton",
                   command=self.export_audio).pack(side="left", padx=8)
        ttk.Button(top, text="Save Track (JSON)", style="Dark.TButton",
                   command=self.save_track).pack(side="left", padx=4)

        ttk.Button(top, text="Exit", style="Dark.TButton",
                   command=self.exit_app).pack(side="right", padx=4)

        # ===== CONTROLS: BPM + Pattern Length =====
        ctrl = tk.Frame(self.root, bg="#1e1e1e")
        ctrl.pack(pady=8, fill="x")

        # BPM slider
        tk.Label(ctrl, text="BPM", fg="white", bg="#1e1e1e").pack(side="left", padx=(4, 6))
        self.bpm_var = tk.IntVar(value=self.track.get_bpm())
        bpm_slider = tk.Scale(
            ctrl, from_=60, to=200, orient="horizontal", length=220,
            resolution=1, bg="#1e1e1e", fg="white", troughcolor="#333333",
            highlightthickness=0, command=lambda v: self.on_bpm_change(int(float(v)))
        )
        bpm_slider.set(self.bpm_var.get())
        bpm_slider.pack(side="left")

        # Pattern length
        tk.Label(ctrl, text="Pattern Length", fg="white", bg="#1e1e1e").pack(side="left", padx=(16, 6))
        self.length_var = tk.StringVar(value=str(self.steps))
        length_box = ttk.Combobox(ctrl, width=5, values=["8", "16", "32"], textvariable=self.length_var)
        length_box.bind("<<ComboboxSelected>>", lambda e: self.on_length_change(int(self.length_var.get())))
        length_box.pack(side="left")

        # ===== PADS =====
        self.pad_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.pad_frame.pack(pady=10)
        self.build_pad_grid()

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

    # ---------- UI Builders ----------
    def build_pad_grid(self):
        # Clear old children
        for child in self.pad_frame.winfo_children():
            child.destroy()
        self.pads = {instr: [] for instr in self.instruments}

        for row, instr in enumerate(self.instruments):
            tk.Label(
                self.pad_frame, text=instr.upper(), fg="white", bg="#1e1e1e"
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")

            for col in range(self.steps):
                pad = tk.Canvas(
                    self.pad_frame,
                    width=20, height=20,
                    bg="#2b2b2b",
                    highlightthickness=2,
                    highlightbackground="#555",
                )
                pad.grid(row=row, column=col + 1, padx=1, pady=1)
                pad.bind("<Button-1>", lambda e, i=instr, c=col: self.toggle_pad(i, c))
                self.pads[instr].append(pad)

            ttk.Button(
                self.pad_frame, text="Clear", style="Dark.TButton",
                command=lambda i=instr: self.clear_pattern(i)
            ).grid(row=row, column=self.steps + 1, padx=5)

            # Ensure colors reflect current pattern
            self.update_pad_colors(instr)

    # ---------- Controls ----------
    def on_bpm_change(self, bpm: int):
        self.bpm_var.set(bpm)
        self.track.set_bpm(bpm)

    def on_length_change(self, new_steps: int):
        self.steps = int(new_steps)
        self.track.set_steps(self.steps)  # normalizes patterns
        self.build_pad_grid()             # rebuild grid to new length

    # ---------- Sliders ----------
    def add_slider_group(self, parent, name, synth, params, wave_control=False):
        group_frame = tk.LabelFrame(
            parent, text=f"{name} Controls", fg="white", bg="#1e1e1e",
            labelanchor="n", highlightbackground="#555"
        )
        group_frame.pack(side="top", pady=10)

        for label, param, minv, maxv, step in params:
            tk.Label(group_frame, text=f"{label}", fg="white", bg="#1e1e1e").pack()
            slider = tk.Scale(
                group_frame,
                from_=minv, to=maxv, resolution=step,
                orient="horizontal", length=200,
                bg="#1e1e1e", fg="white", troughcolor="#333333",
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

    # ---------- Pads ----------
    def toggle_pad(self, instr, col):
        pattern = list(self.track.get_patterns().get(instr, "-" * self.steps))
        pattern[col] = "X" if pattern[col] == "-" else "-"
        self.track.add_pattern(instr, "".join(pattern))
        self.update_pad_colors(instr)

    def update_pad_colors(self, instr):
        pattern = self.track.get_patterns().get(instr, "-" * self.steps)
        for col, pad in enumerate(self.pads[instr]):
            if pad.winfo_exists():
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

    # ---------- Transport / Export ----------
    def stop_all(self):
        self.sequencer.stop()

    def export_audio(self):
        try:
            # Ask optional file name
            name = simpledialog.askstring("Export Audio", "File name (no extension):", initialvalue="output")
            if not name:
                return
            path = export_to_wav(self.track, filename=f"{name}.wav")
            messagebox.showinfo("Export", f"WAV exported:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def save_track(self):
        try:
            name = simpledialog.askstring("Save Track", "Track name:", initialvalue="my_track")
            if not name:
                return
            path = save_track_as_json(self.track, name=name)
            messagebox.showinfo("Saved", f"Track saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def exit_app(self):
        try:
            self.stop_all()
            self.sequencer.shutdown()
        finally:
            self.root.quit()
            self.root.destroy()

    def start(self):
        self.root.mainloop()
