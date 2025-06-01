# dsl_parser.py

from engine.midi_exporter import export_to_midi

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
            print(f"{instr.title()} pattern set to: {pattern}")

    elif command == "export":
        export_to_midi(track)

    else:
        print(f"unknown command: {command}")

def get_pattern_arg(tokens):
    for t in tokens:
        if "pattern=" in t:
            return t.split("=", 1)[1].strip('"')
    return None
