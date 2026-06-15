# Audiveris OMR Setup Guide

This document explains how to enable Optical Music Recognition (OMR) for image-to-MIDI conversion in armonic.

## What is OMR?

**Optical Music Recognition** converts images of printed music scores into digital notation (MusicXML). In armonic:

```
Hymn Photo → Audiveris OMR → MusicXML → SATB Separation → 9 Practice MIDI Tracks
```

## ✅ Current Status

Audiveris **v5.4** is now fully integrated:

- ✅ Built from source in Docker container
- ✅ Tesseract OCR 5.3.1 auto-configured
- ✅ Backend recognizes and uses Audiveris automatically
- ✅ Ready for image uploads and OMR processing

## Setup Methods

### Option 1: Docker (Recommended - Built In)

Audiveris is **already included** in the Docker image:

```bash
docker compose up --build
```

The build will take 12-15 minutes on first run (Audiveris compilation).
Subsequent runs will use the cached layer.

**OMR automatically available at:**
- `/api/upload` — accepts .jpg, .png, .tif, .bmp images
- Returns job_id for polling → eventual MIDI tracks

### Option 2: GitHub Codespaces

Your Codespaces environment has Audiveris pre-built at `/opt/audiveris/bin/Audiveris`.

**To enable OMR in running Codespaces:**

```bash
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
docker compose up
```

**Or run the quick setup:**

```bash
bash .devcontainer/quick-setup-codespaces.sh
```

Then restart your backend:

```bash
docker compose restart backend
```

### Option 3: Manual Installation (Local Development)

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install -y openjdk-21-jre-headless tesseract-ocr

# macOS
brew install openjdk@21 tesseract
```

Build and install Audiveris:

```bash
bash .devcontainer/build-audiveris.sh
```

Set environment variable:

```bash
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
```

## Testing OMR

### Test 1: Verify Configuration

```bash
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
python3 << 'EOF'
from backend.app.config import settings
print(f"OMR Available: {settings.omr_available}")
EOF
```

### Test 2: Upload an Image

1. Open http://localhost:8000
2. Click "Upload"
3. Select a hymn photo (JPG, PNG, TIFF)
4. Backend will:
   - Run Audiveris OMR (produces MusicXML)
   - Separate into SATB voices
   - Generate 9 practice MIDI tracks
5. Download your practice tracks

### Test 3: Use Sample Data

Already included sample hymns (no OMR needed):

- `demo.html` — Offline demo with 9 practice tracks
- `backend/app/samples/himno2.mxl` — Real hymn (102 notes)
- `backend/app/samples/demo_satb.musicxml` — Simple example

## How It Works

### Pipeline Flow

1. **Image Upload** → POST `/api/upload`
2. **OMR Processing** → Audiveris converts image to MusicXML
3. **Score Analysis** → music21 analyzes key, parts, notes
4. **SATB Separation** → Splits into 4 voices (soprano, alto, tenor, bass)
5. **MIDI Generation** → Creates 9 practice tracks:
   - 4 voices × (solo + highlighted)
   - 1 full SATB mix
6. **Download** → GET `/api/hymn/{hymn_id}/midi/{track}`

### What Gets Generated

For each hymn, you get 9 MIDI tracks:

| Track | Solo | Highlighted | Full Mix |
|-------|------|-------------|----------|
| Soprano | soprano_solo | soprano_realce | satb_completo |
| Alto | alto_solo | alto_realce | |
| Tenor | tenor_solo | tenor_realce | |
| Bass | bass_solo | bass_realce | |

- **Solo**: Just that voice, unaccompanied
- **Highlighted** (con fondo): That voice prominent, others at background volume
- **Full Mix**: All 4 voices balanced (SATB complete)

## OMR Limitations & Accuracy

Audiveris **≈69% character accuracy** on hymnal photos. It's very good for:

- ✅ Clean printed scores
- ✅ Standard music notation
- ✅ SATB hymnals

It may struggle with:

- ❌ Handwritten annotations
- ❌ Very small print
- ❌ Multiple staves on one line
- ❌ Unusual clefs or time signatures

**Tip**: When uploading photos:
1. Take straight-on shots (no angles)
2. Good lighting (minimize shadows)
3. Focus on the music staff
4. High resolution (2000+ px width)

## Troubleshooting

### "OMR not available" error

**Solution**: Ensure `AUDIVERIS_BIN` environment variable is set:

```bash
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
# Or in docker-compose.yml / Dockerfile
```

### Audiveris builds but Docker image is huge

**Expected**: The built image is ~2-3 GB because:
- Java Runtime (~500 MB)
- Gradle + build artifacts (~800 MB)
- Audiveris binary + deps (~300 MB)
- Python/music21 (~200 MB)

**To reduce**: Use a smaller base image or multi-stage build to drop build artifacts.

### Image processing is slow

**Expected**: OMR is CPU-intensive:
- Small image (~500 KB): 30-60 seconds
- Large image (~2 MB): 2-5 minutes
- Codespaces 4GB RAM: should handle most sizes

**Tip**: Use job polling to check progress:

```javascript
// GET /api/job/{job_id}
// Returns: {job_id, status: "processing", progress: 35}
```

## Next Steps

1. **Local Testing**: `docker compose up` + upload a hymn photo
2. **Codespaces Testing**: Set `AUDIVERIS_BIN`, upload a hymn photo
3. **Deployment**: Push to Render → OMR works on free tier (with patience)

## References

- [Audiveris GitHub](https://github.com/Audiveris/audiveris)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract)
- [music21 Documentation](https://web.mit.edu/music21/)

---

**Questions?** Check `backend/app/omr.py` and `backend/app/pipeline.py` for implementation details.
