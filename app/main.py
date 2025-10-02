from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import entities, contracts, titles, claims, diary, documents, views

def create_app() -> FastAPI:
    app = FastAPI(
        title="Omnia8 File-API",
        description="Utenti → Entità → Contratti → (Titoli, Sinistri, Documenti) con storage filesystem.",
        version="1.0.1",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # restringere in prod
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(entities.router)
    app.include_router(contracts.router)
    app.include_router(titles.router)
    app.include_router(claims.router)
    app.include_router(diary.router)
    app.include_router(documents.router)
    app.include_router(views.router)

    @app.get("/ping")
    def ping(): return {"status": "ok"}

    return app

app = create_app()
