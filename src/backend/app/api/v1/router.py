from fastapi import APIRouter

from app.api.v1 import dashboard, gmail, health, inboxes, labels, runs, stats, tags

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(inboxes.router)
api_router.include_router(gmail.router)
api_router.include_router(tags.router)
api_router.include_router(labels.router)
api_router.include_router(runs.router)
api_router.include_router(stats.router)
api_router.include_router(dashboard.router)
