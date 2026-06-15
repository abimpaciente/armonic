"""API REST de armonic.

Flujo: POST /api/upload -> GET /api/job/{id} (polling) -> GET /api/hymn/{id}
      -> GET /api/hymn/{id}/midi/{track}

Sirve además una página de prueba estática en /.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .pipeline import process
from .store import store

app = FastAPI(title="armonic API", version="0.1.0")

VOICE_ORDER = ["soprano", "alto", "tenor", "bass"]


def _process_job(job_id: str, hymn_id: str, src: Path, title: str = "") -> None:
    """Tarea en segundo plano: corre el pipeline y registra el resultado."""
    store.update_job(job_id, status="processing", progress=20)
    work_dir = settings.storage_dir / hymn_id
    try:
        result = process(src, hymn_id, work_dir, title=title)
    except Exception as exc:  # noqa: BLE001 - reportamos el error al cliente
        store.update_job(job_id, status="failed", error=str(exc))
        return

    hymn = {
        "hymn_id": result.hymn_id,
        "title": result.title,
        "key": result.key,
        "mode": result.mode,
        "notes_per_voice": result.notes_per_voice,
        "duration_seconds": result.duration_seconds,
        "tracks": sorted(result.midi_files.keys()),
    }
    # Copia los MIDI a una carpeta estable servible
    midi_dir = work_dir / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    for name, path in result.midi_files.items():
        shutil.copy(path, midi_dir / f"{name}.mid")
    store.add_hymn(hymn)
    store.update_job(job_id, status="completed", progress=100, hymn_id=hymn_id)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "omr_available": settings.omr_available}


@app.post("/api/upload")
async def upload(file: UploadFile, background: BackgroundTasks) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.image_exts | settings.score_exts:
        raise HTTPException(400, f"Tipo de archivo no soportado: {ext or '?'}")
    if ext in settings.image_exts and not settings.omr_available:
        raise HTTPException(
            503,
            "OMR no configurado en el servidor. Sube un MusicXML/MIDI, o "
            "configura AUDIVERIS_BIN.",
        )

    hymn_id = store.new_hymn_id()
    job_id = store.new_job()
    work_dir = settings.storage_dir / hymn_id
    work_dir.mkdir(parents=True, exist_ok=True)
    src = work_dir / f"source{ext}"
    with src.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    title = Path(file.filename or "").stem or "Himno"
    background.add_task(_process_job, job_id, hymn_id, src, title)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/job/{job_id}")
def job_status(job_id: str) -> dict:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job no encontrado")
    return {"job_id": job_id, **job}


@app.get("/api/hymns")
def list_hymns() -> dict:
    return {"hymns": store.list_hymns()}


@app.get("/api/hymn/{hymn_id}")
def get_hymn(hymn_id: str) -> dict:
    hymn = store.get_hymn(hymn_id)
    if hymn is None:
        raise HTTPException(404, "Himno no encontrado")
    return hymn


@app.get("/api/hymn/{hymn_id}/midi/{track}")
def get_midi(hymn_id: str, track: str) -> FileResponse:
    hymn = store.get_hymn(hymn_id)
    if hymn is None:
        raise HTTPException(404, "Himno no encontrado")
    if track not in hymn["tracks"]:
        raise HTTPException(404, f"Pista no encontrada: {track}")
    path = settings.storage_dir / hymn_id / "midi" / f"{track}.mid"
    if not path.exists():
        raise HTTPException(404, "Archivo MIDI no encontrado")
    return FileResponse(path, media_type="audio/midi", filename=f"{track}.mid")


# Página de prueba estática (montada al final para no tapar /api)
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
