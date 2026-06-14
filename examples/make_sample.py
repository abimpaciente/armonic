"""Genera un MusicXML de ejemplo (melodía de 'Twinkle, Twinkle Little Star').

    python examples/make_sample.py
crea examples/twinkle.musicxml, una melodía monofónica en Do mayor lista
para armonizar con armonic.
"""

from music21 import metadata, meter, note, stream

# Do-Do-Sol-Sol-La-La-Sol / Fa-Fa-Mi-Mi-Re-Re-Do
NOTES = [
    ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1),
    ("A4", 1), ("A4", 1), ("G4", 2),
    ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1),
    ("D4", 1), ("D4", 1), ("C4", 2),
]


def build() -> stream.Score:
    s = stream.Score()
    s.metadata = metadata.Metadata(title="Twinkle (melodía)")
    p = stream.Part(id="melody")
    p.insert(0, meter.TimeSignature("4/4"))
    for name, ql in NOTES:
        p.append(note.Note(name, quarterLength=ql))
    s.insert(0, p)
    return s


if __name__ == "__main__":
    import os

    out = os.path.join(os.path.dirname(__file__), "twinkle.musicxml")
    build().write("musicxml", fp=out)
    print(f"Escrito: {out}")
