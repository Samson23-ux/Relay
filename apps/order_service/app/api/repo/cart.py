import json
import asyncio
from uuid import UUID, uuid4


from shared.repo.redis import RedisRepository

LOCK_TTL = 5
LOCK_WAIT_TIMEOUT = 3
LOCK_RETRY_INTERVAL = 0.05


class CartRepository:
    def __init__(self, redis_repo: RedisRepository):
        self._redis_repo = redis_repo

    def _cart_key(self, cart_id: UUID) -> str:
        return f"cart:{cart_id}"

    def _user_carts_key(self, user_id: UUID) -> str:
        return f"user:{user_id}:carts"

    def _lock_key(self, cart_id: UUID) -> str:
        return f"lock:cart:{cart_id}"

    async def get_cart(self, cart_id: UUID) -> dict | None:
        raw: str | None = await self._redis_repo.get_key(self._cart_key(cart_id))
        return json.loads(raw) if raw else None

    async def get_carts(self, user_id: UUID, sort: str | None, order: str) -> list[dict]:
        cart_ids: list[str] = await self._redis_repo.get_sorted_set(
            self._user_carts_key(user_id), desc=bool(sort and order == "desc")
        )

        carts = []
        for cart_id in cart_ids:
            cart = await self.get_cart(cart_id)
            if cart:
                carts.append(cart)
        return carts

    async def save_cart(self, cart: dict):
        await self._redis_repo.set_key(self._cart_key(cart["id"]), json.dumps(cart))

    async def index_cart(self, user_id: UUID, cart_id: UUID, created_at_ts: float):
        await self._redis_repo.add_to_sorted_set(
            self._user_carts_key(user_id), str(cart_id), created_at_ts
        )

    async def delete_cart(self, user_id: UUID, cart_id: UUID):
        await self._redis_repo.delete_key(self._cart_key(cart_id))
        await self._redis_repo.remove_from_sorted_set(
            self._user_carts_key(user_id), str(cart_id)
        )

    async def acquire_lock(self, cart_id: UUID) -> str:
        token: str = str(uuid4())
        key: str = self._lock_key(cart_id)

        waited = 0.0
        while waited < LOCK_WAIT_TIMEOUT:
            if await self._redis_repo.acquire_lock(key, token, LOCK_TTL):
                return token

            await asyncio.sleep(LOCK_RETRY_INTERVAL)
            waited += LOCK_RETRY_INTERVAL

        raise TimeoutError(f"Could not acquire lock for cart {cart_id}")

    async def release_lock(self, cart_id: UUID, token: str):
        await self._redis_repo.release_lock(self._lock_key(cart_id), token)
