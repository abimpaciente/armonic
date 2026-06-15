"""Almacenamiento simple para el MVP: registro de himnos en JSON + jobs en
memoria. En producción esto se reemplaza por Firestore/PostgreSQL + S3.
"""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

from .config import settings


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.jobs: Dict[str, dict] = {}
        self.hymns: Dict[str, dict] = {}
        self._load()

    # --- persistencia de himnos ---
    @property
    def _index_path(self) -> Path:
        return settings.storage_dir / "hymns.json"

    def _load(self) -> None:
        settings.ensure_dirs()
        if self._index_path.exists():
            self.hymns = json.loads(self._index_path.read_text("utf-8"))

    def _save(self) -> None:
        self._index_path.write_text(
            json.dumps(self.hymns, ensure_ascii=False, indent=2), "utf-8"
        )

    # --- jobs ---
    def new_job(self) -> str:
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self.jobs[job_id] = {"status": "queued", "progress": 0,
                                 "hymn_id": None, "error": None}
        return job_id

    def update_job(self, job_id: str, **fields) -> None:
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(fields)

    def get_job(self, job_id: str) -> Optional[dict]:
        return self.jobs.get(job_id)

    # --- himnos ---
    def add_hymn(self, hymn: dict) -> None:
        with self._lock:
            self.hymns[hymn["hymn_id"]] = hymn
            self._save()

    def get_hymn(self, hymn_id: str) -> Optional[dict]:
        return self.hymns.get(hymn_id)

    def list_hymns(self) -> list:
        return sorted(self.hymns.values(), key=lambda h: h.get("title", ""))

    def new_hymn_id(self) -> str:
        return uuid.uuid4().hex[:12]


store = Store()
