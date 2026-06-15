# OMR: de la foto a las voces

Notas de viabilidad del paso de **reconocimiento óptico de partituras** (OMR),
basadas en pruebas reales con la foto del himno *"Cantad alegres al Señor"*
(4 voces, partitura cerrada en 2 pentagramas).

## Resumen ejecutivo

- **El OMR es el cuello de botella del producto**, no la armonía.
- La **polifonía densa** (4 voces en 2 pentagramas, típico de himnario) es el
  peor caso para cualquier OMR.
- Dos motores probados sobre la **misma foto**, midiendo cuánto del soprano
  recuperaron frente a la partitura real (MIDI de MuseScore como verdad):

  | Motor      | Tipo                    | Soprano recuperado | ¿Conserva voces? |
  |------------|-------------------------|--------------------|------------------|
  | **Audiveris** | Java, reglas + ML    | **~69 %**          | Sí (2 pentagramas) |
  | **oemer**     | Python, deep learning | ~55 %              | No (aplasta a 1 parte) |

- **Conclusión:** Audiveris es más preciso y, sobre todo, **preserva la
  estructura de pentagramas**, que es lo que permite separar las voces
  (Caso A). oemer es más fácil de instalar (pip) pero hoy no sirve para
  separar voces de un himno.
- Ningún motor llega a 100 %: el flujo de producto **debe incluir un paso de
  revisión/corrección humana** antes de exportar las voces.

## Opción recomendada: Audiveris (server-side)

Audiveris es una aplicación Java; corre en el **backend**, no en el móvil.

### Requisitos

- JDK 21 (Audiveris 5.4) — versiones nuevas (master) piden JDK 25.
- Tesseract OCR + datos de idioma (`tesseract-ocr`, `tesseract-ocr-spa`).
- Gradle (incluido vía `./gradlew`).

### Construcción

```bash
git clone https://github.com/Audiveris/audiveris.git
cd audiveris
git checkout v5.4                      # rama estable para JDK 21
./gradlew :app:build -x test -x javadoc
# distribución ejecutable:
tar xf app/build/distributions/app-5.4.tar -C /opt/
```

#### Aviso: dependencia no-libre `jai-core`

Audiveris depende de `javax.media:jai-core:1.1.3` (Java Advanced Imaging), un
JAR **no-libre que no está en Maven Central** (solo su `.pom`). Normalmente se
descarga del repo de JBoss; si tu red lo bloquea, instálalo en el repo Maven
local desde una fuente alternativa:

```bash
# El JAR (mismas clases) está espejado en GitHub; el POM mínimo lo creas tú.
DEST=~/.m2/repository/javax/media/jai-core/1.1.3
mkdir -p "$DEST"
curl -sSL -o "$DEST/jai-core-1.1.3.jar" \
  https://raw.githubusercontent.com/francoisandre/repo/master/javax/media/jai_core/1.1.3/jai_core-1.1.3.jar
cat > "$DEST/jai-core-1.1.3.pom" <<'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>javax.media</groupId><artifactId>jai-core</artifactId>
  <version>1.1.3</version><packaging>jar</packaging>
</project>
EOF
```

`mavenLocal()` ya está en los repositorios del build, así que Gradle lo
resolverá. (Verifica la licencia de JAI para tu uso en producción.)

### Ejecución por lotes (batch)

```bash
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
/opt/app-5.4/bin/Audiveris -batch -export -output ./out  partitura.jpg
# genera out/partitura.mxl  (MusicXML comprimido)
```

## Alternativa ligera: oemer (Python/pip)

Sin Java; útil como respaldo o para melodías simples.

```bash
pip install oemer
oemer partitura.jpg -o ./out      # genera out/partitura.musicxml
```

Limitación medida: en himnos a 4 voces colapsa todo en **una sola parte** con
errores → no apto para separar voces, sí para una transcripción aproximada.

## Integración con el pipeline

Una vez tienes el MusicXML/MXL del OMR:

```bash
# Caso A — separar las 4 voces ya escritas y crear pistas de ensayo
python examples/omr_to_voices.py out/partitura.mxl -o practice/

# Caso B — si el OMR dio una sola melodía, generar armonía nueva
python -m armonic.cli out/partitura.musicxml -o coral.musicxml
```

## Recomendaciones de producto

1. **Lanza primero la entrada MusicXML/MIDI** (export de MuseScore): la
   separación de voces ya funciona de forma fiable, sin depender del OMR.
2. **OMR de foto = fase 2**, server-side con Audiveris, y **siempre** con
   pantalla de "revisa y corrige" antes de exportar.
3. **Preprocesa la imagen** (recorte, enderezado, contraste): una foto de
   celular con perspectiva baja mucho la precisión frente a un escaneo plano.
