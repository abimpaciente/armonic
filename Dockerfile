# ---- Stage 1: build the Angular frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend that also serves the built frontend ----
FROM python:3.11-slim
WORKDIR /app

# NOTE: el MVP solo necesita Python (music21 + FastAPI son puro Python/wheels).
# El OMR de fotos (Audiveris) requiere Java + Tesseract; cuando se integre,
# añadir aquí: apt-get install default-jre-headless tesseract-ocr
# (paquetes que existen en cualquier versión de Debian).

# Backend code + install
COPY . .
RUN pip install --no-cache-dir -e ".[backend]"

# Drop the built Angular app into the static dir the backend serves at "/"
COPY --from=frontend /fe/dist/frontend/browser/ /app/backend/static/

# Storage for hymns and MIDI files
RUN mkdir -p /app/storage

EXPOSE 8000

# Health check using stdlib only (no extra deps)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/api/health')" || exit 1

# Render (and most PaaS) inject $PORT; default to 8000 locally
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
