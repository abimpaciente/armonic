"""Orquestación: archivo de entrada -> partitura -> voces -> pistas MIDI.

Reúne todo el núcleo `armonic`:
  - Si la entrada es una imagen, se pasa por OMR (Audiveris).
  - Si la partitura trae >=2 pentagramas -> separación SATB (Caso A).
  - Si trae 1 sola voz (melodía) -> armonización a 4 voces (Caso B).
  - En ambos casos se generan las pistas de ensayo por voz.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from music21 import converter, stream

from armonic.harmony import harmonize
from armonic.voices import VOICE_ORDER, split_satb, write_practice_tracks

from .config import settings
from .omr import run_audiveris


@dataclass
class HymnResult:
    hymn_id: str
    title: str
    key: str
    mode: str            # "separado" (Caso A) o "armonizado" (Caso B)
    notes_per_voice: Dict[str, int]
    duration_seconds: float
    midi_files: Dict[str, str] = field(default_factory=dict)  # nombre -> ruta
    source_ext: str = ""


def _estimate_seconds(score: stream.Score, bpm: float = 90.0) -> float:
    ql = float(score.highestTime or 0.0)
    return round(ql * 60.0 / bpm, 1)


def _title_from(score: stream.Score, fallback: str) -> str:
    md = score.metadata
    if md is not None and md.title:
        return md.title
    return fallback


def process(input_path: Path, hymn_id: str, work_dir: Path,
            title: str = "") -> HymnResult:
    """Procesa un archivo subido y devuelve el resultado con rutas de MIDI."""
    work_dir.mkdir(parents=True, exist_ok=True)
    ext = input_path.suffix.lower()

    # 1. Obtener MusicXML (vía OMR si es imagen)
    if ext in settings.image_exts:
        score_path = run_audiveris(input_path, work_dir / "omr")
    elif ext in settings.score_exts:
        score_path = input_path
    else:
        raise ValueError(f"Extensión no soportada: {ext}")

    score = converter.parse(str(score_path))

    # 2. Separar o armonizar según el número de pentagramas
    n_parts = len(score.parts)
    if n_parts >= 2:
        satb = split_satb(score)
        mode = "separado"
    else:
        satb = harmonize(score)
        mode = "armonizado"

    # 3. Metadatos
    try:
        key = str(score.analyze("key"))
    except Exception:
        key = "desconocida"
    notes_per_voice = {
        p.id: len(p.flatten().notes) for p in satb.parts
    }

    # 4. Pistas de ensayo
    tracks_dir = work_dir / "tracks"
    paths = write_practice_tracks(satb, str(tracks_dir))
    midi_files = {Path(p).stem: p for p in paths}

    return HymnResult(
        hymn_id=hymn_id,
        title=_title_from(score, fallback=title or input_path.stem),
        key=key,
        mode=mode,
        notes_per_voice=notes_per_voice,
        duration_seconds=_estimate_seconds(satb),
        midi_files=midi_files,
        source_ext=ext,
    )
