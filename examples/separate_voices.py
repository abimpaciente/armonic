"""Separa una partitura cerrada SATB y genera pistas de ensayo por voz.

Uso:
    python examples/separate_voices.py entrada.mid [carpeta_salida]

Toma un MIDI/MusicXML en partitura cerrada (2 pentagramas: Soprano+Alto y
Tenor+Bajo) y escribe en la carpeta de salida:
    soprano_solo.mid, soprano_realce.mid, ... y satb_completo.mid
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from music21 import converter

from armonic.voices import split_satb, write_practice_tracks


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    in_path = argv[0]
    out_dir = argv[1] if len(argv) > 1 else "practice"

    score = converter.parse(in_path)
    satb = split_satb(score)
    paths = write_practice_tracks(satb, out_dir)
    print(f"Generadas {len(paths)} pistas en '{out_dir}/':")
    for p in paths:
        print("  ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
