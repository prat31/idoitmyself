from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def check_health(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check checking API, PostgreSQL, and Redis connectivity."""
    status = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": "unknown",
            "redis": "unknown"
        }
    }

    # Test Database
    try:
        await db.execute(text("SELECT 1"))
        status["dependencies"]["database"] = "connected"
    except Exception as e:
        status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    # Test Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await r.ping()
        await r.close()
        status["dependencies"]["redis"] = "connected" if pong else "unhealthy"
    except Exception as e:
        status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    return status
