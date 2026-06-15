#!/bin/bash
set -e

echo "🎼 Building Audiveris from source..."
echo "   This will take 10-15 minutes on first run."
echo ""

BUILD_DIR="/tmp/audiveris-build"
INSTALL_PREFIX="/opt/audiveris"

# Clone Audiveris if not already cloned
if [ ! -d "$BUILD_DIR" ]; then
    echo "📥 Cloning Audiveris repository..."
    git clone --depth 1 https://github.com/Audiveris/audiveris.git "$BUILD_DIR"
fi

# Build Audiveris
echo "⚙️  Building Audiveris (this takes ~10-15 minutes)..."
cd "$BUILD_DIR"
./gradlew clean build -x test

# Extract and install
echo "📦 Installing Audiveris..."
mkdir -p "$INSTALL_PREFIX"
tar -xf app/build/distributions/app-5.4.tar -C "$INSTALL_PREFIX" --strip-components=1

# Create wrapper script that handles environment
mkdir -p /usr/local/bin
cat > /usr/local/bin/audiveris << 'WRAPPER'
#!/bin/bash
# Audiveris wrapper that sets TESSDATA_PREFIX if not already set
if [ -z "$TESSDATA_PREFIX" ]; then
    export TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata"
fi
exec /opt/audiveris/bin/Audiveris "$@"
WRAPPER
chmod +x /usr/local/bin/audiveris

echo "✅ Audiveris installed successfully!"
echo ""
echo "Available as: audiveris (or /opt/audiveris/bin/Audiveris)"
echo "Test with: audiveris --version"
