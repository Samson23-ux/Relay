from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


from shared.repo.redis import RedisRepository
from apps.user_service.app.core.security import Security
from apps.user_service.app.core.config import get_user_settings


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

        self._redis = None
        self._security = Security()
        self._settings = get_user_settings()

    async def dispatch(self, request, call_next):
        self._redis = RedisRepository(async_redis=request.app.state.redis)

        roles: list[str] = request.state.roles
        check_role: bool = request.state.check_role
        revoke_token: bool = request.state.revoke_token
        auth_required: bool = request.state.auth_required

        if auth_required:
            token: str = request.headers.get("Authorization").split("Bearer ")[-1]
            payload: dict = self._security.decode_token(
                token, self._settings.ACCESS_TOKEN_SECRET_KEY
            )

            if not payload:
                raise HTTPException(status_code=401, detail="User not authenticated.")

            if check_role:
                user_role: str = payload.get("userrole")

                if user_role not in roles:
                    raise HTTPException(status_code=403, detail="User not authorized.")

            request.state.user_email = payload.get("sub")
            request.state.user_type = payload.get("usertype")

        if revoke_token:
            refresh_token: str = request.cookies.get("refresh_token")
            payload: dict = await self._security.decode_token(
                refresh_token, self._settings.REFRESH_TOKEN_SECRET_KEY
            )

            if not payload:
                raise HTTPException(status_code=401, detail="User not authenticated.")

            refresh_token_id: str = refresh_token["jti"]
            key: str = f"tokens:{refresh_token_id}"

            refresh_token_db: dict = await self._redis.get_hset(key)

            if not refresh_token_db:
                raise HTTPException(status_code=401, detail="User not authenticated.")

            request.state.user_type = refresh_token_db["email"]
            request.state.user_email = refresh_token_db["user_type"]

            await self._redis.delete_key(key)

        res = await call_next(request)
        return res
