#!/bin/bash
# Quick setup script to enable Audiveris OMR in current Codespaces environment
# Run this in the terminal to add Audiveris support without restarting Codespaces

set -e

echo "🎼 Setting up Audiveris OMR in Codespaces..."

# Install system dependencies if not already present
echo "📦 Installing Tesseract OCR..."
sudo apt-get update && sudo apt-get install -y tesseract-ocr > /dev/null 2>&1 || true

# Check if Audiveris is already built (from earlier build)
if [ -d "/opt/audiveris" ]; then
    echo "✅ Audiveris found at /opt/audiveris"
else
    # Build Audiveris from source
    echo "⚙️  Building Audiveris from source (10-15 minutes)..."
    bash /workspaces/armonic/.devcontainer/build-audiveris.sh
fi

# Export environment variable for current session
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
echo "export AUDIVERIS_BIN='/opt/audiveris/bin/Audiveris'" >> ~/.bashrc

echo "✅ Audiveris setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start the backend: docker compose up --build"
echo "  2. Upload a hymn image at http://localhost:8000"
echo "  3. Backend will run OMR and generate practice MIDI files"
