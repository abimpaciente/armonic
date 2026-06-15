# armonic — Backend (API REST)

API que envuelve el núcleo `armonic`: recibe una foto/partitura, la procesa
(OMR → separación SATB / armonización → pistas de ensayo) y sirve los MIDI por
voz. Incluye una página de prueba en `/`.

## Requisitos

### Opción A: Docker (recomendado)

- Docker 20+ y Docker Compose 1.29+
- ```bash
  docker-compose up --build
  ```
- Abre <http://localhost:8000/> para la página de prueba.

### Opción B: Local

- Python 3.10+ con el paquete `armonic` instalado:
  ```bash
  pip install -e ".[backend]"     # desde la raíz del repo
  ```
- **Para OMR de imágenes** (opcional): Audiveris + Tesseract en el servidor
  (ver [`docs/OMR.md`](../docs/OMR.md)). Sin OMR, el backend acepta
  MusicXML/MIDI directamente.

## Variables de entorno

| Variable | Para qué | Ejemplo |
|----------|----------|---------|
| `ARMONIC_STORAGE` | Carpeta de datos | `./backend/storage` |
| `AUDIVERIS_BIN` | Ejecutable de Audiveris (habilita OMR) | `/opt/app-5.4/bin/Audiveris` |
| `TESSDATA_PREFIX` | Datos de Tesseract (requerido por Audiveris) | `/usr/share/tesseract-ocr/5/tessdata` |
| `ARMONIC_MAX_UPLOAD_MB` | Límite de subida | `25` |

## Arrancar (Local)

```bash
export AUDIVERIS_BIN=/opt/app-5.4/bin/Audiveris        # opcional (OMR)
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
export ARMONIC_STORAGE=./backend/storage

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Abre <http://localhost:8000/> para la página de prueba.

## Arrancar (Docker)

```bash
# Desde la raíz del proyecto
docker-compose up --build

# En otra terminal, prueba la API:
curl http://localhost:8000/api/health
```

El contenedor monta un volumen `storage` para persistir himnos y MIDI entre reinicios.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET  | `/api/health` | Estado y si el OMR está disponible |
| POST | `/api/upload` | Sube foto/partitura → `{job_id}` |
| GET  | `/api/job/{job_id}` | Estado del procesamiento |
| GET  | `/api/hymns` | Biblioteca de himnos procesados |
| GET  | `/api/hymn/{hymn_id}` | Metadatos + lista de pistas |
| GET  | `/api/hymn/{hymn_id}/midi/{track}` | Descarga un MIDI |

`track` es uno de: `soprano_solo`, `soprano_realce`, … `bass_realce`,
`satb_completo`.

### Ejemplo

```bash
# Subir
curl -F "file=@himno.jpg" http://localhost:8000/api/upload
# -> {"job_id":"abc123","status":"queued"}

# Consultar estado
curl http://localhost:8000/api/job/abc123
# -> {"status":"completed","hymn_id":"xyz789", ...}

# Metadatos
curl http://localhost:8000/api/hymn/xyz789

# Descargar la voz de bajo (solo)
curl -OJ http://localhost:8000/api/hymn/xyz789/midi/bass_solo
```

## Lógica

- Imagen (`.jpg/.png/…`) → OMR (Audiveris) → MusicXML.
- MusicXML/MIDI directo → se usa tal cual.
- ≥2 pentagramas → **separación SATB** (Caso A).
- 1 sola voz → **armonización** a 4 voces (Caso B).
- Siempre genera 9 pistas de ensayo.

## Pruebas

```bash
python -m pytest backend/tests/ -q
```

## Notas de producción

Este MVP usa almacenamiento en disco y un registro de jobs en memoria
(proceso único). Para producción, reemplazar `store.py` por Firestore/Postgres,
los MIDI por S3/GCS, y los jobs por una cola (Celery/RQ) con varios workers.
Ver [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
