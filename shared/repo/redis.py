from redis.asyncio import Redis
from redis import Redis as SyncRedis


class RedisRepository:
    def __init__(self, async_redis: Redis = None, sync_redis: SyncRedis = None):
        self._sync_redis = sync_redis
        self._async_redis = async_redis

    async def set_key(self, key: str, value: str, expire: int = None):
        await self._async_redis.set(key, value, ex=expire)

    async def publish(self, channel: str, message: str):
        await self._async_redis.publish(channel, message)

    async def create_hset(self, key: str, mapping: dict):
        await self._async_redis.hset(key, mapping=mapping)

    async def increment_counter(self, key: str) -> int:
        return await self._async_redis.incr(key)

    async def get_hset(self, key: str) -> dict:
        return await self._async_redis.hgetall(key)

    async def get_key(self, key: str) -> str:
        return await self._async_redis.get(key)

    async def decrement_counter(self, key: str) -> int:
        return await self._async_redis.decr(key)

    async def delete_key(self, key: str):
        await self._async_redis.delete(key)

    async def add_to_sorted_set(self, key: str, member: str, score: float):
        await self._async_redis.zadd(key, {member: score})

    async def get_sorted_set(self, key: str, desc: bool = False) -> list[str]:
        if desc:
            return await self._async_redis.zrevrange(key, 0, -1)
        return await self._async_redis.zrange(key, 0, -1)

    async def remove_from_sorted_set(self, key: str, member: str):
        await self._async_redis.zrem(key, member)

    async def acquire_lock(self, key: str, token: str, ttl: int) -> bool:
        return bool(await self._async_redis.set(key, token, nx=True, ex=ttl))

    async def release_lock(self, key: str, token: str):
        if await self._async_redis.get(key) == token:
            await self._async_redis.delete(key)

    # sync

    def sync_get_key(self, key: str) -> str | None:
        return self._sync_redis.get(key)
    
    def sync_get_hset(self, key: str) -> dict:
        return self._sync_redis.hgetall(key)

    def mark_task_processed(self, key: str, value: str, ttl: int):
        self._sync_redis.set(key, value, ex=ttl)
