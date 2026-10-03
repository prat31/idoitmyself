import time
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.ping")
def ping_task() -> str:
    """Simple ping task to verify worker health."""
    return "pong"


@celery_app.task(name="app.workers.tasks.sample_background_job")
def sample_background_job(job_id: str, duration_seconds: int = 5) -> dict:
    """Demonstration long-running background task."""
    time.sleep(duration_seconds)
    return {
        "job_id": job_id,
        "status": "completed",
        "duration_seconds": duration_seconds
    }
