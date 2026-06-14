"""Interfaz de línea de comandos para armonic.

Uso:
    python -m armonic.cli entrada.musicxml -o salida.musicxml
"""

from __future__ import annotations

import argparse
import sys

from .harmony import harmonize_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="armonic",
        description="Armoniza una melodía (MusicXML) a 4 voces SATB.",
    )
    parser.add_argument("input", help="Ruta al MusicXML de entrada (melodía).")
    parser.add_argument(
        "-o",
        "--output",
        default="armonizado.musicxml",
        help="Ruta del MusicXML de salida (por defecto: armonizado.musicxml).",
    )
    args = parser.parse_args(argv)

    try:
        harmonize_file(args.input, args.output)
    except Exception as exc:  # pragma: no cover - mensaje amigable en CLI
        print(f"Error al armonizar: {exc}", file=sys.stderr)
        return 1

    print(f"Coral a 4 voces escrito en: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
