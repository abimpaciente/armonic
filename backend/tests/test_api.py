"""Pruebas de la API (sin OMR: se sube MusicXML directamente)."""

import io
import os
import tempfile

os.environ["ARMONIC_STORAGE"] = tempfile.mkdtemp(prefix="armonic_test_")

from fastapi.testclient import TestClient
from music21 import chord, stream

from backend.app.main import app

client = TestClient(app)


def _closed_score_bytes() -> bytes:
    """Genera un MusicXML de partitura cerrada (2 pentagramas S+A / T+B)."""
    s = stream.Score()
    top = stream.Part()
    bottom = stream.Part()
    for _ in range(3):
        top.append(chord.Chord(["A4", "D4"]))
        bottom.append(chord.Chord(["F#3", "D3"]))
    s.insert(0, top)
    s.insert(0, bottom)
    from music21.musicxml import m21ToXml

    return m21ToXml.GeneralObjectExporter(s).parse()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_score_flow():
    data = _closed_score_bytes()
    r = client.post(
        "/api/upload",
        files={"file": ("hymn.musicxml", io.BytesIO(data), "application/xml")},
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # BackgroundTasks corre tras la respuesta en TestClient -> ya completó
    j = client.get(f"/api/job/{job_id}").json()
    assert j["status"] == "completed", j
    hymn_id = j["hymn_id"]

    h = client.get(f"/api/hymn/{hymn_id}").json()
    assert h["mode"] == "separado"
    assert "bass_solo" in h["tracks"]
    assert h["notes_per_voice"]["bass"] == 3

    # Descarga de un MIDI
    m = client.get(f"/api/hymn/{hymn_id}/midi/bass_solo")
    assert m.status_code == 200
    assert m.headers["content-type"] == "audio/midi"
    assert m.content[:4] == b"MThd"  # cabecera de archivo MIDI


def test_unsupported_type_rejected():
    r = client.post(
        "/api/upload",
        files={"file": ("foo.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_hymns_listing():
    assert "hymns" in client.get("/api/hymns").json()
