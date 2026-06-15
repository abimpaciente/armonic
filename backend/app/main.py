"""API REST de armonic.

Flujo: POST /api/upload -> GET /api/job/{id} (polling) -> GET /api/hymn/{id}
      -> GET /api/hymn/{id}/midi/{track}

Sirve además una página de prueba estática en /.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from armonic.voices import DEFAULT_TEMPO, retempo_midi

from .config import settings
from .pipeline import process
from .store import store

app = FastAPI(title="armonic API", version="0.1.0")

VOICE_ORDER = ["soprano", "alto", "tenor", "bass"]


def _persist_result(result, work_dir: Path) -> None:
    """Registra el himno en el store y copia sus MIDI a una carpeta servible."""
    hymn = {
        "hymn_id": result.hymn_id,
        "title": result.title,
        "key": result.key,
        "mode": result.mode,
        "notes_per_voice": result.notes_per_voice,
        "duration_seconds": result.duration_seconds,
        "tracks": sorted(result.midi_files.keys()),
    }
    midi_dir = work_dir / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)
    for name, path in result.midi_files.items():
        shutil.copy(path, midi_dir / f"{name}.mid")
    store.add_hymn(hymn)


def _process_job(job_id: str, hymn_id: str, src: Path, title: str = "") -> None:
    """Tarea en segundo plano: corre el pipeline y registra el resultado."""
    store.update_job(job_id, status="processing", progress=20)
    work_dir = settings.storage_dir / hymn_id
    try:
        result = process(src, hymn_id, work_dir, title=title)
    except Exception as exc:  # noqa: BLE001 - reportamos el error al cliente
        store.update_job(job_id, status="failed", error=str(exc))
        return
    _persist_result(result, work_dir)
    store.update_job(job_id, status="completed", progress=100, hymn_id=hymn_id)


def _seed_demo() -> None:
    """Siembra himnos de demostración si la biblioteca está vacía.

    Útil en despliegues con disco efímero (p. ej. Render plan gratis): el coro
    siempre encuentra dos himnos para probar aunque el contenedor se reinicie.
    - demo: coral SATB de ejemplo (Do mayor)
    - himno2_audiveris: hymn real procesado con OMR (Audiveris, Re mayor)
    """
    if store.list_hymns():
        return
    samples_dir = Path(__file__).resolve().parent / "samples"
    demos = [
        ("demo", "demo_satb.musicxml", "Coral de ejemplo"),
        ("himno2_audiveris", "himno2.mxl", "A Dios, el Padre celestial"),
    ]
    for hymn_id, filename, title in demos:
        sample = samples_dir / filename
        if not sample.exists():
            continue
        work_dir = settings.storage_dir / hymn_id
        try:
            result = process(sample, hymn_id, work_dir, title=title)
            _persist_result(result, work_dir)
        except Exception:  # noqa: BLE001 - el demo es opcional, no debe tumbar el arranque
            pass


@app.on_event("startup")
def _on_startup() -> None:
    settings.ensure_dirs()
    _seed_demo()


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


def _delete_hymn_files(hymn_id: str) -> None:
    """Borra la carpeta de un himno, siempre dentro de storage_dir."""
    work_dir = (settings.storage_dir / hymn_id).resolve()
    if work_dir.parent == settings.storage_dir and work_dir.is_dir():
        shutil.rmtree(work_dir, ignore_errors=True)


@app.delete("/api/hymns")
def clear_hymns() -> dict:
    ids = store.clear_hymns()
    for hymn_id in ids:
        _delete_hymn_files(hymn_id)
    return {"deleted": len(ids)}


@app.delete("/api/hymn/{hymn_id}")
def delete_hymn(hymn_id: str) -> dict:
    if not store.remove_hymn(hymn_id):
        raise HTTPException(404, "Himno no encontrado")
    _delete_hymn_files(hymn_id)
    return {"deleted": hymn_id}


@app.get("/api/hymn/{hymn_id}/midi/{track}")
def get_midi(
    hymn_id: str,
    track: str,
    tempo: int | None = Query(None, ge=40, le=160,
                              description="BPM de ensayo; por defecto el original"),
) -> FileResponse:
    hymn = store.get_hymn(hymn_id)
    if hymn is None:
        raise HTTPException(404, "Himno no encontrado")
    if track not in hymn["tracks"]:
        raise HTTPException(404, f"Pista no encontrada: {track}")
    path = settings.storage_dir / hymn_id / "midi" / f"{track}.mid"
    if not path.exists():
        raise HTTPException(404, "Archivo MIDI no encontrado")

    # Sin tempo (o el de por defecto) -> sirve el MIDI tal cual.
    if tempo is None or tempo == DEFAULT_TEMPO:
        return FileResponse(path, media_type="audio/midi",
                            filename=f"{track}.mid")

    # Tempo personalizado -> genera (y cachea) una copia reajustada.
    cached = settings.storage_dir / hymn_id / "midi" / "cache" / f"{track}__{tempo}.mid"
    if not cached.exists():
        try:
            retempo_midi(str(path), tempo, str(cached))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, f"No se pudo ajustar el tempo: {exc}")
    return FileResponse(cached, media_type="audio/midi",
                        filename=f"{track}_{tempo}bpm.mid")


class SPAStaticFiles(StaticFiles):
    """Sirve archivos estáticos y, para rutas desconocidas (no /api ni un
    archivo real), devuelve index.html para que el router de Angular maneje
    enlaces profundos como /hymn/xyz al recargar la página."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


# Frontend (app Angular compilada en producción; página de prueba en local).
# Montado al final para no tapar /api.
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", SPAStaticFiles(directory=str(_static_dir), html=True), name="static")
