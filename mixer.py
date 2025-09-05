import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from engine.pattern_exporter import save_preset, load_preset


class MixerUI:
    def __init__(self, sequencer):
        self.sequencer = sequencer
        self.track = sequencer.track

        # ----- Window -----
        self.root = tk.Tk()
        self.root.title("CLI Music Mixer")
        self.root.configure(bg="#1e1e1e")

        # ----- State -----
        self.instruments = ["kick", "bass", "clap", "snare", "hihat"]
        self.steps = 16
        self.pads = {instr: [] for instr in self.instruments}
        self.current_playhead = None
        self.recording_active = False

        self.sequencer.playhead_callback = self.highlight_playhead

        # ----- Styles -----
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

        # ===== TOP: Transport & REC =====
        top = tk.Frame(self.root, bg="#1e1e1e")
        top.pack(pady=(12, 6), fill="x")

        ttk.Button(top, text="Start", style="Dark.TButton", command=self.on_start).pack(side="left", padx=5)
        ttk.Button(top, text="Stop", style="Dark.TButton", command=self.on_stop).pack(side="left", padx=5)
        ttk.Button(top, text="Exit", style="Dark.TButton", command=self.exit_app).pack(side="left", padx=5)

        self.rec_label = tk.Label(top, text="●", fg="#555", bg="#1e1e1e", font=("Helvetica", 14, "bold"))
        self.rec_label.pack(side="left", padx=(12, 0))
        tk.Label(top, text="REC", fg="#aaa", bg="#1e1e1e").pack(side="left", padx=(4, 10))

        # ===== GLOBAL CONTROLS: BPM & Steps =====
        globals_frame = tk.Frame(self.root, bg="#1e1e1e")
        globals_frame.pack(pady=(4, 10), fill="x")

        tk.Label(globals_frame, text="BPM", fg="white", bg="#1e1e1e").pack(side="left", padx=(6, 6))
        self.bpm_slider = tk.Scale(
            globals_frame,
            from_=60, to=200, resolution=1,
            orient="horizontal", length=220,
            bg="#1e1e1e", fg="white", troughcolor="#333",
            highlightthickness=0,
            command=lambda v: self.track.set_bpm(int(float(v)))
        )
        try:
            self.bpm_slider.set(self.track.get_bpm())
        except Exception:
            self.track.set_bpm(120)
            self.bpm_slider.set(120)
        self.bpm_slider.pack(side="left", padx=(0, 20))

        tk.Label(globals_frame, text="Steps", fg="white", bg="#1e1e1e").pack(side="left")
        self.length_combo = ttk.Combobox(globals_frame, values=("8", "16", "32"), width=6, state="readonly")
        self.length_combo.set(str(self.steps))
        self.length_combo.bind("<<ComboboxSelected>>", self._on_length_change)
        self.length_combo.pack(side="left", padx=6)

        # ===== GRID =====
        self.pad_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.pad_frame.pack(pady=10)
        self._build_pad_grid()

        # ===== PRESETS =====
        preset_frame = tk.Frame(self.root, bg="#1e1e1e")
        preset_frame.pack(pady=(6, 6))
        ttk.Button(preset_frame, text="Save Track (JSON)", style="Dark.TButton",
                   command=self.save_track_preset).pack(side="left", padx=5)
        ttk.Button(preset_frame, text="Load Track (JSON)", style="Dark.TButton",
                   command=self.load_track_preset).pack(side="left", padx=5)

        # ===== SYNTH CONTROLS =====
        synths_frame = tk.Frame(self.root, bg="#1e1e1e")
        synths_frame.pack(pady=(6, 14))

        # Kick controls
        self._add_slider_group(
            parent=synths_frame,
            name="Kick",
            synth=self.sequencer.kick_synth,
            params=[
                ("Volume", "volume", 0.0, 5.0, 0.1),
                ("Decay", "decay", 0.05, 1.0, 0.01),
            ],
            wave_control=False,
        )

        # Bass controls
        self._add_slider_group(
            parent=synths_frame,
            name="Bass",
            synth=self.sequencer.bass_synth,
            params=[
                ("Volume", "volume", 0.0, 5.0, 0.1),
                ("Freq", "freq", 30.0, 200.0, 1.0),
                ("Decay", "decay", 0.05, 1.0, 0.01),
            ],
            wave_control=True,  # adds a waveform combobox (saw/square/sine)
        )

    # ---------------------------------------------------------------------
    # Grid building / updates
    # ---------------------------------------------------------------------
    def _build_pad_grid(self):
        for child in self.pad_frame.winfo_children():
            child.destroy()
        self.pads = {instr: [] for instr in self.instruments}

        for row, instr in enumerate(self.instruments):
            tk.Label(self.pad_frame, text=instr.upper(), fg="white", bg="#1e1e1e").grid(
                row=row, column=0, padx=5, pady=2, sticky="w"
            )
            for col in range(self.steps):
                pad = tk.Canvas(
                    self.pad_frame,
                    width=20, height=20,
                    bg="#2b2b2b",
                    highlightthickness=1,
                    highlightbackground="#555",
                )
                pad.grid(row=row, column=col + 1, padx=1, pady=1)
                pad.bind("<Button-1>", lambda e, i=instr, c=col: self.toggle_pad(i, c))
                self.pads[instr].append(pad)

            clear_btn = ttk.Button(
                self.pad_frame, text="Clear", style="Dark.TButton",
                command=lambda i=instr: self.clear_pattern(i)
            )
            clear_btn.grid(row=row, column=self.steps + 1, padx=5)

            self.update_pad_colors(instr)

    def _normalize_pattern(self, pattern: str, steps: int) -> str:
        s = (pattern or "")
        if len(s) < steps:
            s = s + "-" * (steps - len(s))
        elif len(s) > steps:
            s = s[:steps]
        return s

    def _on_length_change(self, _evt=None):
        new_steps = int(self.length_combo.get())
        self.set_steps(new_steps)

    def set_steps(self, new_steps: int):
        for instr in self.instruments:
            cur = self.track.get_patterns().get(instr, "-" * self.steps)
            self.track.add_pattern(instr, self._normalize_pattern(cur, new_steps))
        self.steps = new_steps
        self._build_pad_grid()

    # ---------------------------------------------------------------------
    # Pattern interactions
    # ---------------------------------------------------------------------
    def toggle_pad(self, instr, col):
        pattern = list(self.track.get_patterns().get(instr, "-" * self.steps))
        pattern[col] = "X" if pattern[col] == "-" else "-"
        self.track.add_pattern(instr, "".join(pattern))
        self.update_pad_colors(instr)

    def update_pad_colors(self, instr):
        pattern = self.track.get_patterns().get(instr, "-" * self.steps)
        for col, pad in enumerate(self.pads[instr]):
            if pad.winfo_exists():
                pad.configure(bg="#ff7f50" if pattern[col] == "X" else "#2b2b2b")
                if self.current_playhead is not None and col == self.current_playhead:
                    pad.configure(highlightbackground="#ffeb3b")
                else:
                    pad.configure(highlightbackground="#555")

    def clear_pattern(self, instr):
        self.track.add_pattern(instr, "-" * self.steps)
        self.update_pad_colors(instr)

    def highlight_playhead(self, step):
        self.current_playhead = step
        for instr in self.instruments:
            self.update_pad_colors(instr)

    # ---------------------------------------------------------------------
    # Transport / Recording
    # ---------------------------------------------------------------------
    def on_start(self):
        self.track.set_bpm(int(self.bpm_slider.get()))
        self.sequencer.start()

        temp_path = self.sequencer.make_temp_record_path()
        self.sequencer.start_recording(temp_path)
        self._set_rec_indicator(True)

    def on_stop(self):
        self.sequencer.stop()
        temp_path = self.sequencer.stop_recording()
        self._set_rec_indicator(False)

        if not temp_path or not os.path.exists(temp_path):
            return

        self._prompt_save_recording(temp_path)

    def _prompt_save_recording(self, temp_path: str):
        exports_dir = os.path.join("exports")
        os.makedirs(exports_dir, exist_ok=True)
        initial = os.path.join(exports_dir, os.path.basename(temp_path).replace("recording_", ""))

        dest = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Recording",
            initialfile=os.path.basename(initial),
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
        )
        if dest:
            try:
                os.replace(temp_path, dest)
                messagebox.showinfo("Saved", f"Recording saved to:\n{dest}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")
        else:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    def _set_rec_indicator(self, on: bool):
        self.recording_active = on
        self.rec_label.configure(fg="#ff4d4d" if on else "#555")

    # ---------------------------------------------------------------------
    # Presets
    # ---------------------------------------------------------------------
    def save_track_preset(self):
        exports_dir = os.path.join("exports")
        os.makedirs(exports_dir, exist_ok=True)

        dest = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Track (JSON)",
            initialdir=exports_dir,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not dest:
            return

        name = os.path.splitext(os.path.basename(dest))[0]
        try:
            save_preset(self.track, self.steps, dest, name=name)
            messagebox.showinfo("Saved", f"Preset saved to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save preset:\n{e}")

    def load_track_preset(self):
        exports_dir = os.path.join("exports")
        os.makedirs(exports_dir, exist_ok=True)

        src = filedialog.askopenfilename(
            parent=self.root,
            title="Load Track (JSON)",
            initialdir=exports_dir,
            filetypes=[("JSON", "*.json")],
        )
        if not src:
            return

        try:
            data = load_preset(src)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load preset:\n{e}")
            return

        # Apply BPM
        self.track.set_bpm(int(data["bpm"]))
        self.bpm_slider.set(int(data["bpm"]))

        # Apply step length
        steps = int(data.get("steps", 16))
        self.length_combo.set(str(steps))
        self.set_steps(steps)

        # Apply patterns
        instruments = data.get("instruments", {})
        for instr in self.instruments:
            pat = instruments.get(instr, "-" * self.steps)
            self.track.add_pattern(instr, self._normalize_pattern(pat, self.steps))

        for instr in self.instruments:
            self.update_pad_colors(instr)

        messagebox.showinfo("Loaded", f"Preset loaded:\n{os.path.basename(src)}")

    # ---------------------------------------------------------------------
    # Synth control groups
    # ---------------------------------------------------------------------
    def _add_slider_group(self, parent, name, synth, params, wave_control=False):
        group = tk.LabelFrame(
            parent, text=f"{name} Controls", fg="white", bg="#1e1e1e",
            labelanchor="n", highlightbackground="#555"
        )
        group.pack(side="left", padx=12)

        for label, param, minv, maxv, step in params:
            tk.Label(group, text=label, fg="white", bg="#1e1e1e").pack(pady=(6, 0))
            slider = tk.Scale(
                group,
                from_=minv, to=maxv, resolution=step,
                orient="horizontal", length=200,
                bg="#1e1e1e", fg="white", troughcolor="#333",
                highlightthickness=0,
                command=lambda v, p=param, s=synth: s.update(p, float(v)),
            )
            # Initialize to current synth value if available (handles Sig/SigTo/float)
            try:
                val = getattr(synth, param)
                slider.set(val.value if hasattr(val, "value") else float(val))
            except Exception:
                pass
            slider.pack(pady=(0, 6))

        if wave_control:
            tk.Label(group, text="Wave", fg="white", bg="#1e1e1e").pack(pady=(6, 0))
            wave_box = ttk.Combobox(group, values=["saw", "square", "sine"], state="readonly", width=10)
            try:
                wave_box.set(getattr(synth, "wave", "saw"))
            except Exception:
                wave_box.set("saw")
            wave_box.bind("<<ComboboxSelected>>", lambda e, s=synth, b=wave_box: s.update("wave", b.get()))
            wave_box.pack(pady=(0, 8))

    # ---------------------------------------------------------------------
    # App lifecycle
    # ---------------------------------------------------------------------
    def exit_app(self):
        try:
            self.sequencer.stop()
            temp = self.sequencer.stop_recording()
            if temp and os.path.exists(temp):
                try:
                    os.remove(temp)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.sequencer.shutdown()
        except Exception:
            pass

        self.root.quit()
        self.root.destroy()

    def start(self):
        self.root.mainloop()
