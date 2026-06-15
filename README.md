# armonic

Prototipo de **armonización automática a 4 voces** (SATB) a partir de una
melodía en MusicXML, construido con [music21](https://web.mit.edu/music21/).

Este es el **núcleo de armonía** del proyecto (sin OMR ni frontend todavía).
Cubre dos casos de uso:

- **Caso A — Separar voces** (`armonic.voices`): una partitura que ya viene a
  4 voces en *partitura cerrada* (2 pentagramas con Soprano+Alto y Tenor+Bajo,
  como en muchos himnarios) se separa en las 4 voces individuales y genera
  pistas de ensayo por voz ("dame mi voz de contralto para practicar").
- **Caso B — Generar armonía** (`armonic.harmony`): dada solo una melodía,
  genera un coral a 4 voces aplicando reglas básicas de armonía tonal y
  conducción de voces.

## Qué hace

1. **Análisis de tonalidad** de la melodía de entrada.
2. **Selección de acordes** diatónicos por nota mediante Viterbi, usando una
   tabla de preferencias de progresión funcional (p. ej. `ii→V`, `V→I`) y
   prefiriendo cerrar en la tónica (cadencia).
3. **Realización a 4 voces** (soprano = melodía; bajo, tenor y alto generados)
   con un segundo Viterbi que minimiza el movimiento de voces, evita cruces y
   quintas/octavas paralelas, y prefiere duplicar la fundamental.

El resultado se escribe como MusicXML, que puedes abrir en MuseScore, Finale,
Sibelius o renderizar en web con VexFlow/OpenSheetMusicDisplay.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

Genera una melodía de ejemplo ("Twinkle, Twinkle Little Star") y armonízala:

```bash
python examples/make_sample.py                 # crea examples/twinkle.musicxml
python -m armonic.cli examples/twinkle.musicxml -o armonizado.musicxml
```

O desde Python:

```python
from music21 import converter
from armonic import harmonize

score = converter.parse("mi_melodia.musicxml")
coral = harmonize(score)
coral.write("musicxml", fp="coral.musicxml")
# coral.show()  # abre en tu editor de partituras
```

### Ejemplo de salida (Twinkle, en Do mayor)

```
 #      S     A     T     B   cifrado
 0     C4    G3    E3    C3   I
 1     C4    A3    F3    F2   IV
 2     G4    B3    D3    G2   V
 3     G4    C4    E3    G2   I
 ...
13     C4    C4    E3    G2   I    (cadencia V–I)
```

## Separación de voces (Caso A)

Si tienes una partitura coral cerrada (MIDI o MusicXML exportado de MuseScore,
con 2 pentagramas), sepárala en 4 voces y genera pistas de ensayo:

```bash
python examples/separate_voices.py himno.mid practice/
```

Esto escribe en `practice/`:

- `soprano_solo.mid`, `alto_solo.mid`, `tenor_solo.mid`, `bass_solo.mid`
  — cada voz aislada.
- `<voz>_realce.mid` — esa voz fuerte y las demás de fondo (aprender tu parte
  con contexto).
- `satb_completo.mid` — las cuatro voces equilibradas.

Desde Python:

```python
from music21 import converter
from armonic.voices import split_satb, write_practice_tracks

score = converter.parse("himno.mid")
satb = split_satb(score)            # 4 partes: soprano, alto, tenor, bass
write_practice_tracks(satb, "practice/")
```

## Pruebas

```bash
python -m pytest -q
```

## Estructura

```
armonic/
  __init__.py        # API pública: harmonize(), harmonize_file()
  harmony.py         # Caso B: análisis, elección de acordes y voces
  voices.py          # Caso A: separar partitura cerrada + pistas de ensayo
  cli.py             # interfaz de línea de comandos
examples/
  make_sample.py     # genera un MusicXML de melodía de ejemplo
  separate_voices.py # separa una partitura cerrada en pistas por voz
tests/
  test_harmony.py
```

## Alcance y limitaciones (MVP)

- Trabaja **nota a nota**: cada nota de la melodía recibe un acorde. Buen punto
  de partida; una futura versión puede armonizar por pulso/compás.
- Sólo **tríadas diatónicas**. Sin séptimas, dominantes secundarias,
  modulaciones ni notas de paso/bordadura todavía.
- Las reglas de paralelas y reparto son heurísticas, no un verificador
  contrapuntístico completo.

## Próximos pasos (roadmap)

- [ ] Armonización por pulso y tratamiento de notas extrañas (paso, bordadura).
- [ ] Séptimas y cadencias más ricas (V7, ii–V–I).
- [ ] Integración OMR (Audiveris) para entrada desde imagen de partitura.
- [ ] Renderizado web (VexFlow / OpenSheetMusicDisplay) y API backend.
