from shared.utils import log_error, log_info
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from gateway.app.schemas.config import Config
from gateway.app.core.load_config import load_config

CONFIG_PATH = "gateway/app/core/config.yml"
GATEWAY_CONFIG_KEY = "gateway:config"
GATEWAY_CONFIG_CHANNEL = "gateway:config:reload"


class AdminService:
    def __init__(self, redis_repo: RedisRepository):
        self._redis_repo = redis_repo

    async def load_config(self, request_meta: dict):
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            raw_config = load_config(CONFIG_PATH)
            config = Config.model_validate(raw_config)

            await self._redis_repo.set_key(GATEWAY_CONFIG_KEY, config.model_dump_json())
            await self._redis_repo.publish(GATEWAY_CONFIG_CHANNEL, "reload")

            message = "Config reloaded successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
        except Exception as exc:
            message = f"Error occured while reloading config." f"Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError()
