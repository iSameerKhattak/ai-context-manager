from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.core.config import settings
from contextclaw.db.engine import close_engine, init_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    await init_engine()
    yield
    await close_engine()


app = FastAPI(
    title="ContextClaw API",
    version="0.1.0",
    description="AI-powered Context Management Platform for Software Teams",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.is_production
        and ["https://app.contextclaw.dev"]
        or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────
app.include_router(v1_router, prefix="/v1")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "api-gateway", "version": "0.1.0"}


@app.get("/readyz")
async def readyz():
    # TODO: check downstream service health
    return {"status": "ok"}
