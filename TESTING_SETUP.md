# Testing OMR in Codespaces - Quick Start

## Current Status ✅

Audiveris **v5.4** has been successfully built and is ready to use.

- ✅ Audiveris binary: `/opt/audiveris/bin/Audiveris`
- ✅ Tesseract OCR: 5.3.1 (auto-detected)
- ✅ Backend configuration: OMR-ready

## Enable OMR in Your Codespaces

In your Codespaces terminal, run:

```bash
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"
```

Or add to your shell profile:

```bash
echo "export AUDIVERIS_BIN='/opt/audiveris/bin/Audiveris'" >> ~/.bashrc
source ~/.bashrc
```

## Start the Backend

```bash
cd /workspaces/armonic
docker compose up --build
```

First run: ~2-3 minutes (Docker build)
Subsequent runs: ~30 seconds

## Test the OMR Pipeline

### Option A: Upload a Hymn Image (Full Test)

1. Open http://localhost:8000 in your browser
2. Click the upload button
3. Select a hymn photo from your device (JPG, PNG, or TIFF)
4. Wait for processing (1-5 minutes depending on image size)
5. Download the generated MIDI practice tracks

### Option B: Upload MusicXML (Quick Test - No OMR)

1. Open http://localhost:8000
2. Upload `backend/app/samples/himno2.mxl`
3. Instant processing (no OMR needed)
4. Download MIDI tracks to verify SATB separation works

### Option C: Test from CLI

```bash
# Export env var first
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"

# Test OMR configuration
python3 << 'EOF'
from backend.app.config import settings
print(f"OMR Available: {settings.omr_available}")
print(f"Audiveris: {settings.audiveris_bin}")
EOF

# You should see:
# OMR Available: True
# Audiveris: /opt/audiveris/bin/Audiveris
```

## What to Expect

### Image Processing Times

- Small image (< 1 MB): 1-2 minutes
- Medium image (1-3 MB): 2-5 minutes
- Large image (> 3 MB): 5-10 minutes

Codespaces has 4 GB RAM, which is sufficient for most hymnal images.

### Generated MIDI Tracks

For each hymn you process, you'll get:

```
/api/hymn/{hymn_id}/
├── soprano_solo.mid           # Just soprano, unaccompanied
├── soprano_realce.mid         # Soprano prominent + other voices
├── alto_solo.mid
├── alto_realce.mid
├── tenor_solo.mid
├── tenor_realce.mid
├── bass_solo.mid
├── bass_realce.mid
└── satb_completo.mid          # All 4 voices balanced
```

### Check Processing Status

```bash
# While processing:
curl http://localhost:8000/api/job/{job_id}
# Returns: {"status": "processing", "progress": 45}

# After completion:
curl http://localhost:8000/api/hymn/{hymn_id}
# Returns metadata + list of generated tracks
```

## Expected OMR Accuracy

Audiveris v5.4 achieves **~69% character accuracy** on good-quality hymnal photos.

**Works well with:**
- Printed scores (hymn books)
- Clean, high-contrast images
- Standard SATB layout
- Good lighting

**May struggle with:**
- Handwritten notes
- Very small print
- Unusual clefs or signatures
- Angled/blurry photos

## Troubleshooting

### OMR not available in backend

**Symptom**: Upload form shows "OMR not configured"

**Fix**:
```bash
# Make sure env var is set
export AUDIVERIS_BIN="/opt/audiveris/bin/Audiveris"

# Restart Docker
docker compose restart backend
```

### Docker compose fails to build

**Symptom**: `docker compose up --build` fails

**Solution 1**: Use cached build (if Audiveris was already built)
```bash
docker compose up
```

**Solution 2**: Clean and rebuild
```bash
docker compose down -v
docker compose up --build
```

### Processing hangs or times out

**Default timeout**: 10 minutes

**For larger images**: Increase timeout in `backend/app/pipeline.py`

```python
result = process(src, hymn_id, work_dir, title=title)
# Change timeout in run_audiveris(... timeout=600)
```

### Web interface not loading

**Check backend health**:
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{"status": "ok", "omr_available": true}
```

## Next Steps

1. **Test locally** with a hymn image
2. **Verify MIDI output** sounds correct
3. **Try different images** to understand accuracy
4. **Deploy to Render** (when ready for production)

## Files to Know

| File | Purpose |
|------|---------|
| `backend/app/omr.py` | Audiveris wrapper |
| `backend/app/pipeline.py` | Full OMR→SATB→MIDI pipeline |
| `backend/app/main.py` | API endpoints (/api/upload, etc) |
| `OMR_SETUP.md` | Detailed OMR setup guide |

---

**Need help?** Check the error messages in the browser console and Docker logs:

```bash
docker compose logs -f backend
```

**Ready to deploy?** See [DEPLOY.md](DEPLOY.md) for Render/Docker Hub instructions.
