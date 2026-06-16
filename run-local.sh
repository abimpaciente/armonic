#!/bin/bash
# Corre armonic SIN Docker (backend FastAPI sirviendo el frontend Angular).
# Funciona en Debian/Ubuntu (apt) y Alpine (apk). Uso:
#   bash run-local.sh            # arranca (compila Audiveris/front la 1ª vez)
#   bash run-local.sh --rebuild  # fuerza recompilar el frontend
set -e
cd "$(dirname "$0")"

SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
if command -v apt-get >/dev/null 2>&1; then PM="apt"
elif command -v apk >/dev/null 2>&1; then PM="apk"
else echo "❌ Sin apt-get ni apk; SO no soportado."; exit 1; fi
echo "🧰 Package manager: $PM"

# 1. Audiveris + datos OCR (eng+spa). Una sola vez (~10-15 min).
if [ ! -x /opt/audiveris/bin/Audiveris ]; then
    echo "🎼 Audiveris no está instalado; construyéndolo…"
    bash .devcontainer/build-audiveris.sh
fi
export AUDIVERIS_BIN=/opt/audiveris/bin/Audiveris
export TESSDATA_PREFIX=/opt/tessdata
export OMR_LANG=spa+eng
export ARMONIC_STORAGE="$PWD/storage"

# 2. Node (para compilar el frontend).
if ! command -v npm >/dev/null 2>&1; then
    echo "📦 Instalando Node…"
    if [ "$PM" = "apt" ]; then $SUDO apt-get install -y -qq nodejs npm
    else $SUDO apk add --no-cache nodejs npm >/dev/null; fi
fi

# 3. Python + dependencias del backend.
PIP_FLAGS=""
if [ "$PM" = "apk" ]; then
    command -v pip3 >/dev/null 2>&1 || $SUDO apk add --no-cache python3 py3-pip >/dev/null
    PIP_FLAGS="--break-system-packages"   # Alpine marca el entorno como gestionado
fi
echo "🐍 Instalando dependencias del backend…"
$SUDO python3 -m pip install $PIP_FLAGS -q -e ".[backend]"

# 4. Compila el frontend dentro de backend/static (1ª vez o con --rebuild).
if [ "$1" = "--rebuild" ] || [ ! -f backend/static/index.html ]; then
    echo "📱 Compilando el frontend…"
    (cd frontend && npm ci && npm run build)
    mkdir -p backend/static
    rm -rf backend/static/*
    cp -r frontend/dist/frontend/browser/* backend/static/
fi

# 5. Arranca el servidor (frontend + API en el mismo puerto).
echo ""
echo "✅ armonic en http://localhost:${PORT:-8000}  (abre el puerto 8000 reenviado)"
exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
