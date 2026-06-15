#!/bin/bash
# Build and install Audiveris 5.4 from source into /opt/audiveris.
# Works in GitHub Codespaces or any Linux box with Java 21 + git.
set -e

INSTALL_PREFIX="/opt/audiveris"
BUILD_DIR="/tmp/audiveris-build"

# Use sudo only if we are not already root.
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

echo "🎼 Installing Audiveris OMR..."

# 1. Java 21 is required to build AND run Audiveris 5.4.
if ! java -version 2>&1 | grep -q '"21'; then
    echo "❌ Java 21 not found. Current java:"
    java -version 2>&1 || echo "   (no java on PATH)"
    echo "   In Codespaces, switch with:  sudo update-alternatives --config java"
    echo "   or rebuild the container (uses the java:21 devcontainer)."
    exit 1
fi

# 2. Tesseract (Audiveris uses libtesseract via JNI).
echo "📦 Installing Tesseract OCR..."
$SUDO apt-get update -qq
$SUDO apt-get install -y --no-install-recommends tesseract-ocr

# 3. Clone + build (~10-15 min the first time).
if [ ! -d "$BUILD_DIR" ]; then
    echo "📥 Cloning Audiveris v5.4..."
    # Pin to v5.4: builds with JDK 21. main (5.10+) requires Java 25.
    git clone --depth 1 --branch v5.4 https://github.com/Audiveris/audiveris.git "$BUILD_DIR"
fi
echo "⚙️  Building Audiveris (this takes ~10-15 minutes)..."
cd "$BUILD_DIR"
./gradlew clean build -x test

# 4. Install the distribution.
echo "📦 Installing to $INSTALL_PREFIX ..."
$SUDO mkdir -p "$INSTALL_PREFIX"
$SUDO tar -xf app/build/distributions/app-5.4.tar -C "$INSTALL_PREFIX" --strip-components=1
$SUDO ln -sf "$INSTALL_PREFIX/bin/Audiveris" /usr/local/bin/audiveris

echo ""
echo "✅ Audiveris installed at $INSTALL_PREFIX/bin/Audiveris"
echo ""
echo "Now point the backend at it and restart:"
echo "  export AUDIVERIS_BIN=\"$INSTALL_PREFIX/bin/Audiveris\""
