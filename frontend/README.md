# armonic — Frontend (Angular PWA)

App web para subir himnos y practicar tu voz. Consume la API del backend
(`/api`) y reproduce los MIDI por voz en el navegador.

## Requisitos

- Node 18+ y npm.
- El **backend** corriendo en `http://localhost:8000` (ver `../backend/README.md`).

## Desarrollo

```bash
cd frontend
npm install
npm start            # ng serve con proxy /api -> localhost:8000
# abre http://localhost:4200
```

El proxy (`proxy.conf.json`) enruta las llamadas `/api/*` al backend, así que
ambos corren en paralelo sin CORS.

## Build de producción

```bash
npm run build        # genera dist/frontend
```

Sirve `dist/frontend` detrás del mismo dominio que la API (o configura un
reverse proxy para `/api`).

## Estructura

```
src/app/
  api.service.ts        # llamadas a la API (upload, job, hymn, midi)
  voice.service.ts      # guarda "tu voz" en localStorage
  app.component.ts      # shell (header + router-outlet)
  app.routes.ts         # rutas + guard de onboarding
  pages/
    onboarding.component.ts  # elegir tu voz (primera vez)
    home.component.ts        # subir himno + biblioteca + búsqueda
    hymn.component.ts        # voces + reproductor MIDI (tu voz destacada)
```

## Notas

- El reproductor MIDI usa el web component `<midi-player>`
  (`html-midi-player`), cargado por CDN en `index.html`.
- PWA: incluye `manifest.webmanifest`. Para el service worker completo
  (offline), ejecutar `ng add @angular/pwa`.
