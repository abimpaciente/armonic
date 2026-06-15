"""Separación de voces (Caso A): de partitura cerrada a 4 voces SATB.

Muchos himnarios y exportaciones de MuseScore vienen en *partitura cerrada*:
dos pentagramas con dos voces cada uno (Soprano+Alto arriba, Tenor+Bajo
abajo, escritas como acordes). Para que un coro ensaye necesitamos cada voz
por separado.

Este módulo separa esas sonoridades en cuatro voces independientes y genera
pistas de ensayo: cada voz en solo y "mezclas de realce" donde una voz suena
fuerte y las demás de fondo.
"""

from __future__ import annotations

import os
from typing import Dict, List

from music21 import (
    chord,
    clef,
    converter,
    instrument,
    note,
    stream,
    tempo,
    volume,
)

VOICE_ORDER = ["soprano", "alto", "tenor", "bass"]

# Tempo de ensayo por defecto (BPM). Más lento que el 120 del MIDI crudo para
# que un coro pueda seguir la línea. El front permite ajustarlo con un slider.
DEFAULT_TEMPO = 84

# Timbres disponibles (programas General MIDI). Las pistas se generan con voz
# coral ("aah"); el front puede pedir piano y el backend lo reescribe al vuelo.
CHOIR_PROGRAM = 52   # Choir Aahs
PIANO_PROGRAM = 0    # Acoustic Grand Piano
TIMBRES = {"voz": CHOIR_PROGRAM, "coro": CHOIR_PROGRAM, "piano": PIANO_PROGRAM}


def _split_staff(part: stream.Part, top_name: str, bottom_name: str
                 ) -> Dict[str, stream.Part]:
    """Separa un pentagrama (con 2 voces como acordes) en dos partes.

    La nota superior de cada sonoridad va a la voz aguda y la inferior a la
    grave. Si suena una sola nota (unísono), ambas voces la comparten.
    """
    top = stream.Part(id=top_name)
    bottom = stream.Part(id=bottom_name)
    chordified = part.chordify()
    for el in chordified.flatten().notesAndRests:
        ql = float(el.quarterLength)
        off = float(el.offset)
        if el.isRest:
            top.insert(off, note.Rest(quarterLength=ql))
            bottom.insert(off, note.Rest(quarterLength=ql))
            continue
        pitches = sorted(el.pitches, key=lambda p: p.midi)
        low = pitches[0]
        high = pitches[-1]
        top.insert(off, note.Note(high, quarterLength=ql))
        bottom.insert(off, note.Note(low, quarterLength=ql))
    return {top_name: top, bottom_name: bottom}


def split_satb(score: stream.Score) -> stream.Score:
    """Convierte una partitura cerrada de 2 pentagramas en 4 voces SATB.

    Args:
        score: partitura con 2 partes (pentagrama agudo = S+A, grave = T+B).
    Returns:
        Una partitura con 4 partes independientes: soprano, alto, tenor, bass.
    """
    parts = score.parts
    if len(parts) < 2:
        raise ValueError(
            "Se esperaban 2 pentagramas (agudo S/A, grave T/B); "
            f"se encontraron {len(parts)}."
        )
    voices: Dict[str, stream.Part] = {}
    voices.update(_split_staff(parts[0], "soprano", "alto"))
    voices.update(_split_staff(parts[1], "tenor", "bass"))

    out = stream.Score()
    voices["soprano"].insert(0, clef.TrebleClef())
    voices["alto"].insert(0, clef.TrebleClef())
    voices["tenor"].insert(0, clef.BassClef())
    voices["bass"].insert(0, clef.BassClef())
    for name in VOICE_ORDER:
        out.insert(0, voices[name])
    return out


def _voice_part(part: stream.Part, vel: int, bpm: int) -> stream.Part:
    """Copia de la parte con voz coral ("aah"), velocidad y tempo dados.

    El timbre de coro (GM program 52, ``instrument.Choir``) hace que la pista
    suene a voces cantando en vez del piano/MIDI seco.
    """
    p = part.flatten()
    # Evita instrumentos/tempos duplicados si la parte ya traía alguno.
    for el in list(p.getElementsByClass((instrument.Instrument,
                                         tempo.MetronomeMark))):
        p.remove(el)
    p.insert(0, instrument.Choir())
    p.insert(0, tempo.MetronomeMark(number=bpm))
    for n in p.notes:
        n.volume = volume.Volume(velocity=vel)
    return p


def write_practice_tracks(satb: stream.Score, out_dir: str,
                          highlight: int = 110, background: int = 40,
                          tempo_bpm: int = DEFAULT_TEMPO) -> List[str]:
    """Genera MIDIs de ensayo a partir de una partitura SATB.

    Para cada voz crea dos archivos:
      * ``<voz>_solo.mid``      — solo esa voz.
      * ``<voz>_realce.mid``    — esa voz fuerte y las demás de fondo,
                                  útil para aprender tu parte con contexto.

    Todas las pistas usan timbre de coro y se escriben a ``tempo_bpm``. El
    tempo se puede reajustar después por pista con :func:`retempo_midi`.

    Devuelve la lista de rutas escritas.
    """
    os.makedirs(out_dir, exist_ok=True)
    written: List[str] = []
    parts = {p.id: p for p in satb.parts}

    for target in VOICE_ORDER:
        # Solo
        solo = stream.Score()
        solo.insert(0, _voice_part(parts[target], highlight, tempo_bpm))
        solo_path = os.path.join(out_dir, f"{target}_solo.mid")
        solo.write("midi", fp=solo_path)
        written.append(solo_path)

        # Realce: voz objetivo fuerte, resto de fondo
        mix = stream.Score()
        for name in VOICE_ORDER:
            vel = highlight if name == target else background
            mix.insert(0, _voice_part(parts[name], vel, tempo_bpm))
        mix_path = os.path.join(out_dir, f"{target}_realce.mid")
        mix.write("midi", fp=mix_path)
        written.append(mix_path)

    # Mezcla completa equilibrada
    full = stream.Score()
    for name in VOICE_ORDER:
        full.insert(0, _voice_part(parts[name], 80, tempo_bpm))
    full_path = os.path.join(out_dir, "satb_completo.mid")
    full.write("midi", fp=full_path)
    written.append(full_path)
    return written


def _instrument_for(program: int) -> instrument.Instrument:
    """Instancia el instrumento adecuado para un programa General MIDI."""
    if program == CHOIR_PROGRAM:
        return instrument.Choir()
    if program == PIANO_PROGRAM:
        return instrument.Piano()
    inst = instrument.Instrument()
    inst.midiProgram = program
    return inst


def restyle_midi(src_path: str, dest_path: str,
                 bpm: int | None = None,
                 program: int | None = None) -> str:
    """Reescribe un MIDI cambiando tempo y/o timbre, conservando notas y
    velocidades. ``bpm``/``program`` en ``None`` se dejan como estaban.
    Devuelve ``dest_path``."""
    score = converter.parse(str(src_path))

    if bpm is not None:
        for mm in list(score.recurse().getElementsByClass(tempo.MetronomeMark)):
            if mm.activeSite is not None:
                mm.activeSite.remove(mm)
        target = score.parts[0] if score.parts else score
        target.insert(0, tempo.MetronomeMark(number=bpm))

    if program is not None:
        for part in (score.parts or [score]):
            # Reemplaza el instrumento por completo: mutar el midiProgram de
            # una subclase (p. ej. Choir) deja un cambio de programa fantasma.
            for inst in list(part.recurse().getElementsByClass(instrument.Instrument)):
                if inst.activeSite is not None:
                    inst.activeSite.remove(inst)
            part.insert(0, _instrument_for(program))

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    score.write("midi", fp=str(dest_path))
    return dest_path


def retempo_midi(src_path: str, bpm: int, dest_path: str) -> str:
    """Atajo de :func:`restyle_midi` que solo cambia el tempo."""
    return restyle_midi(src_path, dest_path, bpm=bpm)
