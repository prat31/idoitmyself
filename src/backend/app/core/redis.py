import asyncio

from redis.asyncio import Redis

from app.core.config import get_settings

# API process: one client on uvicorn's event loop.
redis_client: Redis = Redis.from_url(get_settings().redis_url, decode_responses=True)

_loop_clients: dict[int, Redis] = {}


def loop_redis() -> Redis:
    """A client bound to the running event loop. Celery tasks each run their own loop (asyncio.run),
    and an asyncio Redis connection can't cross loops."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _loop_clients:
        _loop_clients[loop_id] = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _loop_clients[loop_id]


async def close_loop_redis() -> None:
    client = _loop_clients.pop(id(asyncio.get_running_loop()), None)
    if client is not None:
        await client.aclose()
