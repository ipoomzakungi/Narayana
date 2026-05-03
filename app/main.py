from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_acs import router as acs_router
from app.api.routes_audio import router as audio_router
from app.api.routes_cases import router as cases_router
from app.api.routes_intake import router as intake_router
from app.api.routes_triage import router as triage_router
from app.api.routes_twilio import router as twilio_router
from app.api.routes_tts import router as tts_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Narayana AI Azure Voice Gateway",
        version="0.1.0",
        description="Local-first crisis voice intake and triage assistant for Azure hackathon demos.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(audio_router)
    app.include_router(triage_router)
    app.include_router(intake_router)
    app.include_router(cases_router)
    app.include_router(twilio_router)
    app.include_router(tts_router)
    app.include_router(acs_router)
    return app


app = create_app()
