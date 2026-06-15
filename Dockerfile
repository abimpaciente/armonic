# ---- Stage 1: build the Angular frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 3: Build Audiveris from source (needs JDK 21) ----
FROM gradle:8.5-jdk21 AS audiveris-builder
WORKDIR /audiveris
RUN git clone --depth 1 https://github.com/Audiveris/audiveris.git .
RUN ./gradlew clean build -x test

# ---- Stage 4: Python backend that also serves the built frontend ----
FROM python:3.11-slim
WORKDIR /app

# Java 21 runtime for Audiveris (copied from Temurin; Debian slim has no openjdk-21).
# libtesseract is needed by Audiveris' OCR (via JNI); tesseract-ocr pulls it in.
COPY --from=eclipse-temurin:21-jre /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="$JAVA_HOME/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Audiveris
COPY --from=audiveris-builder /audiveris/app/build/distributions/app-5.4.tar /tmp/audiveris.tar
RUN mkdir -p /opt/audiveris && tar -xf /tmp/audiveris.tar -C /opt/audiveris --strip-components=1 && \
    rm /tmp/audiveris.tar && \
    ln -s /opt/audiveris/bin/Audiveris /usr/local/bin/audiveris

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
ENV AUDIVERIS_BIN=/usr/local/bin/audiveris
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
