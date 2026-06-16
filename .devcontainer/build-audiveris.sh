#!/bin/bash
# Build and install Audiveris 5.4 from source into /opt/audiveris.
# Works on Debian/Ubuntu (apt) and Alpine (apk). Needs git + curl.
set -e

INSTALL_PREFIX="/opt/audiveris"
BUILD_DIR="/tmp/audiveris-build"
TESS_DIR="/opt/tessdata"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

# Detect package manager.
if command -v apt-get >/dev/null 2>&1; then PM="apt"
elif command -v apk >/dev/null 2>&1; then PM="apk"
else echo "❌ No apt-get nor apk found; unsupported OS."; exit 1; fi
echo "🎼 Installing Audiveris OMR (package manager: $PM)…"

# 1. Java 21 (build + runtime).
if ! java -version 2>&1 | grep -q 'version "21'; then
    echo "☕ Java 21 not found; installing…"
    if [ "$PM" = "apt" ]; then
        $SUDO apt-get update -qq || true
        $SUDO apt-get install -y -qq wget apt-transport-https gpg ca-certificates
        wget -qO- https://packages.adoptium.net/artifactory/api/gpg/key/public \
            | gpg --dearmor | $SUDO tee /etc/apt/trusted.gpg.d/adoptium.gpg >/dev/null
        . /etc/os-release
        echo "deb https://packages.adoptium.net/artifactory/deb ${VERSION_CODENAME} main" \
            | $SUDO tee /etc/apt/sources.list.d/adoptium.list >/dev/null
        $SUDO apt-get update -qq
        $SUDO apt-get install -y temurin-21-jdk
    else
        # Alpine: openjdk21 + gcompat (glibc shim, helps native Tesseract load).
        $SUDO apk add --no-cache openjdk21 gcompat curl git >/dev/null
        JHOME="$(ls -d /usr/lib/jvm/java-21-openjdk 2>/dev/null || ls -d /usr/lib/jvm/java-21-* | head -1)"
        $SUDO ln -sf "$JHOME/bin/java" /usr/local/bin/java
        $SUDO ln -sf "$JHOME/bin/javac" /usr/local/bin/javac
        export JAVA_HOME="$JHOME"
    fi
fi
if ! java -version 2>&1 | grep -q 'version "21'; then
    echo "❌ Could not get Java 21 on PATH."; java -version 2>&1 || true; exit 1
fi
echo "☕ Using: $(java -version 2>&1 | head -1)"

# 2. Tesseract runtime (libtesseract for Audiveris' OCR via JNI).
echo "📦 Installing Tesseract…"
if [ "$PM" = "apt" ]; then
    # '|| true': a broken 3rd-party repo (e.g. yarn) must not abort us; the
    # Ubuntu main repo still refreshes and provides tesseract/curl.
    $SUDO apt-get update -qq || true
    $SUDO apt-get install -y --no-install-recommends tesseract-ocr curl ca-certificates
else
    $SUDO apk add --no-cache tesseract-ocr curl >/dev/null || true
fi

# 3. Clone + build (~10-15 min the first time).
if [ ! -d "$BUILD_DIR" ]; then
    echo "📥 Cloning Audiveris v5.4…"
    git clone --depth 1 --branch v5.4 https://github.com/Audiveris/audiveris.git "$BUILD_DIR"
fi
echo "⚙️  Building Audiveris (this takes ~10-15 minutes)…"
cd "$BUILD_DIR"
./gradlew clean build -x test

# 4. Install the distribution.
echo "📦 Installing to $INSTALL_PREFIX …"
$SUDO mkdir -p "$INSTALL_PREFIX"
$SUDO tar -xf app/build/distributions/app-5.4.tar -C "$INSTALL_PREFIX" --strip-components=1
$SUDO ln -sf "$INSTALL_PREFIX/bin/Audiveris" /usr/local/bin/audiveris

# 5. OCR language data for the TITLE/lyrics (full legacy eng from the repo + spa).
echo "🔤 Installing OCR language data (eng + spa)…"
$SUDO mkdir -p "$TESS_DIR"
$SUDO cp "$BUILD_DIR/app/dev/tessdata/eng.traineddata" "$TESS_DIR/"
$SUDO curl -sL -o "$TESS_DIR/spa.traineddata" \
    https://github.com/tesseract-ocr/tessdata/raw/4.1.0/spa.traineddata

echo ""
echo "✅ Audiveris installed at $INSTALL_PREFIX/bin/Audiveris"
