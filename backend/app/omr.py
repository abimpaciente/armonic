"""Wrapper del motor OMR (Audiveris) para convertir imágenes en MusicXML."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from .config import settings

try:  # Pillow es opcional; sin él, no se reescala (puede fallar el OMR de fotos chicas)
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


class OMRError(RuntimeError):
    """El reconocimiento de la partitura falló."""


# Audiveris necesita ~16-20 px de "interline" (espacio entre líneas del
# pentagrama). Una foto de himno bien escaneada ronda los 2200+ px de lado
# largo; por debajo de esto, el OMR aborta ("interline too low").
_TARGET_LONG_SIDE = 2400
_MAX_SCALE = 4.0


def _prepare_image(image_path: Path, out_dir: Path) -> Path:
    """Agranda la imagen si es de baja resolución, para que Audiveris la lea.

    Devuelve la ruta a usar (la original si ya es suficientemente grande, o
    una copia reescalada). Si Pillow no está, devuelve la original.
    """
    if Image is None:
        return image_path
    try:
        img = Image.open(image_path)
        long_side = max(img.size)
    except Exception:  # noqa: BLE001 - si no se puede abrir, que lo intente Audiveris
        return image_path
    if long_side >= _TARGET_LONG_SIDE:
        return image_path
    scale = min(_MAX_SCALE, _TARGET_LONG_SIDE / long_side)
    if scale <= 1.05:
        return image_path
    w, h = img.size
    big = img.convert("RGB").resize((round(w * scale), round(h * scale)),
                                    Image.LANCZOS)
    out_dir.mkdir(parents=True, exist_ok=True)
    prepared = out_dir / "omr_input.png"
    big.save(prepared)
    return prepared


def run_audiveris(image_path: Path, out_dir: Path,
                  timeout: int = 600) -> Path:
    """Ejecuta Audiveris en modo batch y devuelve la ruta del .mxl generado.

    Requiere settings.audiveris_bin y settings.tessdata_prefix configurados.
    """
    if not settings.omr_available:
        raise OMRError(
            "OMR no disponible: define AUDIVERIS_BIN con la ruta al "
            "ejecutable de Audiveris."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if settings.tessdata_prefix:
        env["TESSDATA_PREFIX"] = settings.tessdata_prefix

    # Reescala fotos de baja resolución para que Audiveris pueda transcribir.
    image_path = _prepare_image(image_path, out_dir)

    cmd = [
        settings.audiveris_bin,
        "-batch",
        "-export",
    ]
    # Idioma del OCR de texto (título/letra). Sin esto, Audiveris no reconoce
    # el título y el himno queda "sin título".
    if settings.omr_lang:
        cmd += [
            "-option",
            f"org.audiveris.omr.text.Language.defaultSpecification={settings.omr_lang}",
        ]
    cmd += [
        "-output",
        str(out_dir),
        str(image_path),
    ]
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise OMRError(f"Audiveris excedió el tiempo límite ({timeout}s).") from exc

    # Audiveris exporta <nombre>.mxl en out_dir
    mxl = _find_output(out_dir)
    if mxl is None:
        tail = (proc.stderr or proc.stdout or "")[-500:]
        raise OMRError(f"Audiveris no produjo MusicXML. Detalle:\n{tail}")
    return mxl


def _find_output(out_dir: Path) -> Optional[Path]:
    for pattern in ("*.mxl", "*.musicxml", "*.xml"):
        matches = sorted(out_dir.glob(pattern))
        if matches:
            return matches[0]
    return None
