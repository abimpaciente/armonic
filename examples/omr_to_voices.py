"""Pipeline OMR -> voces: de una partitura reconocida a pistas de ensayo.

Toma el MusicXML/MXL que produce un motor OMR (Audiveris u oemer) a partir de
una foto y, si trae 2 pentagramas (himno cerrado S+A / T+B), lo separa en 4
voces y genera las pistas de ensayo por voz.

    python examples/omr_to_voices.py audiveris_out/himno.mxl -o practice/

NOTA: el OMR es imperfecto (especialmente en fotos). Revisa el resultado en
MuseScore antes de usarlo en serio; este script es el "pegamento" entre el
reconocimiento y la separación de voces, no un corrector.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from music21 import converter

from armonic.voices import split_satb, write_practice_tracks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="MusicXML/MXL reconocido por el OMR.")
    parser.add_argument("-o", "--output", default="practice",
                        help="Carpeta de salida (por defecto: practice).")
    args = parser.parse_args(argv)

    score = converter.parse(args.input)
    n_parts = len(score.parts)
    if n_parts < 2:
        print(
            f"El OMR entregó {n_parts} parte(s). Para separar en SATB se "
            "necesitan 2 pentagramas (S+A / T+B). Si es una melodía sola, "
            "usa la armonización: python -m armonic.cli",
            file=sys.stderr,
        )
        return 1

    satb = split_satb(score)
    paths = write_practice_tracks(satb, args.output)
    print(f"Generadas {len(paths)} pistas en '{args.output}/':")
    for p in satb.parts:
        print(f"   {p.id:8} {len(p.flatten().notes)} notas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
