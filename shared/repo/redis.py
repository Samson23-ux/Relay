from redis.asyncio import Redis
from redis import Redis as SyncRedis


class RedisRepository:
    def __init__(self, async_redis: Redis = None, sync_redis: SyncRedis = None):
        self._sync_redis = sync_redis
        self._async_redis = async_redis

    async def create_hset(self, key: str, mapping: dict):
        await self._async_redis.hset(key, mapping=mapping)

    async def get_hset(self, key: str) -> dict:
        return await self._async_redis.hgetall(key)

    async def delete_key(self, key: str):
        await self._async_redis.delete(key)

    # sync

    def sync_get_key(self, key: str) -> str | None:
        return self._sync_redis.get(key)
    
    def sync_get_hset(self, key: str) -> dict:
        return self._sync_redis.hgetall(key)

    def mark_task_processed(self, key: str, value: str, ttl: int):
        self._sync_redis.set(key, value, ex=ttl)
