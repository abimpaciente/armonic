"""Pruebas de separación SATB, timbre de coro y ajuste de tempo."""

import os
import tempfile

from music21 import chord, instrument, stream, tempo

from armonic.voices import (
    DEFAULT_TEMPO,
    VOICE_ORDER,
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


def test_retempo_changes_bpm_and_keeps_timbre():
    from music21 import converter

    satb = split_satb(_closed_score())
    out = tempfile.mkdtemp()
    write_practice_tracks(satb, out)
    src = os.path.join(out, "bass_solo.mid")
    dest = os.path.join(out, "cache", "bass_solo__60.mid")

    retempo_midi(src, 60, dest)
    s = converter.parse(dest)
    programs = {i.midiProgram for i in s.recurse().getElementsByClass(instrument.Instrument)}
    tempos = {t.number for t in s.recurse().getElementsByClass(tempo.MetronomeMark)}
    assert programs == {52}
    assert tempos == {60}
