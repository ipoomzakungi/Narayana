from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_audio import router as audio_router
from app.api.routes_cases import router as cases_router
from app.api.routes_triage import router as triage_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Narayana AI Azure Voice Gateway",
        version="0.1.0",
        description="Local-first crisis voice intake and triage assistant for Azure hackathon demos.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(audio_router)
    app.include_router(triage_router)
    app.include_router(cases_router)
    return app


app = create_app()
