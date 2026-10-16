from fastapi import APIRouter

from app.api.v1.endpoints import ai, health, items, sources

api_router = APIRouter()

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI & OpenRouter"])
