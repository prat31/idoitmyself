from fastapi import APIRouter

from app.api.v1 import dashboard, emails, filters, gmail, health, inboxes, labels, scans, stats, tags

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(inboxes.router)
api_router.include_router(gmail.router)
api_router.include_router(tags.router)
api_router.include_router(labels.router)
api_router.include_router(filters.router)
api_router.include_router(scans.router)
api_router.include_router(emails.router)
api_router.include_router(stats.router)
api_router.include_router(dashboard.router)
