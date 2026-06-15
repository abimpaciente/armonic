#!/bin/bash
set -e

echo "🎵 Setting up armonic development environment..."

# Install system dependencies for OMR (Audiveris + Tesseract)
echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y --no-install-recommends \
    tesseract-ocr \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    pip

# Python backend setup
echo "🐍 Setting up Python backend..."
cd /workspaces/armonic
pip install --no-cache-dir -e ".[backend]"

# Frontend setup
echo "📱 Setting up Node.js frontend..."
cd /workspaces/armonic/frontend
npm ci

# Build Audiveris from source (optional, can take 10-15 min)
echo "🎼 Audiveris setup instructions:"
echo "   To build Audiveris from source, run: bash .devcontainer/build-audiveris.sh"
echo "   Or set AUDIVERIS_BIN environment variable to your local Audiveris path"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. (Optional) Build Audiveris: bash .devcontainer/build-audiveris.sh"
echo "  2. Start backend: cd /workspaces/armonic && docker compose up --build"
echo "  3. Open http://localhost:8000 in your browser"
