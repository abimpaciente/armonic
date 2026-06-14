"""Pruebas del prototipo de armonización."""

from music21 import key, meter, note, stream

from armonic.harmony import (
    MelodyEvent,
    VOICE_RANGES,
    choose_chords,
    harmonize,
    realize_voices,
)


def _melody(names, ql=1):
    s = stream.Score()
    p = stream.Part()
    p.insert(0, meter.TimeSignature("4/4"))
    for n in names:
        p.append(note.Note(n, quarterLength=ql))
    s.insert(0, p)
    return s


def test_harmonize_produces_four_parts():
    s = _melody(["C4", "D4", "E4", "F4", "G4", "C5"])
    result = harmonize(s)
    assert len(result.parts) == 4
    # Misma cantidad de notas en cada voz que en la melodía.
    counts = {p.id: len(p.flatten().notes) for p in result.parts}
    assert all(c == 6 for c in counts.values()), counts


def test_voices_within_ranges_and_no_crossing():
    s = _melody(["C4", "E4", "G4", "E4", "C4"])
    result = harmonize(s)
    parts = {p.id: list(p.flatten().notes) for p in result.parts}
    for i in range(len(parts["soprano"])):
        sop = parts["soprano"][i].pitch.midi
        alt = parts["alto"][i].pitch.midi
        ten = parts["tenor"][i].pitch.midi
        bas = parts["bass"][i].pitch.midi
        # Orden de voces (sin cruces): bajo <= tenor <= alto <= soprano
        assert bas <= ten <= alt <= sop, (bas, ten, alt, sop)
        # Rangos
        assert VOICE_RANGES["bass"][0] <= bas <= VOICE_RANGES["bass"][1]
        assert VOICE_RANGES["alto"][0] <= alt <= VOICE_RANGES["alto"][1]


def test_chord_contains_melody_note():
    events = [
        MelodyEvent(60, 0, 1.0, 0.0),   # C
        MelodyEvent(62, 2, 1.0, 1.0),   # D
        MelodyEvent(64, 4, 1.0, 2.0),   # E
    ]
    k = key.Key("C")
    chords = choose_chords(events, k)
    for ev, ch in zip(events, chords):
        assert ch is not None
        assert ev.pitch_class in ch.pitch_classes


def test_cadence_prefers_tonic_on_last_note():
    # Melodía que termina en la tónica (Do) debe cerrar en I.
    s = _melody(["G4", "F4", "E4", "D4", "C4"])
    result = harmonize(s)
    bass = list(result.parts[3].flatten().notes)
    last_roman = bass[-1].lyric
    assert last_roman in ("I", "i"), last_roman


def test_rests_are_preserved():
    s = stream.Score()
    p = stream.Part()
    p.insert(0, meter.TimeSignature("4/4"))
    p.append(note.Note("C4", quarterLength=1))
    p.append(note.Rest(quarterLength=1))
    p.append(note.Note("E4", quarterLength=1))
    s.insert(0, p)
    result = harmonize(s)
    # Cada voz debe tener exactamente un silencio.
    for part in result.parts:
        rests = part.flatten().getElementsByClass("Rest")
        assert len(rests) == 1


def test_empty_melody_raises():
    s = stream.Score()
    p = stream.Part()
    p.append(note.Rest(quarterLength=4))
    s.insert(0, p)
    try:
        harmonize(s)
    except ValueError:
        return
    raise AssertionError("Se esperaba ValueError con melodía vacía")
