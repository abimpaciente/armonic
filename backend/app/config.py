"""Configuración del backend, leída de variables de entorno.

Variables relevantes:
  ARMONIC_STORAGE   carpeta donde se guardan himnos y MIDIs (def: ./storage)
  AUDIVERIS_BIN     ruta al ejecutable de Audiveris (para OMR de imágenes)
  TESSDATA_PREFIX   ruta a los datos de Tesseract (requerido por Audiveris)
"""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.storage_dir = Path(
            os.environ.get("ARMONIC_STORAGE", "./storage")
        ).resolve()
        self.audiveris_bin = os.environ.get("AUDIVERIS_BIN", "")
        self.tessdata_prefix = os.environ.get("TESSDATA_PREFIX", "")
        # Idiomas para el OCR de texto de Audiveris (título, letra). Español
        # primero para los himnarios; inglés ayuda con subtítulos en inglés.
        self.omr_lang = os.environ.get("OMR_LANG", "spa+eng")
        # Extensiones aceptadas
        self.image_exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
        self.score_exts = {".xml", ".musicxml", ".mxl", ".mid", ".midi"}
        self.max_upload_mb = int(os.environ.get("ARMONIC_MAX_UPLOAD_MB", "25"))

    @property
    def omr_available(self) -> bool:
        return bool(self.audiveris_bin) and Path(self.audiveris_bin).exists()

    def ensure_dirs(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
