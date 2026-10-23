class MemoryCounter:
    """In-memory stand-in for the Redis commands QuotaBudget uses."""

    def __init__(self):
        self.values: dict[str, int] = {}

    async def incrby(self, name: str, amount: int) -> int:
        self.values[name] = self.values.get(name, 0) + amount
        return self.values[name]

    async def decrby(self, name: str, amount: int) -> int:
        return await self.incrby(name, -amount)

    async def expire(self, name: str, time: int) -> bool:
        return True
