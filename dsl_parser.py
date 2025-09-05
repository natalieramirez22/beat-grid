# dsl_parser.py

# Not relevant to UI, only for CLI mode

from engine.audio_exporter import export_to_wav

def parse_command(cmd, track):
    tokens = cmd.strip().split()
    if not tokens:
        return

    command = tokens[0]

    if command == "set_bpm":
        try:
            bpm = int(tokens[1])
            track.set_bpm(bpm)
            print(f"BPM set to {bpm}")
        except:
            print("invalid BPM, correct syntax: set_bpm 120")

    elif command.startswith("add_"):
        instr = command[4:]
        pattern = get_pattern_arg(tokens)
        if not pattern:
            print("no pattern provided.")
        else:
            track.add_pattern(instr, pattern)
            print(f"{instr.title().lower()} pattern set to: {pattern}")

    elif command == "export":
        format = "wav"

        for t in tokens:
            if "format=" in t:
                format = t.split("=", 1)[1]

        if format == "wav":
            export_to_wav(track)
        else:
            print(f"unsupported export format: {format}")
    
    elif command == "set_bass_synth":
        if len(tokens) < 3:
            print("Usage: set_bass_synth <param> <value>")
            return
        param = tokens[1]
        value_str = tokens[2]
        try:
            value = float(value_str) if value_str.replace('.', '', 1).isdigit() else value_str
            if not hasattr(track, "bass_synth_settings"):
                track.bass_synth_settings = {}
            track.bass_synth_settings[param] = value
            if hasattr(track, "sequencer") and hasattr(track.sequencer, "bass_synth"):
                track.sequencer.bass_synth.update(param, value)
            print(f"Bass synth {param} set to {value}")
        except Exception as e:
            print(f"Error updating bass synth: {e}")
            print("Usage: set_bass_synth <param> <value>")

    elif command == "set_kick_synth":
        if len(tokens) < 3:
            print("Usage: set_kick_synth <param> <value>")
            return
        param = tokens[1]
        value_str = tokens[2]
        try:
            value = float(value_str) if value_str.replace('.', '', 1).isdigit() else value_str
            if hasattr(track, "sequencer") and hasattr(track.sequencer, "kick_synth"):
                track.sequencer.kick_synth.update(param, value)
            print(f"Kick synth {param} set to {value}")
        except Exception as e:
            print(f"Error updating kick synth: {e}")

    elif command == "set_hihat_synth":
        if len(tokens) < 3:
            print("Usage: set_hihat_synth <param> <value>")
            return
        param, val = tokens[1], tokens[2]
        value = float(val) if val.replace('.', '', 1).isdigit() else val
        track.sequencer.hihat_synth.update(param, value)
        print(f"Hihat synth {param} set to {value}")

    elif command == "set_clap_synth":
        if len(tokens) < 3:
            print("Usage: set_clap_synth <param> <value>")
            return
        param, val = tokens[1], tokens[2]
        value = float(val) if val.replace('.', '', 1).isdigit() else val
        track.sequencer.clap_synth.update(param, value)
        print(f"Clap synth {param} set to {value}")

    elif command == "set_snare_synth":
        if len(tokens) < 3:
            print("Usage: set_snare_synth <param> <value>")
            return
        param, val = tokens[1], tokens[2]
        value = float(val) if val.replace('.', '', 1).isdigit() else val
        track.sequencer.snare_synth.update(param, value)
        print(f"Snare synth {param} set to {value}")

    else:
        print(f"unknown command: {command}")

def get_pattern_arg(tokens):
    for t in tokens:
        if "pattern=" in t:
            return t.split("=", 1)[1].strip('"')
    return None
