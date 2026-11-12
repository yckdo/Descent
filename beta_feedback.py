"""Collecte des signalements pour Descent V2 (stockage SQLite local).

Mode privé par défaut : DESCENT_BETA_REQUIRE_AUTH=1 avec
DESCENT_BETA_TOKEN_HASHES. Mode libre explicite : DESCENT_BETA_REQUIRE_AUTH=0.
Le mode libre conserve les limites de fréquence et de concurrence.
Aucun secret ne doit être embarqué dans GitHub Pages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent
_LIMIT_LOCK = threading.Lock()
_LIMIT: dict[str, list[float]] = {}
_ASK_SLOTS = threading.BoundedSemaphore(value=2)


class IncorrectFeedback(BaseModel):
    verdict: Literal["incorrect"] = "incorrect"
    question: str = Field(min_length=3, max_length=1000)
    answer: dict[str, Any]
    comment: str = Field(default="", max_length=1500)


def _db_path() -> Path:
    configured = os.environ.get("DESCENT_BETA_FEEDBACK_DB", "").strip()
    return Path(configured) if configured else BASE_DIR / "data" / "beta_feedback.sqlite3"


def _record(report: IncorrectFeedback) -> str:
    payload = json.dumps(report.answer, ensure_ascii=False)
    if len(payload.encode("utf-8")) > 32000:
        raise HTTPException(413, "Réponse trop volumineuse.")
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    report_id = uuid.uuid4().hex
    with sqlite3.connect(path, timeout=15) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incorrect_feedback (
                id TEXT PRIMARY KEY,
                created_utc TEXT NOT NULL,
                verdict TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_json TEXT NOT NULL,
                comment TEXT NOT NULL
            )
        """)
        connection.execute(
            "INSERT INTO incorrect_feedback VALUES (?, ?, ?, ?, ?, ?)",
            (
                report_id,
                datetime.now(timezone.utc).isoformat(),
                report.verdict,
                report.question,
                payload,
                report.comment,
            ),
        )
    return report_id


@router.post("/api/feedback", status_code=201)
def report_incorrect_answer(report: IncorrectFeedback):
    return {"status": "recorded", "feedback_id": _record(report)}


def _authorized(request: Request) -> tuple[bool, str]:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False, ""
    token = header[7:].strip()
    if not token or len(token) > 200:
        return False, ""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stored = [h.strip().lower() for h in os.environ.get("DESCENT_BETA_TOKEN_HASHES", "").split(",") if h.strip()]
    valid = any(len(h) == 64 and hmac.compare_digest(digest, h) for h in stored)
    return valid, digest


def _limited(key: str, path: str, limit: int | None = None) -> bool:
    now = time.monotonic()
    if limit is None:
        limit = 12 if path == "/api/ask" else 30
    identifier = f"{key}:{path}"
    with _LIMIT_LOCK:
        timestamps = [v for v in _LIMIT.get(identifier, ()) if now - v < 60]
        if len(timestamps) >= limit:
            _LIMIT[identifier] = timestamps
            return True
        timestamps.append(now)
        _LIMIT[identifier] = timestamps
        if len(_LIMIT) > 1000:
            for k in list(_LIMIT)[:250]:
                if not any(now - t < 60 for t in _LIMIT[k]):
                    del _LIMIT[k]
        return False


def install_beta_feedback(app: FastAPI) -> None:
    """À appeler une seule fois après la création de l'application FastAPI."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://yckdo.github.io",
            "http://127.0.0.1:8001",
            "http://localhost:8001",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def _beta_access(request: Request, call_next):
        endpoint = request.url.path
        guarded = request.method != "OPTIONS" and endpoint in ("/api/ask", "/api/feedback")
        if not guarded:
            return await call_next(request)

        # Par défaut, l'API reste fermée sans configuration explicite.
        if os.environ.get("DESCENT_BETA_REQUIRE_AUTH") != "0":
            if not os.environ.get("DESCENT_BETA_TOKEN_HASHES", "").strip():
                return JSONResponse({"detail": "Accès bêta non configuré."}, status_code=503)
            ok, identity = _authorized(request)
            if not ok:
                return JSONResponse({"detail": "Code testeur invalide."}, status_code=401)
            if _limited(identity, endpoint):
                return JSONResponse({"detail": "Trop de demandes. Réessaie dans une minute."}, status_code=429)
        else:
            # Lien ouvert à tous : limiter la charge globale ET par visiteur.
            # CF-Connecting-IP est défini par Cloudflare pour les visiteurs du tunnel.
            client_ip = request.headers.get("CF-Connecting-IP") or (
                request.client.host if request.client else "unknown"
            )
            max_global = 20 if endpoint == "/api/ask" else 60
            max_client = 6 if endpoint == "/api/ask" else 12
            if _limited("public-global", endpoint, limit=max_global) or _limited(
                f"public-ip:{client_ip}", endpoint, limit=max_client
            ):
                return JSONResponse({"detail": "Trop de demandes. Réessaie dans une minute."}, status_code=429)

        # Éviter qu'un groupe de requêtes simultanées sature Qwen local.
        need_slot = endpoint == "/api/ask"
        if need_slot and not _ASK_SLOTS.acquire(blocking=False):
            return JSONResponse({"detail": "Serveur occupé. Réessaie dans un instant."}, status_code=429)
        try:
            return await call_next(request)
        finally:
            if need_slot:
                _ASK_SLOTS.release()

    app.include_router(router)
