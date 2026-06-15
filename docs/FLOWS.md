# Flujos de Usuario: armonic

Cómo vive la persona la app, pantalla por pantalla. Hay 3 perfiles:

- **Corista** (p. ej. tú, que cantas bajo): sube himnos y practica su voz.
- **Director de coro**: gestiona la biblioteca de himnos del coro.
- **Sistema/Backend**: procesa en segundo plano.

---

## Flujo 0 — Onboarding (primera vez)

```
[Abrir app]
   │
   ▼
[¿Qué voz cantas?]
   ├─ Soprano
   ├─ Alto
   ├─ Tenor
   └─ Bass  ◄── (el usuario elige la suya)
   │
   ▼
[Listo] ──► La app recordará tu voz y la destacará
            en cada himno (botón grande "Mi voz: Bass")
```

> Se guarda en `users.voice`. Beneficio: el corista entra a cualquier himno y
> ve su pista al frente, sin buscar.

---

## Flujo 1 — Subir un himno nuevo (flujo estrella) ⭐

```
[Inicio]
   │  toca "＋ Subir himno"
   ▼
[Tomar foto] ó [Elegir de galería]
   │
   ▼
[Preview de la imagen]
   │  "¿Se ve completa y derecha?"
   ├─ No ──► [Reintentar / recortar]
   └─ Sí ──► toca "Procesar"
   │
   ▼
┌──────────────────────────────┐
│  Procesando...               │
│  ▓▓▓▓▓▓░░░░  60%             │
│  • Leyendo partitura (OMR)   │
│  • Separando 4 voces         │
│  • Generando pistas          │
│  (~10–30 segundos)           │
└──────────────────────────────┘
   │
   ▼
[✓ Listo: "Cantad alegres al Señor"]
   │  Tonalidad: Re mayor · 4 voces · 0:45
   │
   ▼  (va directo al Flujo 3 — Practicar)
```

> Si la foto es mala, el sistema puede avisar **antes** de gastar tiempo:
> "La imagen está borrosa/torcida, ¿continuar igual?" (Flujo 4).

---

## Flujo 2 — Buscar un himno ya existente (caché) 🔍

Evita reprocesar lo que ya alguien subió.

```
[Inicio]
   │  toca "🔍 Buscar"
   ▼
[Escribe número o título]
   │  "14"  ó  "Engrandecido"
   ▼
┌─────────────────────────────────────┐
│  Resultados                         │
│  ► #1  Cantad alegres al Señor      │
│  ► #14 Engrandecido sea Dios   ◄──  │
│  ► #2  Da gloria al Señor           │
└─────────────────────────────────────┘
   │  toca uno
   ▼
[Himno listo] ──► (Flujo 3 — Practicar)
                   SIN reprocesar (ya está en la BD)
```

> Clave de producto: **la biblioteca crece sola**. El primer corista que sube
> el himno #14 lo deja disponible para todo el coro.

---

## Flujo 3 — Practicar / escuchar (el corazón) 🎧

```
┌───────────────────────────────────────────────┐
│  Engrandecido sea Dios               #14       │
│  La bemol mayor · 4 voces · 0:48               │
│                                                │
│  ┌─────────────────────────────────────────┐  │
│  │  MI VOZ:  ♪ Bass                         │  │ ◄── destacada
│  │  [ ▶ Solo ]  [ ▶ Con fondo ]  [ ⤓ ]     │  │     (preferencia)
│  └─────────────────────────────────────────┘  │
│                                                │
│  Otras voces:                                  │
│  Soprano   [▶ Solo] [▶ Fondo] [⤓]             │
│  Alto      [▶ Solo] [▶ Fondo] [⤓]             │
│  Tenor     [▶ Solo] [▶ Fondo] [⤓]             │
│                                                │
│  Todas juntas  [ ▶ ]  [ ⤓ ]                   │
└───────────────────────────────────────────────┘

  ▶ Solo       = solo tu voz (aprender la melodía)
  ▶ Con fondo  = tu voz fuerte + las otras suaves (ensayar en contexto)
  ⤓            = descargar MIDI a tu teléfono
```

**Sub-flujo de reproducción:**
```
[Toca ▶ Solo en Bass]
   │
   ▼
[Reproductor en barra inferior]
   ◄◄  ▶/❚❚  ►►   ━━━●────  0:12 / 0:48   🔁
   │
   ├─ Pausar / reanudar
   ├─ Saltar adelante/atrás
   └─ Repetir (loop para practicar un fragmento)
```

---

## Flujo 4 — Cuando el OMR falla o duda ⚠️

El OMR no es perfecto (sobre todo con fotos). El flujo lo maneja con honestidad.

```
[Procesando...]
   │
   ├─ Calidad BUENA ──────► [Himno listo] (Flujo 3)
   │
   ├─ Calidad DUDOSA ─────► ┌─────────────────────────────┐
   │                        │ ⚠ Leímos el himno pero      │
   │                        │   puede tener errores.      │
   │                        │ [Usar así] [Subir mejor foto]│
   │                        └─────────────────────────────┘
   │
   └─ FALLÓ (no es partitura, muy borrosa)
                            ┌─────────────────────────────┐
                            │ ✗ No pudimos leer la imagen. │
                            │ Consejos:                    │
                            │ • Foto derecha, sin sombras  │
                            │ • Una página a la vez        │
                            │ [Reintentar]                 │
                            └─────────────────────────────┘
```

> Métrica `omr_quality` (good/fair/poor) en la BD decide qué ruta mostrar.

---

## Flujo 5 — Director de coro (gestión) 👔

```
[Panel del director]
   │
   ├─ [Biblioteca del coro]
   │     ► Lista de himnos del repertorio
   │     ► Agregar/quitar himnos
   │     ► Marcar "himnos de este mes"
   │
   ├─ [Miembros]
   │     ► Ver quién canta qué voz
   │     ► Invitar coristas (link/código)
   │
   └─ [Corregir himno]  (Fase 4)
         ► Abrir editor de notación
         ► Ajustar notas mal leídas por el OMR
         ► Re-generar pistas corregidas
```

---

## Flujo Técnico (qué pasa por detrás) ⚙️

Para el equipo de desarrollo — corresponde al Flujo 1.

```
Cliente (Angular PWA)              Backend (FastAPI)            Worker
       │                                  │                       │
       │ 1. POST /upload (foto.jpg)       │                       │
       │─────────────────────────────────►│                       │
       │                                  │ valida + guarda temp  │
       │                                  │ encola job            │
       │                                  │──────────────────────►│
       │ ◄─── {job_id, "queued"} ─────────│                       │
       │                                  │                       │ Audiveris OMR
       │ 2. GET /job/{id}  (cada 2s)      │                       │  → MusicXML
       │─────────────────────────────────►│                       │ split_satb()
       │ ◄─── {"processing", 60%} ────────│                       │  → 4 voces
       │ 2. GET /job/{id}                 │                       │ write_tracks()
       │─────────────────────────────────►│                       │  → 9 MIDI
       │                                  │                       │ sube a storage
       │                                  │ ◄─────────────────────│ guarda en BD
       │ ◄─── {"completed", hymn_id} ─────│                       │
       │                                  │                       │
       │ 3. GET /hymn/{id}                │                       │
       │─────────────────────────────────►│                       │
       │ ◄─── {metadatos + 9 URLs MIDI} ──│                       │
       │                                  │                       │
       │ 4. Reproduce / descarga MIDI desde storage (CDN)         │
```

**Tiempos esperados:**
- Upload: 1–3 s (según red y tamaño de foto)
- OMR (Audiveris): 5–30 s (según CPU y densidad del himno)
- Separación + MIDI: < 1 s
- Total percibido: **~10–35 segundos** con barra de progreso

---

## Resumen de pantallas (MVP)

| # | Pantalla | Flujo |
|---|----------|-------|
| 1 | Onboarding (elegir voz) | 0 |
| 2 | Inicio (Subir / Buscar) | 1, 2 |
| 3 | Cámara / Galería + Preview | 1 |
| 4 | Procesando (progreso) | 1, 4 |
| 5 | Himno: voces + reproductor | 3 |
| 6 | Búsqueda + resultados | 2 |
| 7 | Error / calidad dudosa | 4 |
| 8 | Panel director (Fase 5) | 5 |

> El MVP mínimo viable son las pantallas **2, 4 y 5** (subir → procesar →
> practicar). Las demás se agregan después.
