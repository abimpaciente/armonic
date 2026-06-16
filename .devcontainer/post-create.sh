#!/bin/bash
# Se ejecuta al crear el contenedor (Debian + Java 21 + Node + Python).
# Deja las dependencias instaladas; Audiveris se compila al correr run-local.sh.
set -e
cd "$(dirname "$0")/.."

echo "🐍 Instalando dependencias del backend…"
pip install -e ".[backend]" || python3 -m pip install -e ".[backend]" || true

echo "📱 Instalando dependencias del frontend…"
(cd frontend && npm ci) || true

echo ""
echo "✅ Entorno listo. Para arrancar armonic:"
echo "     bash run-local.sh"
echo "   (la 1ª vez compila Audiveris, ~10-15 min; luego es instantáneo)"
