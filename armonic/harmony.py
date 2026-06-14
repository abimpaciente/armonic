"""Núcleo de armonización.

Estrategia (dos pasadas de programación dinámica / Viterbi):

  Pasada 1 — Acordes
    Para cada nota de la melodía se eligen acordes diatónicos candidatos
    (los que contienen la nota de la melodía como nota del acorde). Se
    elige la secuencia que minimiza:
        coste = penalización_emisión + penalización_transición
    donde la transición usa una tabla de preferencias de progresión
    funcional (ii->V, V->I, etc.).

  Pasada 2 — Voces (SATB)
    Para cada acorde elegido se generan realizaciones a 4 voces con la
    soprano fija (= melodía). Se elige la secuencia de voicings que
    minimiza el movimiento total de voces (conducción suave), evitando
    cruces de voces y quintas/octavas paralelas, y prefiriendo duplicar
    la fundamental.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import List, Optional, Sequence, Tuple

from music21 import chord, clef, key, layout, meter, note, roman, stream

# --- Rangos de las voces (en MIDI), aproximados a tesituras corales ---
VOICE_RANGES = {
    "soprano": (60, 81),  # C4 - A5
    "alto": (53, 74),     # F3 - D5
    "tenor": (47, 69),    # B2 - A4
    "bass": (40, 62),     # E2 - D4
}

# Preferencias de progresión funcional. transition_cost[a][b] = coste de
# pasar del grado 'a' al grado 'b' (1..7). Valores bajos = más idiomático.
_PROGRESSION = {
    1: {1: 0.5, 2: 0.4, 3: 0.6, 4: 0.3, 5: 0.3, 6: 0.4, 7: 0.7},
    2: {1: 0.8, 2: 0.5, 3: 0.9, 4: 0.7, 5: 0.2, 6: 0.8, 7: 0.4},
    3: {1: 0.7, 2: 0.8, 3: 0.5, 4: 0.4, 5: 0.7, 6: 0.3, 7: 0.9},
    4: {1: 0.4, 2: 0.5, 3: 0.8, 4: 0.5, 5: 0.2, 6: 0.7, 7: 0.5},
    5: {1: 0.2, 2: 0.7, 3: 0.9, 4: 0.7, 5: 0.5, 6: 0.4, 7: 0.9},
    6: {1: 0.6, 2: 0.3, 3: 0.7, 4: 0.4, 5: 0.4, 6: 0.5, 7: 0.8},
    7: {1: 0.2, 2: 0.8, 3: 0.6, 4: 0.8, 5: 0.7, 6: 0.6, 7: 0.5},
}

# Preferencia por la "fuerza" del grado como acorde (tónica/dominante/
# subdominante son más estables que iii o vii).
_DEGREE_BIAS = {1: 0.0, 2: 0.3, 3: 0.5, 4: 0.1, 5: 0.0, 6: 0.2, 7: 0.4}


@dataclass
class MelodyEvent:
    """Una nota de la melodía con su duración y offset."""

    pitch_midi: int
    pitch_class: int
    quarter_length: float
    offset: float
    is_rest: bool = False


@dataclass
class ChordChoice:
    """Acorde diatónico elegido para un evento melódico."""

    degree: int                 # grado de la escala (1..7)
    pitch_classes: Tuple[int, int, int]  # (fundamental, tercera, quinta)
    roman: str                  # cifrado (p.ej. 'I', 'V', 'vi')


def _melody_events(part: stream.Part) -> List[MelodyEvent]:
    """Extrae los eventos melódicos (notas y silencios) en orden."""
    events: List[MelodyEvent] = []
    for el in part.flatten().notesAndRests:
        if isinstance(el, note.Rest):
            events.append(
                MelodyEvent(0, -1, float(el.quarterLength), float(el.offset), True)
            )
            continue
        n = el
        if isinstance(el, chord.Chord):
            n = max(el.notes, key=lambda x: x.pitch.midi)  # voz superior
        events.append(
            MelodyEvent(
                pitch_midi=n.pitch.midi,
                pitch_class=n.pitch.pitchClass,
                quarter_length=float(el.quarterLength),
                offset=float(el.offset),
            )
        )
    return events


def _diatonic_triads(k: key.Key) -> List[ChordChoice]:
    """Tríadas diatónicas de la tonalidad, una por grado."""
    triads: List[ChordChoice] = []
    for degree in range(1, 8):
        root = k.pitchFromDegree(degree)
        third = k.pitchFromDegree(((degree - 1 + 2) % 7) + 1)
        fifth = k.pitchFromDegree(((degree - 1 + 4) % 7) + 1)
        rn = roman.romanNumeralFromChord(
            chord.Chord([root, third, fifth]), k
        ).romanNumeralAlone
        triads.append(
            ChordChoice(
                degree=degree,
                pitch_classes=(
                    root.pitchClass,
                    third.pitchClass,
                    fifth.pitchClass,
                ),
                roman=rn,
            )
        )
    return triads


def _emission_cost(event: MelodyEvent, ch: ChordChoice, is_last: bool) -> Optional[float]:
    """Coste de armonizar 'event' con el acorde 'ch'.

    Devuelve None si la nota de la melodía no pertenece al acorde (candidato
    descartado, salvo que no haya alternativa)."""
    if event.pitch_class not in ch.pitch_classes:
        return None
    cost = _DEGREE_BIAS[ch.degree]
    # En la última nota se prefiere cerrar en la tónica (cadencia).
    if is_last and ch.degree != 1:
        cost += 0.6
    return cost


def choose_chords(events: Sequence[MelodyEvent], k: key.Key) -> List[Optional[ChordChoice]]:
    """Pasada 1: elige un acorde por nota con Viterbi sobre los grados."""
    triads = _diatonic_triads(k)
    sounded = [i for i, e in enumerate(events) if not e.is_rest]
    if not sounded:
        return [None] * len(events)

    # dp[i] = lista de (coste_acumulado, indice_acorde, indice_prev)
    n = len(sounded)
    dp: List[List[float]] = []
    back: List[List[int]] = []

    for step, ev_idx in enumerate(sounded):
        ev = events[ev_idx]
        is_last = step == n - 1
        costs = []
        for ti, tr in enumerate(triads):
            ec = _emission_cost(ev, tr, is_last)
            if ec is None:
                costs.append(None)
            else:
                costs.append(ec)
        # Si ningún acorde contiene la nota, permite todos con penalización.
        if all(c is None for c in costs):
            costs = [_DEGREE_BIAS[tr.degree] + 1.5 for tr in triads]

        row_cost = [float("inf")] * len(triads)
        row_back = [-1] * len(triads)
        for ti in range(len(triads)):
            if costs[ti] is None:
                continue
            if step == 0:
                row_cost[ti] = costs[ti]
            else:
                best = float("inf")
                best_prev = -1
                for pi in range(len(triads)):
                    if dp[step - 1][pi] == float("inf"):
                        continue
                    trans = _PROGRESSION[triads[pi].degree][triads[ti].degree]
                    cand = dp[step - 1][pi] + trans + costs[ti]
                    if cand < best:
                        best = cand
                        best_prev = pi
                row_cost[ti] = best
                row_back[ti] = best_prev
        dp.append(row_cost)
        back.append(row_back)

    # Backtrack
    last = min(range(len(triads)), key=lambda ti: dp[-1][ti])
    path = [last]
    for step in range(n - 1, 0, -1):
        last = back[step][last]
        path.append(last)
    path.reverse()

    result: List[Optional[ChordChoice]] = [None] * len(events)
    for step, ev_idx in enumerate(sounded):
        result[ev_idx] = triads[path[step]]
    return result


def _voicings(ch: ChordChoice, soprano_midi: int) -> List[Tuple[int, int, int]]:
    """Genera realizaciones (bajo, tenor, alto) para un acorde con la
    soprano fija. Aplica rango, sin cruces y reparto/espaciado razonable."""
    pcs = ch.pitch_classes  # (fundamental, tercera, quinta)
    root_pc = pcs[0]

    def pitches_in_range(pc: int, lo: int, hi: int) -> List[int]:
        out = []
        m = lo + ((pc - lo) % 12)
        while m <= hi:
            out.append(m)
            m += 12
        return out

    bass_opts = []
    for pc in pcs:  # permite inversiones, pero se penaliza luego
        bass_opts += [(pc, m) for m in pitches_in_range(pc, *VOICE_RANGES["bass"])]
    tenor_opts = [
        (pc, m)
        for pc in pcs
        for m in pitches_in_range(pc, *VOICE_RANGES["tenor"])
    ]
    alto_opts = [
        (pc, m)
        for pc in pcs
        for m in pitches_in_range(pc, *VOICE_RANGES["alto"])
    ]

    results: List[Tuple[int, int, int]] = []
    for (bpc, b), (tpc, t), (apc, a) in product(bass_opts, tenor_opts, alto_opts):
        # Orden y sin cruces: bajo <= tenor <= alto <= soprano
        if not (b <= t <= a <= soprano_midi):
            continue
        # Espaciado: entre voces adyacentes superiores, máx. una octava
        if a - t > 12 or soprano_midi - a > 12:
            continue
        # Las tres notas del acorde deben estar presentes (triada completa).
        present = {bpc, tpc, apc, soprano_midi % 12}
        if set(pcs) - present:
            continue
        results.append((b, t, a))
    return results


def _voicing_cost(
    prev: Optional[Tuple[int, int, int]],
    cur: Tuple[int, int, int],
    ch: ChordChoice,
    soprano_midi: int,
    prev_sop: Optional[int],
) -> float:
    """Coste de un voicing: conducción suave + doblar fundamental +
    penalizar inversiones y paralelas."""
    b, t, a = cur
    cost = 0.0
    # Doblar la fundamental es lo más estable; tercera doblada peor.
    pcs = [b % 12, t % 12, a % 12, soprano_midi % 12]
    root_pc = ch.pitch_classes[0]
    third_pc = ch.pitch_classes[1]
    if pcs.count(root_pc) < 1:
        cost += 1.0
    if pcs.count(third_pc) >= 2:
        cost += 0.8  # tercera doblada
    # Preferir posición fundamental (bajo = fundamental).
    if b % 12 != root_pc:
        cost += 0.5 if b % 12 == ch.pitch_classes[2] else 0.9

    if prev is not None:
        pb, pt, pa = prev
        # Conducción: suma de movimientos de las tres voces inferiores.
        cost += (abs(b - pb) + abs(t - pt) + abs(a - pa)) * 0.1
        # Penalizar quintas/octavas paralelas entre pares de voces.
        upper = [(pb, b), (pt, t), (pa, a)]
        if prev_sop is not None:
            upper.append((prev_sop, soprano_midi))
        for i in range(len(upper)):
            for j in range(i + 1, len(upper)):
                (p1, c1), (p2, c2) = upper[i], upper[j]
                prev_int = abs(p1 - p2) % 12
                cur_int = abs(c1 - c2) % 12
                moved = (c1 - p1 != 0) or (c2 - p2 != 0)
                if moved and prev_int == cur_int and cur_int in (0, 7):
                    cost += 2.0  # paralelas de 8ª/5ª
    return cost


def realize_voices(
    events: Sequence[MelodyEvent],
    chords: Sequence[Optional[ChordChoice]],
) -> List[Optional[Tuple[int, int, int]]]:
    """Pasada 2: elige los voicings (bajo, tenor, alto) con Viterbi."""
    sounded = [i for i, e in enumerate(events) if not e.is_rest and chords[i]]
    result: List[Optional[Tuple[int, int, int]]] = [None] * len(events)
    if not sounded:
        return result

    # Estados por paso = lista de voicings posibles.
    states: List[List[Tuple[int, int, int]]] = []
    for idx in sounded:
        opts = _voicings(chords[idx], events[idx].pitch_midi)
        if not opts:
            # Relaja: sólo orden/rango, sin exigir triada completa.
            opts = _fallback_voicings(chords[idx], events[idx].pitch_midi)
        states.append(opts)

    dp: List[List[float]] = []
    back: List[List[int]] = []
    for step, idx in enumerate(sounded):
        ev = events[idx]
        row_cost = []
        row_back = []
        for ci, cur in enumerate(states[step]):
            if step == 0:
                row_cost.append(
                    _voicing_cost(None, cur, chords[idx], ev.pitch_midi, None)
                )
                row_back.append(-1)
            else:
                prev_idx = sounded[step - 1]
                prev_sop = events[prev_idx].pitch_midi
                best, best_prev = float("inf"), -1
                for pi, prev in enumerate(states[step - 1]):
                    cand = dp[step - 1][pi] + _voicing_cost(
                        prev, cur, chords[idx], ev.pitch_midi, prev_sop
                    )
                    if cand < best:
                        best, best_prev = cand, pi
                row_cost.append(best)
                row_back.append(best_prev)
        dp.append(row_cost)
        back.append(row_back)

    last = min(range(len(states[-1])), key=lambda ci: dp[-1][ci])
    path = [last]
    for step in range(len(sounded) - 1, 0, -1):
        last = back[step][last]
        path.append(last)
    path.reverse()

    for step, idx in enumerate(sounded):
        result[idx] = states[step][path[step]]
    return result


def _fallback_voicings(ch: ChordChoice, soprano_midi: int) -> List[Tuple[int, int, int]]:
    """Voicings relajados cuando no se logra triada completa: sólo respeta
    rango y orden de voces."""
    pcs = ch.pitch_classes

    def pir(pc, lo, hi):
        out, m = [], lo + ((pc - lo) % 12)
        while m <= hi:
            out.append(m)
            m += 12
        return out

    bass = [m for pc in pcs for m in pir(pc, *VOICE_RANGES["bass"])]
    tenor = [m for pc in pcs for m in pir(pc, *VOICE_RANGES["tenor"])]
    alto = [m for pc in pcs for m in pir(pc, *VOICE_RANGES["alto"])]
    out = []
    for b, t, a in product(bass, tenor, alto):
        if b <= t <= a <= soprano_midi:
            out.append((b, t, a))
    if not out:  # último recurso: triada cerrada bajo la soprano
        root = pcs[0]
        b = max(m for m in pir(root, *VOICE_RANGES["bass"]))
        out = [(b, b + 12 if b + 12 <= soprano_midi else b, soprano_midi)]
    return out


def _build_score(
    events: Sequence[MelodyEvent],
    chords: Sequence[Optional[ChordChoice]],
    voicings: Sequence[Optional[Tuple[int, int, int]]],
    k: key.Key,
    ts: Optional[meter.TimeSignature],
) -> stream.Score:
    """Ensambla la partitura a 4 voces (SATB en dos pentagramas)."""
    score = stream.Score()
    parts = {name: stream.Part(id=name) for name in ("soprano", "alto", "tenor", "bass")}
    parts["soprano"].insert(0, clef.TrebleClef())
    parts["alto"].insert(0, clef.TrebleClef())
    parts["tenor"].insert(0, clef.BassClef())  # clave de Fa para el tenor
    parts["bass"].insert(0, clef.BassClef())

    for name in parts:
        parts[name].insert(0, key.KeySignature(k.sharps))
        if ts is not None:
            parts[name].insert(0, meter.TimeSignature(ts.ratioString))

    for ev, ch, vo in zip(events, chords, voicings):
        ql = ev.quarter_length
        if ev.is_rest or ch is None or vo is None:
            for name in parts:
                parts[name].append(note.Rest(quarterLength=ql))
            continue
        b, t, a = vo
        s_note = note.Note(ev.pitch_midi, quarterLength=ql)
        a_note = note.Note(a, quarterLength=ql)
        t_note = note.Note(t, quarterLength=ql)
        b_note = note.Note(b, quarterLength=ql)
        rn = roman.RomanNumeral(ch.roman, k)
        b_note.addLyric(ch.roman)
        parts["soprano"].append(s_note)
        parts["alto"].append(a_note)
        parts["tenor"].append(t_note)
        parts["bass"].append(b_note)

    for name in ("soprano", "alto", "tenor", "bass"):
        score.insert(0, parts[name])
    score.insert(0, layout.StaffGroup(
        [parts["soprano"], parts["alto"], parts["tenor"], parts["bass"]],
        name="SATB", symbol="bracket",
    ))
    return score


def harmonize(score_in: stream.Score) -> stream.Score:
    """Armoniza una partitura monofónica a 4 voces (SATB).

    Args:
        score_in: partitura de music21 cuya primera parte es la melodía.
    Returns:
        Una nueva partitura a 4 voces.
    """
    parts = score_in.parts
    melody_part = parts[0] if parts else score_in
    events = _melody_events(melody_part)
    if not any(not e.is_rest for e in events):
        raise ValueError("La melodía no contiene notas que armonizar.")

    k = score_in.analyze("key")
    ts = melody_part.recurse().getElementsByClass(meter.TimeSignature)
    ts = ts[0] if ts else None

    chords = choose_chords(events, k)
    voicings = realize_voices(events, chords)
    return _build_score(events, chords, voicings, k, ts)


def harmonize_file(input_path: str, output_path: str) -> stream.Score:
    """Lee un MusicXML, lo armoniza y escribe el resultado en disco."""
    from music21 import converter

    score_in = converter.parse(input_path)
    result = harmonize(score_in)
    result.write("musicxml", fp=output_path)
    return result
