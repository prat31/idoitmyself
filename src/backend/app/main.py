import logging

from fastapi import FastAPI

from app.api.v1 import (
    dashboards,
    datasets,
    emails,
    filters,
    gmail,
    health,
    home,
    inboxes,
    labels,
    notifications,
    processors,
    scans,
    stats,
    tags,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="IDIM API", version="0.1.0")

app.include_router(health.router, prefix="/api/v1")
app.include_router(inboxes.router, prefix="/api/v1")
app.include_router(gmail.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")
app.include_router(labels.router, prefix="/api/v1")
app.include_router(filters.router, prefix="/api/v1")
app.include_router(processors.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(emails.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(home.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(dashboards.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
