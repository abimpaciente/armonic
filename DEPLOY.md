# Deploy de armonic

El repo ya trae todo listo para desplegar **backend + frontend juntos** desde
un solo contenedor Docker: el backend de FastAPI sirve la app Angular compilada
en `/` y la API en `/api`, así que todo vive en **el mismo dominio sin CORS**.

## Opción recomendada: Render (con `render.yaml`)

Render lee el archivo [`render.yaml`](render.yaml) y configura el servicio solo.

### Pasos (≈5 min)

1. Crea una cuenta en <https://render.com> (puedes entrar con tu GitHub).
2. En el panel: **New +** → **Blueprint**.
3. Conecta tu repositorio `abimpaciente/armonic` y elige la rama
   `claude/music-omr-harmony-7lepaf` (o la que tenga estos cambios).
4. Render detecta `render.yaml`, te muestra el servicio **armonic** y un botón
   **Apply**. Dale clic.
5. Espera el primer build (compila Angular + instala el backend; ~5–10 min la
   primera vez).
6. Cuando termine, Render te da una **URL pública** del tipo
   `https://armonic.onrender.com`. Ábrela desde tu teléfono. ✅

### Notas del plan gratis

- El servicio **se duerme** tras ~15 min sin uso; la primera visita después
  tarda ~50 s en despertar. Normal en el plan free.
- El disco es **efímero**: si Render reinicia el contenedor, la biblioteca de
  himnos se borra. Para *validar* con tu coro está bien (subes un himno y lo
  pruebas en la sesión).
- **Para persistir himnos**: sube a un plan de pago y descomenta el bloque
  `disk:` en `render.yaml` (monta `/app/storage` en un disco real).

## Alternativa: cualquier host con Docker

Como es un contenedor estándar, también corre en Railway, Fly.io, un VPS, etc.:

```bash
docker build -t armonic .
docker run -p 8000:8000 -e PORT=8000 armonic
# abre http://localhost:8000
```

El contenedor escucha en `$PORT` (Render/Railway lo inyectan) o 8000 por
defecto.

## Probar el contenedor en tu máquina antes de desplegar

```bash
docker compose up --build      # construye y levanta en http://localhost:8000
```

(Recuerda parar otros proyectos que usen el puerto 8000, como uniformes cmg.)

## ¿Qué incluye la imagen?

- Python 3.11 + FastAPI + music21 (núcleo de armonía y separación de voces).
- La app Angular **ya compilada**, servida por el backend.
- Java 17 + Tesseract (habilitan el OMR opcional de fotos; sin esto, el backend
  acepta MusicXML/MIDI directo).
