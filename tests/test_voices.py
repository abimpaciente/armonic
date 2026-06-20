"""Pruebas de separación SATB, timbre de coro y ajuste de tempo."""

import os
import tempfile

from music21 import chord, instrument, stream, tempo

from armonic.voices import (
    CHOIR_PROGRAM,
    DEFAULT_TEMPO,
    PIANO_PROGRAM,
    VOICE_ORDER,
    restyle_midi,
    retempo_midi,
    split_satb,
    write_practice_tracks,
)


def _closed_score():
    """Partitura cerrada de 2 pentagramas (S+A arriba, T+B abajo)."""
    s = stream.Score()
    top = stream.Part()
    bottom = stream.Part()
    for soprano, alto, tenor, bass in [
        ("C5", "E4", "G3", "C3"),
        ("D5", "F4", "A3", "D3"),
        ("E5", "G4", "B3", "C3"),
    ]:
        top.append(chord.Chord([soprano, alto], quarterLength=1))
        bottom.append(chord.Chord([tenor, bass], quarterLength=1))
    s.insert(0, top)
    s.insert(0, bottom)
    return s


def test_split_satb_yields_four_voices():
    satb = split_satb(_closed_score())
    assert [p.id for p in satb.parts] == VOICE_ORDER


def test_practice_tracks_use_choir_and_default_tempo():
    from music21 import converter

    satb = split_satb(_closed_score())
    out = tempfile.mkdtemp()
    paths = write_practice_tracks(satb, out)
    assert len(paths) == 9  # 4 solos + 4 realces + mezcla

    s = converter.parse(os.path.join(out, "soprano_solo.mid"))
    programs = {i.midiProgram for i in s.recurse().getElementsByClass(instrument.Instrument)}
    tempos = {t.number for t in s.recurse().getElementsByClass(tempo.MetronomeMark)}
    assert programs == {52}  # 52 = Choir Aahs
    assert tempos == {DEFAULT_TEMPO}


def _programs_tempos(path):
    from music21 import converter

    s = converter.parse(path)
    programs = {i.midiProgram for i in s.recurse().getElementsByClass(instrument.Instrument)}
    tempos = {t.number for t in s.recurse().getElementsByClass(tempo.MetronomeMark)}
    return programs, tempos


def test_retempo_changes_bpm_and_keeps_timbre():
    satb = split_satb(_closed_score())
    out = tempfile.mkdtemp()
    write_practice_tracks(satb, out)
    dest = os.path.join(out, "cache", "bass_solo__60.mid")

    retempo_midi(os.path.join(out, "bass_solo.mid"), 60, dest)
    programs, tempos = _programs_tempos(dest)
    assert programs == {CHOIR_PROGRAM}
    assert tempos == {60}


def test_restyle_to_piano_replaces_timbre_cleanly():
    satb = split_satb(_closed_score())
    out = tempfile.mkdtemp()
    write_practice_tracks(satb, out)
    src = os.path.join(out, "soprano_realce.mid")  # varias voces

    piano = os.path.join(out, "cache", "piano.mid")
    restyle_midi(src, piano, program=PIANO_PROGRAM)
    programs, tempos = _programs_tempos(piano)
    assert programs == {PIANO_PROGRAM}  # sin coro fantasma
    assert tempos == {DEFAULT_TEMPO}

    piano60 = os.path.join(out, "cache", "piano60.mid")
    restyle_midi(src, piano60, bpm=60, program=PIANO_PROGRAM)
    programs, tempos = _programs_tempos(piano60)
    assert programs == {PIANO_PROGRAM}
    assert tempos == {60}


def test_parts_to_satb_maps_four_voices_by_pitch():
    from music21 import chord, note, stream
    from armonic.voices import VOICE_ORDER, parts_to_satb

    # 4 partes con alturas descendentes; la voz aguda trae un acorde (divisi).
    s = stream.Score()
    p0 = stream.Part(); p0.append(chord.Chord(["C5", "E5"], quarterLength=1))
    p1 = stream.Part(); p1.append(note.Note("G4", quarterLength=1))
    p2 = stream.Part(); p2.append(note.Note("C4", quarterLength=1))
    p3 = stream.Part(); p3.append(note.Note("C3", quarterLength=1))
    for p in (p2, p0, p3, p1):  # orden desordenado a propósito
        s.insert(0, p)

    satb = parts_to_satb(s)
    assert [p.id for p in satb.parts] == VOICE_ORDER
    by_id = {p.id: p for p in satb.parts}
    # soprano (top) toma la nota más aguda del acorde; ninguna parte es acorde
    assert by_id["soprano"].flatten().notes[0].pitch.nameWithOctave == "E5"
    assert all(not n.isChord for p in satb.parts for n in p.flatten().notes)
