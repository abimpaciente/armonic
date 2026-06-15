"""Wrapper del motor OMR (Audiveris) para convertir imágenes en MusicXML."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from .config import settings


class OMRError(RuntimeError):
    """El reconocimiento de la partitura falló."""


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

    cmd = [
        settings.audiveris_bin,
        "-batch",
        "-export",
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
