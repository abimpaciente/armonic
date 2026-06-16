"""Orquestación: archivo de entrada -> partitura -> voces -> pistas MIDI.

Reúne todo el núcleo `armonic`:
  - Si la entrada es una imagen, se pasa por OMR (Audiveris).
  - Si la partitura trae >=2 pentagramas -> separación SATB (Caso A).
  - Si trae 1 sola voz (melodía) -> armonización a 4 voces (Caso B).
  - En ambos casos se generan las pistas de ensayo por voz.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

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


_EXT_RE = re.compile(r"\.(mxl|musicxml|xml|midi?|jpe?g|png|tiff?|bmp)$", re.I)


def _looks_like_filename(text: str) -> bool:
    """Un título OCR válido no debería terminar en una extensión de archivo."""
    return bool(_EXT_RE.search(text.strip()))


def _read_musicxml_text(path: Path) -> Optional[str]:
    """Devuelve el XML de un MusicXML (.xml/.musicxml) o el interior de un .mxl."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".mxl":
            with zipfile.ZipFile(path) as z:
                inner = [
                    n for n in z.namelist()
                    if n.lower().endswith((".xml", ".musicxml"))
                    and not n.startswith("META-INF")
                ]
                if not inner:
                    return None
                return z.read(inner[0]).decode("utf-8", "replace")
        if suffix in (".xml", ".musicxml"):
            return path.read_text("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - si no se puede leer, no hay título OCR
        return None
    return None


def _clean_credit_text(block: str) -> str:
    """Une el texto de uno o varios ``credit-words`` de un bloque ``credit``."""
    parts = re.findall(r"<credit-words[^>]*>(.*?)</credit-words>", block, re.S)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _title_from_musicxml(path: Path) -> Optional[str]:
    """Extrae el título reconocido por el OCR desde el MusicXML.

    Prioridad: un ``credit`` marcado como ``title`` > ``work-title`` /
    ``movement-title`` > el ``credit-words`` de mayor tamaño de fuente
    (normalmente el título arriba de la partitura).
    """
    raw = _read_musicxml_text(path)
    if not raw:
        return None

    # 1. credit con <credit-type>title</credit-type>
    for block in re.findall(r"<credit\b.*?</credit>", raw, re.S):
        if re.search(r"<credit-type>\s*title\s*</credit-type>", block, re.I):
            t = _clean_credit_text(block)
            if t and not _looks_like_filename(t):
                return t

    # 2. work-title / movement-title
    for tag in ("work-title", "movement-title"):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", raw, re.S)
        if m:
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            if t and not _looks_like_filename(t):
                return t

    # 3. credit-words más grande (heurística: el título suele ir en letra mayor)
    best, best_size = None, -1.0
    for m in re.finditer(r"<credit-words([^>]*)>(.*?)</credit-words>", raw, re.S):
        attrs, text = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if not text or _looks_like_filename(text):
            continue
        fs = re.search(r'font-size="([\d.]+)"', attrs)
        size = float(fs.group(1)) if fs else 0.0
        if size > best_size:
            best, best_size = text, size
    return best


# Nombres de archivo autogenerados que NO sirven como título de himno.
_GENERIC_RE = re.compile(
    r"screenshot|captura|whats?app|chrome|photo|foto|image|imagen|img|"
    r"scan|escaneo|untitled|sin[ _-]?titulo|document|^dsc|^pxl|^20\d{2}",
    re.I,
)


def _clean_fallback(name: str) -> str:
    """Convierte un nombre de archivo en un título legible. Si parece
    autogenerado (Screenshot_2026…, IMG_1234…), usa un placeholder neutro."""
    pretty = re.sub(r"[_\-]+", " ", name).strip()
    pretty = re.sub(r"\s+", " ", pretty)
    digits = sum(c.isdigit() for c in pretty)
    if _GENERIC_RE.search(pretty) or (pretty and digits >= max(4, len(pretty) // 2)):
        return "Himno sin título"
    return pretty or "Himno sin título"


def _resolve_title(score: stream.Score, score_path: Path, fallback: str) -> str:
    """Título OCR si existe; si no, el de la metadata; si no, uno limpio."""
    ocr = _title_from_musicxml(score_path)
    if ocr:
        return ocr
    md = score.metadata
    if md is not None and md.title and not _looks_like_filename(md.title):
        return md.title
    return _clean_fallback(fallback)


def process(input_path: Path, hymn_id: str, work_dir: Path,
            title: str = "", filename: str = "") -> HymnResult:
    """Procesa un archivo subido y devuelve el resultado con rutas de MIDI.

    ``title`` es un título explícito (lo que escribe el usuario o un demo) y
    tiene prioridad sobre el OCR. ``filename`` es el nombre original, usado
    solo como último recurso para el título.
    """
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

    # Título: explícito del usuario > OCR > metadata > nombre limpio.
    resolved_title = title.strip() if title and title.strip() else \
        _resolve_title(score, score_path, fallback=filename or input_path.stem)

    return HymnResult(
        hymn_id=hymn_id,
        title=resolved_title,
        key=key,
        mode=mode,
        notes_per_voice=notes_per_voice,
        duration_seconds=_estimate_seconds(satb),
        midi_files=midi_files,
        source_ext=ext,
    )
