# mixer.py
import os
import shutil
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

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
        self.rec_active = False  # UI indicator state

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

        # ===== TOP BAR: Transport + REC indicator + Save =====
        top = tk.Frame(self.root, bg="#1e1e1e")
        top.pack(pady=8, fill="x")

        ttk.Button(top, text="Start", style="Dark.TButton",
                   command=self.on_start_clicked).pack(side="left", padx=4)
        ttk.Button(top, text="Stop", style="Dark.TButton",
                   command=self.on_stop_clicked).pack(side="left", padx=4)

        # REC indicator (red dot + label)
        self.rec_canvas = tk.Canvas(top, width=18, height=18, bg="#1e1e1e", highlightthickness=0)
        self.rec_canvas.pack(side="left", padx=(12, 2))
        self.rec_dot = self.rec_canvas.create_oval(4, 4, 14, 14, fill="#550000", outline="#330000")
        tk.Label(top, text="REC", fg="#ff6666", bg="#1e1e1e", font=("Helvetica", 10, "bold")).pack(side="left", padx=(2, 12))

        # Save Track JSON
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

        # Pattern length (8/16/32)
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

        # create pads
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

    # ---------- REC indicator helpers ----------
    def _set_rec_indicator(self, active: bool):
        self.rec_active = active
        fill = "#ff3b30" if active else "#550000"
        outline = "#aa0000" if active else "#330000"
        try:
            self.rec_canvas.itemconfig(self.rec_dot, fill=fill, outline=outline)
        except Exception:
            pass

    # ---------- Transport / Recording ----------
    def on_start_clicked(self):
        # Always record between Start and Stop; indicator shows state
        try:
            temp_path = self.sequencer.make_temp_record_path()
            self.sequencer.start_recording(temp_path)
            self._set_rec_indicator(True)
        except Exception as e:
            self._set_rec_indicator(False)
            messagebox.showwarning("Recording disabled", f"Could not start recording:\n{e}")
        self.sequencer.start()

    def on_stop_clicked(self):
        self.sequencer.stop()

        # If recording, stop and prompt to save
        temp_path = None
        try:
            if getattr(self.sequencer, "recording", False):
                temp_path = self.sequencer.stop_recording()
        except Exception as e:
            messagebox.showwarning("Recording", f"Could not stop recording cleanly:\n{e}")
        finally:
            self._set_rec_indicator(False)

        if temp_path and os.path.exists(temp_path):
            default_name = time.strftime("take_%Y%m%d_%H%M%S")
            name = simpledialog.askstring("Save Recording", "File name (no extension):", initialvalue=default_name)
            if name:
                safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip() or default_name
                final_path = os.path.join("exports", f"{safe}.wav")
                os.makedirs("exports", exist_ok=True)
                try:
                    shutil.move(temp_path, final_path)
                    messagebox.showinfo("Recording saved", os.path.abspath(final_path))
                except Exception as e:
                    messagebox.showerror("Save failed", str(e))
            else:
                # Cancel: discard the temp recording silently and return to UI
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def stop_all(self):
        self.on_stop_clicked()

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
            if getattr(self.sequencer, "recording", False):
                try:
                    self.sequencer.stop_recording()
                except Exception:
                    pass
            self.sequencer.stop()
            if hasattr(self.sequencer, "shutdown"):
                try:
                    self.sequencer.shutdown()
                except Exception:
                    pass
        finally:
            self.root.quit()
            self.root.destroy()

    def start(self):
        self.root.mainloop()
