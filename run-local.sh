#!/bin/bash
# Corre armonic SIN Docker (backend FastAPI sirviendo el frontend Angular).
# Pensado para GitHub Codespaces. Uso:
#   bash run-local.sh            # arranca (build de frontend solo la 1ª vez)
#   bash run-local.sh --rebuild  # fuerza recompilar el frontend
set -e
cd "$(dirname "$0")"

# 1. Audiveris + datos de OCR (eng+spa). Se construye una sola vez (~10-15 min).
if [ ! -x /opt/audiveris/bin/Audiveris ]; then
    echo "🎼 Audiveris no está instalado; construyéndolo (~10-15 min)…"
    bash .devcontainer/build-audiveris.sh
fi
export AUDIVERIS_BIN=/opt/audiveris/bin/Audiveris
export TESSDATA_PREFIX=/opt/tessdata
export OMR_LANG=spa+eng
export ARMONIC_STORAGE="$PWD/storage"

# 2. Dependencias de Python.
echo "🐍 Instalando dependencias del backend…"
pip install -q -e ".[backend]"

# 3. Compila el frontend dentro de backend/static (1ª vez o con --rebuild).
if [ "$1" = "--rebuild" ] || [ ! -f backend/static/index.html ]; then
    echo "📱 Compilando el frontend…"
    (cd frontend && npm ci && npm run build)
    mkdir -p backend/static
    rm -rf backend/static/*
    cp -r frontend/dist/frontend/browser/* backend/static/
fi

# 4. Arranca el servidor (frontend + API en el mismo puerto).
echo ""
echo "✅ armonic en http://localhost:${PORT:-8000}"
echo "   (en Codespaces, abre el puerto 8000 reenviado)"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
