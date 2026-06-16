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

# 1. Java 21 is required to build AND run Audiveris 5.4. Auto-install Temurin
#    21 if it's missing (default Codespaces images may ship no JDK at all).
if ! java -version 2>&1 | grep -q 'version "21'; then
    echo "☕ Java 21 not found; installing Temurin 21…"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq wget apt-transport-https gpg ca-certificates
    wget -qO- https://packages.adoptium.net/artifactory/api/gpg/key/public \
        | gpg --dearmor | $SUDO tee /etc/apt/trusted.gpg.d/adoptium.gpg >/dev/null
    . /etc/os-release
    echo "deb https://packages.adoptium.net/artifactory/deb ${VERSION_CODENAME} main" \
        | $SUDO tee /etc/apt/sources.list.d/adoptium.list >/dev/null
    $SUDO apt-get update -qq
    $SUDO apt-get install -y temurin-21-jdk
fi
if ! java -version 2>&1 | grep -q 'version "21'; then
    echo "❌ Could not get Java 21 on PATH. Current java:"
    java -version 2>&1 || echo "   (no java on PATH)"
    exit 1
fi
echo "☕ Using: $(java -version 2>&1 | head -1)"

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

# 5. OCR language data for the TITLE/lyrics. Audiveris uses Tesseract's *legacy*
#    engine, which needs the full traineddata (eng ships with the repo; spa is
#    fetched). Without this, Audiveris skips text and the hymn has no title.
echo "🔤 Installing OCR language data (eng + spa)..."
TESS_DIR="/opt/tessdata"
$SUDO mkdir -p "$TESS_DIR"
$SUDO cp "$BUILD_DIR/app/dev/tessdata/eng.traineddata" "$TESS_DIR/"
$SUDO curl -sL -o "$TESS_DIR/spa.traineddata" \
    https://github.com/tesseract-ocr/tessdata/raw/4.1.0/spa.traineddata

echo ""
echo "✅ Audiveris installed at $INSTALL_PREFIX/bin/Audiveris"
echo ""
echo "Now point the backend at it and restart (add to ~/.bashrc to persist):"
echo "  export AUDIVERIS_BIN=\"$INSTALL_PREFIX/bin/Audiveris\""
echo "  export TESSDATA_PREFIX=\"$TESS_DIR\""
echo "  export OMR_LANG=\"spa+eng\""
