"""armonic — prototipo de armonización automática a 4 voces con music21.

Toma una melodía (MusicXML) y genera un coral a 4 voces (SATB) aplicando:
  1. Análisis de tonalidad.
  2. Selección de acordes diatónicos mediante Viterbi con preferencias
     de progresión funcional.
  3. Realización a 4 voces con reglas básicas de conducción de voces.
"""

from .harmony import harmonize, harmonize_file

__all__ = ["harmonize", "harmonize_file"]
__version__ = "0.1.0"
