from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import agents, auth, chat, integrations, organizations, projects, search, memory

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(organizations.router, prefix="/orgs", tags=["organizations"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(integrations.router, prefix="/integrations/github", tags=["integrations"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(memory.router, prefix="/memory", tags=["memory"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])


@router.get("")
async def v1_root():
    return {"version": "0.1.0", "name": "ContextClaw API v1"}
