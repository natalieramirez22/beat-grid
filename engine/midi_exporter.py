# engine/midi_exporter.py

from mido import Message, MidiFile, MidiTrack, bpm2tempo

NOTE_MAP = {
    "kick": 36,
    "snare": 38,
    "hihat": 42,
    "clap": 39,
    "bass": 35 
}

def export_to_midi(track, filename="output.mid"):
    mid = MidiFile()
    midi_track = MidiTrack()
    mid.tracks.append(midi_track)

    tempo = bpm2tempo(track.get_bpm())
    mid.tracks[0].append(Message('program_change', program=0, time=0))

    ticks_per_beat = mid.ticks_per_beat
    sixteenth = ticks_per_beat // 4

    for instr, pattern in track.get_patterns().items():
        note = NOTE_MAP.get(instr)
        if note is None:
            continue

        for i, c in enumerate(pattern):
            if c.upper() == "X":
                midi_track.append(Message('note_on', note=note, velocity=100, time=i * sixteenth))
                midi_track.append(Message('note_off', note=note, velocity=64, time=(i + 1) * sixteenth))

    mid.save(filename)
    print(f"MIDI saved as {filename}")
