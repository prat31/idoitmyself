from fastapi import APIRouter
from app.api.v1.endpoints import health, ai

api_router = APIRouter()

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI & OpenRouter"])
