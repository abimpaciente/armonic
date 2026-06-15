# Arquitectura del Producto: armonic

Aplicación web para que los miembros de un coro puedan **subir fotos de himnos,
obtener sus voces en MIDI y practicar** armonizadas a 4 voces (SATB).

## 1. Visión y MVP

**Problema:** Un coro (p. ej. adventista) necesita pistas de ensayo por voz. Hoy:
- Exporta de MuseScore manualmente, o
- Busca en YouTube (baja calidad, no su tonalidad), o
- Nada (los miembros no ensayan fuera de reunión).

**Solución:** App web donde:
1. El usuario sube una **foto/PDF de una página del himnario**.
2. El backend reconoce la partitura (OMR con Audiveris) → MusicXML.
3. Se separan las **4 voces** (SATB).
4. Se generan **9 pistas MIDI**: solo (aprender tu voz), realce (tu voz + fondo), y mezcla completa.
5. El usuario **descarga** para practicar, o escucha online.

**MVP (Fase 1):**
- Soporta himnos en **partitura cerrada SATB** (2 pentagramas, típico del himnario adventista).
- Entrada: **foto limpia** (escaneo, no foto de celular con perspectiva).
- Salida: **MIDI descargable** por voz (solo + realce).
- Base de datos: guardar himnos procesados + metadatos (tonalidad, # de notas).

**Fases futuras:**
- Fase 2: OMR mejorado (preproceso de imagen, manejo de fotos de celular).
- Fase 3: Audio en tiempo real (WAV/MP3 con síntesis de voz en lugar de MIDI).
- Fase 4: Edición web (corrección manual del MusicXML antes de generar pistas).
- Fase 5: Comunidad (compartir arreglos, colaboración de coros).

## 2. Stack Tecnológico

### Frontend (Cliente)

**Tecnología:** Angular 18+ (PWA) — reutilizas el stack de Uniformes CMG.

**Librerías:**
- `@angular/material` — UI/componentes
- `ng-ogg` o `ng-sound` — reproducción MIDI en el navegador
- `opensheetmusicdisplay` — visualizar MusicXML en el navegador (opcional, Fase 2)
- `ng-file-upload` — carga de fotos

**Flujo de usuario:**
```
[Upload foto] → [Procesando...] → [Descargar MIDI]
                  ↓
              [Escuchar online]
                  ↓
              [Ver metadatos: tonalidad, nº notas, duración]
```

### Backend (API REST)

**Tecnología:** Python (FastAPI o Flask) — aprovechas music21 + Audiveris.

**Endpoints:**
```
POST   /api/upload              # sube foto, retorna job_id
GET    /api/job/{job_id}        # estado de procesamiento
GET    /api/hymn/{hymn_id}/midi # descarga MIDI (soprano_solo, bass_realce, etc.)
GET    /api/hymn/{hymn_id}      # metadatos (tonalidad, partes, notas)
```

**Flujo interno:**
```
[Foto JPG] 
    ↓
[Audiveris OMR] → MusicXML (5–30 segundos, CPU)
    ↓
[split_satb() + write_practice_tracks()] → 9 MIDI
    ↓
[Guardar en BD + almacenamiento] → JSON + archivos
    ↓
[Servir al cliente]
```

**Requisitos del servidor:**
- JDK 21 (Audiveris)
- Tesseract OCR + datos de idiomas (`eng`, `spa`)
- Python 3.11+ con music21, FastAPI, Pillow
- Storage: S3/Google Cloud Storage (o filesystem local)

### Base de Datos

**Tecnología:** Firestore (Firebase, como en Uniformes CMG) o PostgreSQL.

**Colecciones/Tablas:**

```
hymns
├── id (PK)
├── title (string) — "Cantad alegres al Señor"
├── number (int) — 1, 2, 3... del himnario
├── key (string) — "D major", "Bb major"
├── num_notes_per_voice (array) — [42, 42, 42, 42]
├── duration_seconds (float) — 120
├── uploaded_at (timestamp)
├── uploaded_by (user_id, nullable)
├── midi_files {
│   soprano_solo: "gs://bucket/hymn_123_soprano_solo.mid"
│   soprano_realce: "gs://bucket/hymn_123_soprano_realce.mid"
│   alto_solo: ...
│   ... (9 total)
│   satb_completo: ...
├── musicxml_url (string) — original o corregido (Fase 4)
├── metadata {
│   omr_quality: "good"|"fair"|"poor"  (~ cobertura Audiveris)
│   manually_corrected: boolean
│   corrections_log: string[]  (Fase 4)

users (si hay autenticación)
├── id (PK)
├── email
├── voice ("soprano"|"alto"|"tenor"|"bass")
├── created_at
├── hymns_downloaded (array de hymn_ids)
├── preferences {
│   auto_download: boolean
│   midi_instrument: "piano"|"organ"|"synth"  (Fase 3)
├── role ("singer"|"choir_admin"|"super_admin")

choirs (optional, Fase 5)
├── id (PK)
├── name — "Coro Adventista Los Ángeles"
├── members (array de user_ids)
├── hymn_library (array de hymn_ids)
├── active (boolean)
```

## 3. Flujo de Arquitectura (Secuencia)

```
┌─────────────────┐
│   User (web)    │
└────────┬────────┘
         │ 1. POST /api/upload + foto.jpg
         ↓
┌─────────────────────────────────────────────────┐
│  Backend API (FastAPI)                          │
│  ├─ 1a. Valida (JPG, < 20 MB, resolución OK)   │
│  ├─ 1b. Guarda en storage temporal              │
│  ├─ 1c. Enqueue job (Redis/Celery o similar)   │
│  └─ Retorna {job_id, status: "queued"}          │
└────────┬────────────────────────────────────────┘
         │
         │ 2. GET /api/job/{job_id}  [polling cada 2s]
         ↓
┌─────────────────────────────────────────────────┐
│  Worker (background job)                        │
│  ├─ 2a. Lee la foto del almacén temporal       │
│  ├─ 2b. Ejecuta: Audiveris -batch -export      │
│  │      (5–30 segundos, depende de CPU)        │
│  ├─ 2c. Parsea MusicXML                        │
│  │      Detecta tonalidad, nº de compases      │
│  ├─ 2d. split_satb() → 4 voces                │
│  ├─ 2e. write_practice_tracks() → 9 MIDI      │
│  ├─ 2f. Sube los 9 MIDI a storage (S3)        │
│  ├─ 2g. Inserta registro en BD (hymns)        │
│  └─ Status: "completed"                       │
└────────┬────────────────────────────────────────┘
         │
         │ 3. GET /api/hymn/{hymn_id}
         ↓
┌─────────────────────────────────────────────────┐
│  User Interface (Angular PWA)                   │
│  ├─ Muestra: título, tonalidad, duración       │
│  ├─ Botones: [Escuchar] [Descargar MIDI]       │
│  ├─ Tabs: Soprano | Alto | Tenor | Bass        │
│  ├─ Cada tab: [Solo] [Realce] [Completo]       │
│  └─ Audio HTML5 <audio> (en-línea o descarga)  │
└─────────────────────────────────────────────────┘
```

## 4. Implementación: Fases

### Fase 1 (MVP, 4–6 semanas)

**Qué entra:**
- ✅ Backend OMR básico (Audiveris en servidor, ya probado).
- ✅ Separación SATB + generación MIDI (código ya existe).
- ✅ API REST simple (upload, job status, download).
- ✅ Frontend PWA (Angular) con carga de foto + lista de descargas.
- ✅ BD Firestore (guardas himnos + URLs de MIDI).

**Qué NO entra:**
- Autenticación (MVP público, o login básico).
- Edición/corrección de MusicXML.
- Audio sintetizado (MIDI solo).
- UI compleja (útil pero no bloqueante).

**Tareas:**
```
Backend (2–3 semanas)
├─ Setup FastAPI + BD Firestore
├─ Endpoint POST /upload (valida foto, enqueue)
├─ Worker OMR (Audiveris loop, armonic.voices)
├─ Endpoints GET /job/{id}, /hymn/{id}, /hymn/{id}/midi
├─ Logging + manejo de errores
└─ Deploy (Docker, Cloud Run o similar)

Frontend (2 semanas)
├─ Pantalla de upload (drag-drop, progress bar)
├─ Listado de himnos (tabla simple)
├─ Links de descarga para cada MIDI
├─ Reproductor HTML5 <audio> inline
└─ Responsive (mobile + desktop)

Infraestructura (1–2 semanas)
├─ Servidor Audiveris (JDK 21 + Tesseract)
├─ Storage (S3/GCS para MIDI)
├─ BD (Firestore setup)
└─ Dominio + SSL
```

### Fase 2 (Mejoras OMR, 2–3 semanas)

- Preproceso de imagen (recorte, enderezado, contraste).
- Manejo de fotos de celular (perspectiva).
- Pantalla de preview MusicXML antes de generar MIDI.
- QA del OMR (métricas de confianza).

### Fase 3 (Audio de calidad, 3–4 semanas)

- Síntesis de voz (Espeak, Google TTS, o MuseScore API) → WAV/MP3.
- Opción de cambiar instrumento (piano, órgano, voz).
- Descarga en formatos múltiples (MIDI, MP3, WAV).

### Fase 4 (Corrección manual, 2–3 semanas)

- Editor web de MusicXML (Vexflow + correcciones).
- Validación humana antes de publicar.
- Historial de cambios.

### Fase 5 (Comunidad, 4+ semanas)

- Sistema de usuarios + coros.
- Compartir arreglos.
- Colaboración entre directores.

## 5. Estimación de Costos (MVP)

### Desarrollo

| Rol | Esfuerzo | Costo (USD aprox.) |
|---|---|---|
| Backend (Python/FastAPI) | 3 semanas | $3,000–5,000 |
| Frontend (Angular/PWA) | 2 semanas | $2,000–3,500 |
| DevOps/Infraestructura | 1.5 semanas | $1,500–2,500 |
| QA + documentación | 1 semana | $1,000–1,500 |
| **Total** | **7.5 semanas** | **$7,500–12,500** |

(Estimación para 1 dev full-stack + 1 frontend dev, costo horario USA ~$75–100/hr)

### Infraestructura (recurrente, /mes)

| Servicio | Uso (MVP) | Costo/mes |
|---|---|---|
| Servidor Audiveris (GCE 4-core, 16GB) | CPU OMR | $100–150 |
| Storage (GCS/S3) | ~1000 himnos × 100KB | $5–10 |
| Firestore | ~500 docs, <10GB | $10–20 |
| Dominio + CDN | Optional | $10–20 |
| **Total** | | **$125–200/mes** |

(Con auto-scaling, puede variar si tienes 100K usuarios.)

## 6. Stack Alternativo Ligero (sin OMR server)

Si no quieres compilar Audiveris, opción alternativa:

**Cliente → Audiveris en escritorio del usuario**
```
User
├─ Instala armonic (pip install)
├─ Corre: python -m armonic.cli foto.jpg -o himno.musicxml
├─ Luego: python examples/omr_to_voices.py himno.musicxml
└─ Obtiene 9 MIDI localmente (sin servidor)

Luego sube los MIDI a una BD/storage compartida (Nextcloud, Google Drive, etc.)
```

**Ventaja:** cero infraestructura.  
**Desventaja:** cada usuario instala, no hay interfaz unificada, no escalable.

## 7. Checklist de Pre-build

- [ ] Decisión: ¿MVP público o acceso restringido?
- [ ] Decisión: ¿Audiveris en servidor (Phase 1) o en cliente?
- [ ] Servidor Audiveris configurado (ver `docs/OMR.md`).
- [ ] Credenciales Firestore (o DB elegida) listas.
- [ ] Dominio y SSL.
- [ ] Plan de copias de seguridad (MIDI almacenados).
- [ ] Términos de servicio (derechos de autor de himnos).

## 8. Propuesta: Cómo Empezar

**Opción A — Full MVP (4–6 semanas, recomendado)**
1. Contrata/asigna: 1 backend dev + 1 frontend dev.
2. Sigue el plan de Fase 1.
3. Lanza MVP público o interno.

**Opción B — MVP Ligero (1–2 semanas, proof of concept)**
1. Arma un servidor básico OMR (Audiveris en GCE).
2. Frontend: formulario simple (upload + descargas).
3. BD: Firestore con tabla minimal (himn_id, URL MIDI).
4. Lanza y valida tráfico real.
5. Itera.

**Opción C — Sin servidor (proof of concept, 1 semana)**
1. Script CLI con armonic: `python -m armonic.cli`.
2. Distribuye a 10 coristas.
3. Recoge feedback.
4. Decide si vale la pena el MVP server.

## Recomendación

**Comienza con Opción B:** servidor OMR mínimo + MVP web en 4–5 semanas. Valida
que los coristas de verdad usen la app. Luego escala con Fase 2/3 si hay demanda.
